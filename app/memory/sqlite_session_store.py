import sqlite3
import json
import time
import os
import asyncio
from typing import List, Dict, Any, Optional
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from contextlib import contextmanager
import threading
from concurrent.futures import ThreadPoolExecutor

from ..config import settings
from ..common.logger import get_logger

logger = get_logger(__name__)


class SQLiteSessionStore:
    """Production-ready SQLite session storage with connection pooling"""
    
    def __init__(self):
        self.db_path = settings.session_db_path
        self._local = threading.local()  # Initialize threading local first
        
        # ✅ Connection pooling for better concurrency
        self._pool_size = getattr(settings, 'db_connection_pool_size', 10)
        self._executor = ThreadPoolExecutor(max_workers=self._pool_size)
        
        self._ensure_db_dir()
        self._init_database()
        logger.info(f"SQLite session store initialized with connection pool (size: {self._pool_size}): {self.db_path}")
    
    def _ensure_db_dir(self):
        """Ensure database directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                        ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_expires 
                ON sessions (expires_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session 
                ON messages (session_id, timestamp)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get thread-safe database connection with improved pooling"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0,  # 30 second timeout
                isolation_level=None  # ✅ Enable autocommit for better concurrency
            )
            self._local.connection.row_factory = sqlite3.Row  # Dict-like access
            
            # ✅ Optimize SQLite settings for concurrent access
            self._local.connection.execute("PRAGMA journal_mode=WAL")  # Better concurrency
            self._local.connection.execute("PRAGMA synchronous=NORMAL")  # Balanced safety/performance
            self._local.connection.execute("PRAGMA cache_size=10000")  # 10MB cache
            self._local.connection.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
        
        try:
            yield self._local.connection
        except Exception as e:
            if self._local.connection:
                self._local.connection.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
    
    def get_session(self, session_id: str) -> List[BaseMessage]:
        """Get session chat history"""
        try:
            with self._get_connection() as conn:
                # Check if session exists and is not expired
                session = conn.execute("""
                    SELECT * FROM sessions 
                    WHERE session_id = ? AND expires_at > ?
                """, (session_id, time.time())).fetchone()
                
                if not session:
                    return []
                
                # Update last accessed
                conn.execute("""
                    UPDATE sessions 
                    SET last_accessed = ? 
                    WHERE session_id = ?
                """, (time.time(), session_id))
                
                # Get messages
                messages_data = conn.execute("""
                    SELECT role, content FROM messages 
                    WHERE session_id = ? 
                    ORDER BY timestamp ASC
                """, (session_id,)).fetchall()
                
                conn.commit()
                
                # Convert to LangChain messages
                messages = []
                for msg in messages_data:
                    if msg['role'] == 'user':
                        messages.append(HumanMessage(content=msg['content']))
                    elif msg['role'] == 'assistant':
                        messages.append(AIMessage(content=msg['content']))
                
                return messages
                
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {str(e)}")
            return []
    
    async def get_session_async(self, session_id: str) -> List[BaseMessage]:
        """Async version of get_session for better concurrency"""
        return await asyncio.get_event_loop().run_in_executor(
            self._executor, self.get_session, session_id
        )
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add message to session"""
        try:
            current_time = time.time()
            expires_at = current_time + settings.session_ttl
            
            with self._get_connection() as conn:
                # Create or update session
                conn.execute("""
                    INSERT OR REPLACE INTO sessions 
                    (session_id, created_at, last_accessed, expires_at, message_count)
                    VALUES (
                        ?, 
                        COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?),
                        ?, 
                        ?,
                        (SELECT COUNT(*) FROM messages WHERE session_id = ?) + 1
                    )
                """, (session_id, session_id, current_time, current_time, expires_at, session_id))
                
                # Add message
                conn.execute("""
                    INSERT INTO messages (session_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (session_id, role, content, current_time))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving message for session {session_id}: {str(e)}")
    
    async def add_message_async(self, session_id: str, role: str, content: str):
        """Async version of add_message for better concurrency"""
        return await asyncio.get_event_loop().run_in_executor(
            self._executor, self.add_message, session_id, role, content
        )
    
    def clear_session(self, session_id: str):
        """Clear session and all its messages"""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                # Messages will be deleted automatically due to CASCADE
                conn.commit()
                logger.info(f"Session {session_id} cleared from database")
                
        except Exception as e:
            logger.error(f"Error clearing session {session_id}: {str(e)}")
    
    def list_sessions(self) -> List[str]:
        """List all active (non-expired) sessions"""
        try:
            with self._get_connection() as conn:
                sessions = conn.execute("""
                    SELECT session_id FROM sessions 
                    WHERE expires_at > ?
                """, (time.time(),)).fetchall()
                
                return [session['session_id'] for session in sessions]
                
        except Exception as e:
            logger.error(f"Error listing sessions: {str(e)}")
            return []
    
    def cleanup_expired_sessions(self) -> List[str]:
        """Clean up expired sessions and return their IDs"""
        try:
            with self._get_connection() as conn:
                # Get expired session IDs
                expired = conn.execute("""
                    SELECT session_id FROM sessions 
                    WHERE expires_at <= ?
                """, (time.time(),)).fetchall()
                
                expired_ids = [session['session_id'] for session in expired]
                
                # Delete expired sessions
                if expired_ids:
                    conn.execute("""
                        DELETE FROM sessions 
                        WHERE expires_at <= ?
                    """, (time.time(),))
                    conn.commit()
                    logger.info(f"Cleaned up {len(expired_ids)} expired sessions")
                
                return expired_ids
                
        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
            return []
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        try:
            with self._get_connection() as conn:
                session = conn.execute("""
                    SELECT session_id, created_at, last_accessed, expires_at, message_count
                    FROM sessions 
                    WHERE session_id = ?
                """, (session_id,)).fetchone()
                
                if not session:
                    return None
                
                return {
                    'session_id': session['session_id'],
                    'message_count': session['message_count'],
                    'created_at': session['created_at'],
                    'last_accessed': session['last_accessed'],
                    'expires_at': session['expires_at'],
                    'is_expired': session['expires_at'] <= time.time()
                }
                
        except Exception as e:
            logger.error(f"Error getting session info {session_id}: {str(e)}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self._get_connection() as conn:
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_sessions,
                        COUNT(CASE WHEN expires_at > ? THEN 1 END) as active_sessions,
                        SUM(message_count) as total_messages,
                        AVG(message_count) as avg_messages_per_session
                    FROM sessions
                """, (time.time(),)).fetchone()
                
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    'total_sessions': stats['total_sessions'],
                    'active_sessions': stats['active_sessions'],
                    'total_messages': stats['total_messages'] or 0,
                    'avg_messages_per_session': round(stats['avg_messages_per_session'] or 0, 2),
                    'database_size_mb': round(db_size / (1024 * 1024), 2)
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {}
    
    # Legacy properties for compatibility with existing code
    @property
    def sessions(self) -> Dict[str, Any]:
        """Legacy property for compatibility - returns session stats"""
        stats = self.get_stats()
        return {'count': stats.get('active_sessions', 0)}
