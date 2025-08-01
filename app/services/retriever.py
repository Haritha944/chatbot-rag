from typing import List
import asyncio
from langchain.schema import Document
from langchain_core.retrievers import BaseRetriever
from ..services.vector_store import VectorStoreService
from ..config import settings
from ..common.logger import get_logger

logger = get_logger(__name__)

class RetrieverService:
    def __init__(self):
        self.vector_store_service = VectorStoreService()
    
    def get_retriever(self, client_id: str, k: int = 4) -> BaseRetriever:
        """Get retriever from client-specific vector store"""
        vector_store = self.vector_store_service.get_vector_store(client_id)
        return vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
    
    def get_relevant_documents(self, query: str, client_id: str, k: int = 4) -> List[Document]:
        """Get relevant documents for a query from client-specific collection"""
        try:
            return self.vector_store_service.search_documents(query, client_id, k=k)
        except Exception as e:
            logger.error(f"Error retrieving documents for client {client_id}: {str(e)}")
            raise
    
    async def get_relevant_documents_async(self, query: str, client_id: str, k: int = 4) -> List[Document]:
        """Async version of get_relevant_documents for better concurrency"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get_relevant_documents, query, client_id, k
        )
    
    def get_relevant_documents_with_scores(self, query: str, client_id: str, k: int = 4):
        """Get relevant documents with similarity scores from client-specific collection"""
        try:
            vector_store = self.vector_store_service.get_vector_store(client_id)
            return vector_store.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"Error retrieving documents with scores for client {client_id}: {str(e)}")
            raise
