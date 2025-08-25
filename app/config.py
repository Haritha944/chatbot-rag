from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # LLM Settings
    groq_api_key: Optional[str] = None
    model_name: str = "llama-3.3-70b-versatile"  # Default Groq model
    temperature: float = 0.7
    
    # Vector Store Settings
    vector_store_type: str = "chroma"  # or "faiss"
    vector_store_path: str = "./chroma_db"
    
    # Memory Settings (Optimized for 512MB limit)
    memory_type: str = "buffer_window"  # Use buffer_window instead of buffer
    max_token_limit: int = 1000  # Reduced from 2000
    
    # Session Storage Settings (SQLite Only) - Memory Optimized
    session_store_type: str = "sqlite"  # Always SQLite for production
    session_db_path: str = "./data/sessions.db"  # SQLite database path
    session_ttl: int = 1800  # Reduced to 30 minutes (was 1 hour)
    
    # Production Settings (Memory Optimized)
    max_cached_sessions: int = 25  # Reduced from 100
    cleanup_interval: int = 180  # Reduced to 3 minutes (was 5)
    
    # ✅ Connection pooling settings (Memory Optimized)
    db_connection_pool_size: int = 3  # Reduced from 10
    max_concurrent_requests: int = 10  # Reduced from 50
    
    # HuggingFace Cache Settings (Optional - for deployment environments)
    hf_home: Optional[str] = None
    transformers_cache: Optional[str] = None
    hf_datasets_cache: Optional[str] = None
    preload_model: Optional[str] = None
    tokenizers_parallelism: Optional[str] = None
    omp_num_threads: Optional[str] = None
    pytorch_transformers_cache: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables

settings = Settings()