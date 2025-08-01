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
    
    # Memory Settings
    memory_type: str = "buffer"  # buffer, summary, buffer_window
    max_token_limit: int = 2000
    
    # Session Storage Settings (SQLite Only)
    session_store_type: str = "sqlite"  # Always SQLite for production
    session_db_path: str = "./data/sessions.db"  # SQLite database path
    session_ttl: int = 3600  # 1 hour session expiration
    
    # Production Settings
    max_cached_sessions: int = 100
    cleanup_interval: int = 300  # 5 minutes
    
    # ✅ Connection pooling settings
    db_connection_pool_size: int = 10
    max_concurrent_requests: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()