import os
import time
import uuid
from typing import List, Optional
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from app.common.file_loader import FileLoader
from app.config import settings
from app.common.logger import get_logger
from app.schemas.ingest import IngestResponse

logger = get_logger(__name__)

class VectorStoreService:
    def __init__(self):
        logger.info("Initializing Vector Store Service")
        
        try:
            # Ensure HuggingFace cache directories exist and are writable
            self._setup_cache_directories()
            
            # Initialize embeddings with better error handling
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                cache_folder=os.getenv('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
            )
            logger.info("HuggingFace embeddings initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {str(e)}")
            logger.error("Common solutions:")
            logger.error("1. Check if the model cache directory has proper permissions")
            logger.error("2. Ensure sufficient disk space is available")
            logger.error("3. Check network connectivity for model downloading")
            raise
        
        self.file_loader = FileLoader()
        self._ensure_vector_store_dir()
        logger.info("Vector Store Service initialized successfully")
    
    def _setup_cache_directories(self):
        """Setup and ensure HuggingFace cache directories exist with proper permissions"""
        cache_dirs = [
            os.getenv('HF_HOME', os.path.expanduser('~/.cache/huggingface')),
            os.getenv('TRANSFORMERS_CACHE', os.path.expanduser('~/.cache/huggingface/transformers')),
            os.getenv('HF_DATASETS_CACHE', os.path.expanduser('~/.cache/huggingface/datasets'))
        ]
        
        for cache_dir in cache_dirs:
            try:
                os.makedirs(cache_dir, exist_ok=True)
                # Test write permissions
                test_file = os.path.join(cache_dir, 'test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                logger.debug(f"Cache directory verified: {cache_dir}")
            except PermissionError as e:
                logger.error(f"Permission denied for cache directory {cache_dir}: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to setup cache directory {cache_dir}: {e}")
                raise
    
    def _ensure_vector_store_dir(self):
        """Ensure vector store directory exists"""
        os.makedirs(settings.vector_store_path, exist_ok=True)
    
    def _generate_client_id(self) -> str:
        """Generate a unique client ID"""
        return f"client_{str(uuid.uuid4())[:8]}"  # e.g., "client_a1b2c3d4"
    
    def _get_collection_name(self, client_id: str) -> str:
        """Generate collection name for client"""
        # Sanitize client_id for collection name
        safe_client_id = "".join(c for c in client_id if c.isalnum() or c in ('_', '-'))
        return f"docs_{safe_client_id}"
    
    def get_vector_store(self, client_id: Optional[str] = None) -> Chroma:
        """Get or create ChromaDB vector store for specific client"""
        if not client_id:
            client_id = "default"  # Use default collection if no client_id
        
        collection_name = self._get_collection_name(client_id)
        logger.info(f"Using collection: {collection_name}")
        
        return Chroma(
            persist_directory=settings.vector_store_path,
            embedding_function=self.embeddings,
            collection_name=collection_name
        )
    
    async def ingest_documents(
        self, 
        file_paths: List[str], 
        client_id: Optional[str] = None,  # ✅ Optional parameter
        chunk_size: int = 1000, 
        chunk_overlap: int = 200
    ) -> IngestResponse:
        """Ingest documents into client-specific vector store"""
        
        # ✅ Auto-generate client_id if not provided or if it's a placeholder
        if not client_id or client_id.lower().strip() in ["string", "null", "", "none"]:
            client_id = self._generate_client_id()
            logger.info(f"Generated new client_id: {client_id}")
        else:
            logger.info(f"Using existing client_id: {client_id}")
        
        logger.info(f"Starting document ingestion for client {client_id}: {len(file_paths)} files")
        start_time = time.time()
        
        try:
            # Load documents
            documents = []
            for i, file_path in enumerate(file_paths, 1):
                logger.info(f"Loading file {i}/{len(file_paths)}: {file_path}")
                try:
                    docs = self.file_loader.load_file(file_path)
                    
                    # Add client_id to metadata
                    for doc in docs:
                        doc.metadata["client_id"] = client_id
                        doc.metadata["upload_timestamp"] = time.time()
                    
                    documents.extend(docs)
                    logger.info(f"Loaded {len(docs)} documents from {file_path}")
                except Exception as e:
                    logger.error(f"Failed to load {file_path}: {str(e)}")
                    continue
            
            if not documents:
                raise ValueError("No documents loaded successfully")
            
            logger.info(f"Total documents loaded for client {client_id}: {len(documents)}")
            
            # Split documents into chunks
            logger.info("Splitting documents into chunks")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
            )
            
            chunks = text_splitter.split_documents(documents)
            logger.info(f"Created {len(chunks)} chunks for client {client_id}")
            
            # Add to client-specific vector store
            logger.info(f"Adding chunks to client-specific vector store: {client_id}")
            vector_store = self.get_vector_store(client_id)
            vector_store.add_documents(chunks)
            
            total_time = time.time() - start_time
            logger.info(f"Document ingestion completed for client {client_id} in {total_time:.4f}s")
            
            return IngestResponse(
                message="Documents ingested successfully",
                documents_processed=len(file_paths),
                chunks_created=len(chunks),
                client_id=client_id  
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Document ingestion failed for client {client_id} after {execution_time:.4f}s: {str(e)}")
            raise
    
    def search_documents(self, query: str, client_id: str, k: int = 4) -> List[Document]:
        """Search for relevant documents in client-specific collection"""
        try:
            logger.info(f"Searching documents for client {client_id}")
            vector_store = self.get_vector_store(client_id)
            results = vector_store.similarity_search(query, k=k)
            logger.info(f"Found {len(results)} documents for client {client_id}")
            return results
        except Exception as e:
            logger.error(f"Document search failed for client {client_id}: {str(e)}")
            raise
    
    def delete_collection(self, client_id: Optional[str] = None):
        """Completely delete specific client's collection"""
        if not client_id:
            client_id = "default"
            
        logger.info(f"Deleting collection for client: {client_id}")
        collection_name = self._get_collection_name(client_id)
        
        try:
            # Get ChromaDB client directly to completely remove collection
            chroma_client = chromadb.PersistentClient(path=settings.vector_store_path)
            
            # Check if collection exists before trying to delete
            existing_collections = [c.name for c in chroma_client.list_collections()]
            if collection_name in existing_collections:
                chroma_client.delete_collection(collection_name)
                logger.info(f"Collection {collection_name} completely deleted")
            else:
                logger.warning(f"Collection {collection_name} not found")
                
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {str(e)}")
            raise
    
    def list_client_collections(self) -> List[dict]:
        """List all client collections with details"""
        try:
            # Get ChromaDB client directly
            chroma_client = chromadb.PersistentClient(path=settings.vector_store_path)
            collections = chroma_client.list_collections()
            
            client_collections = []
            for collection in collections:
                if collection.name.startswith("docs_"):
                    client_id = collection.name.replace("docs_", "")
                    client_collections.append({
                        "client_id": client_id,
                        "collection_name": collection.name,
                        "document_count": collection.count()
                    })
            
            logger.info(f"Found {len(client_collections)} client collections")
            return client_collections
            
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            return []
    
    def get_client_stats(self, client_id: str) -> dict:
        """Get statistics for client's collection"""
        try:
            collection_name = self._get_collection_name(client_id)
            
            # Check if collection exists first
            chroma_client = chromadb.PersistentClient(path=settings.vector_store_path)
            existing_collections = [c.name for c in chroma_client.list_collections()]
            
            if collection_name not in existing_collections:
                return {
                    "client_id": client_id,
                    "collection_name": collection_name,
                    "exists": False,
                    "error": "Collection not found"
                }
            
            vector_store = self.get_vector_store(client_id)
            collection = vector_store._collection
            
            return {
                "client_id": client_id,
                "collection_name": collection_name,
                "exists": True,
                "document_count": collection.count(),
                "last_modified": time.time()  # Could be enhanced to track actual modification time
            }
        except Exception as e:
            logger.error(f"Error getting stats for client {client_id}: {str(e)}")
            return {"client_id": client_id, "error": str(e)}
