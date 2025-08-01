from ..config import settings
from ..common.logger import get_logger
from .sqlite_session_store import SQLiteSessionStore

logger = get_logger(__name__)

def get_session_store():
    """Get SQLite session store - production ready storage"""
    return SQLiteSessionStore()

# Export as SessionStore for backward compatibility
SessionStore = get_session_store
