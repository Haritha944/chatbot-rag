import time
import uuid
import asyncio
from typing import Optional, Dict, Any
from collections import OrderedDict

from langchain.chains import ConversationalRetrievalChain
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory

from ..config import settings
from ..schemas.chat import ChatResponse
from ..common.logger import get_logger
from ..memory import SessionStore
from .retriever import RetrieverService

logger = get_logger(__name__)


class RAGChain:
    """Production-ready Conversational RAG Chain Service with LRU Cache and Async Operations"""
    
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.model_name,
            temperature=0.7,
            max_tokens=2048
        )
        self.retriever_service = RetrieverService()
        self.session_store = SessionStore()
        
        # ✅ LRU Cache with maximum size to prevent memory leaks
        self.max_cached_chains = settings.max_cached_sessions
        self.chains = OrderedDict()  # LRU cache for chains
        
        # ✅ Add locks for thread safety
        self._chain_lock = asyncio.Lock()
        
        logger.info(f"RAG Chain service initialized with LRU cache (max: {self.max_cached_chains} sessions)")
    
    async def _get_memory(self, session_id: str):
        """Get memory for session and load history from SQLite session store"""
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=settings.max_token_limit,
            output_key="answer"  # ✅ Specify which output key to store in memory
        )
        
        # ✅ Load existing chat history asynchronously
        chat_history = await self.session_store.get_session_async(session_id)
        if chat_history:
            logger.info(f"Loaded {len(chat_history)} messages from SQLite for session: {session_id}")
            for message in chat_history:
                memory.chat_memory.add_message(message)
        
        return memory
    
    async def _get_chain(self, session_id: str, client_id: str):
        """Get or create conversational chain for session and client with LRU cache"""
        chain_key = f"{session_id}_{client_id}"  # ✅ Unique key per session+client
        
        async with self._chain_lock:
            # ✅ LRU cache management
            if chain_key in self.chains:
                # Move to end (most recently used)
                self.chains.move_to_end(chain_key)
                return self.chains[chain_key]
            
            # ✅ Evict oldest chains if cache is full
            if len(self.chains) >= self.max_cached_chains:
                oldest_key, oldest_chain = self.chains.popitem(last=False)
                logger.debug(f"Evicted chain: {oldest_key}")
            
            # Create new chain
            memory = await self._get_memory(session_id)
            
            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.retriever_service.get_retriever(client_id),  # ✅ Client-specific retriever
                memory=memory,
                return_source_documents=True,
                verbose=False  # Disable verbose in production
            )
            
            self.chains[chain_key] = chain
            logger.info(f"Created new chain for session: {session_id}, client: {client_id}")
            
            return chain
    
    async def get_response(
        self, 
        message: str, 
        client_id: str,  # ✅ Now required
        session_id: str = None, 
        use_memory: bool = True
    ) -> ChatResponse:
        """Get conversational response with RAG for specific client"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        start_time = time.time()
        logger.info(f"Processing request for client {client_id}, session: {session_id}")
        
        try:
            if use_memory:
                # Use conversational chain with memory
                chain = await self._get_chain(session_id, client_id)
                
                # ✅ Run chain in thread pool to avoid blocking
                result = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: chain.invoke({"question": message})
                )
                response_text = result["answer"]
                
                # ✅ Save to SQLite session store asynchronously
                await asyncio.gather(
                    self.session_store.add_message_async(session_id, "user", message),
                    self.session_store.add_message_async(session_id, "assistant", response_text)
                )
                
                sources = [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in result.get("source_documents", [])
                ]
                
            else:
                # Direct RAG without memory
                docs = await self.retriever_service.get_relevant_documents_async(message, client_id)
                context = "\n".join([doc.page_content for doc in docs])

                prompt = f"""You are a helpful assistant. Answer the following question based ONLY on the provided context.
                If the answer is not available in the context, politely state that you cannot find the information.

                Context: {context}\n\nQuestion: {message}\n\nAnswer:"""
                
                # ✅ Run LLM in thread pool to avoid blocking
                response = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.llm.invoke(prompt)
                )
                response_text = response.content
                sources = [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in docs
                ]
            
            execution_time = time.time() - start_time
            logger.info(f"Response generated for client {client_id} in {execution_time:.4f}s")
            
            return ChatResponse(
                response=response_text,
                session_id=session_id,
                client_id=client_id,  # ✅ Add the missing client_id
                sources=sources,
                memory_used=use_memory
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"RAG chain error for client {client_id} after {execution_time:.4f}s: {str(e)}")
            raise
    
    def clear_session(self, session_id: str, client_id: str = None):
        """Clear session memory and chain"""
        try:
            if client_id:
                chain_key = f"{session_id}_{client_id}"
                if chain_key in self.chains:
                    del self.chains[chain_key]
            else:
                # Clear all chains for this session (across all clients)
                keys_to_remove = [key for key in self.chains.keys() if key.startswith(f"{session_id}_")]
                for key in keys_to_remove:
                    del self.chains[key]
            
            self.session_store.clear_session(session_id)
            logger.info(f"Cleared session: {session_id}")
        except Exception as e:
            logger.error(f"Error clearing session {session_id}: {str(e)}")
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            expired_sessions = self.session_store.cleanup_expired_sessions()
            
            # ✅ Clean up chains for expired sessions
            for session_id in expired_sessions:
                keys_to_remove = [key for key in self.chains.keys() if key.startswith(f"{session_id}_")]
                for key in keys_to_remove:
                    del self.chains[key]
                logger.info(f"Cleaned up expired chain for session: {session_id}")
                
        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions"""
        # Get stats from SQLite session store
        if hasattr(self.session_store, 'get_stats'):
            store_stats = self.session_store.get_stats()
        else:
            store_stats = {"total_sessions": len(self.session_store.list_sessions())}
            
        return {
            "active_chains": len(self.chains),
            "session_ids": list(self.chains.keys()),
            **store_stats
        }
