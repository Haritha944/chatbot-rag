from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from ..services.rag_chain import RAGChain
from ..memory import SessionStore
from ..common.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/{session_id}/info")
async def get_session_info(session_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific session"""
    try:
        store = SessionStore()
        if hasattr(store, 'get_session_info'):
            session_info = store.get_session_info(session_id)
            if not session_info:
                raise HTTPException(status_code=404, detail="Session not found")
            return session_info
        else:
            raise HTTPException(status_code=501, detail="Session info not available with current storage type")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session information")

@router.delete("/{session_id}")
async def clear_session(session_id: str) -> Dict[str, str]:
    """Clear a specific session"""
    try:
        rag_chain = RAGChain()
        rag_chain.clear_session(session_id)
        return {"message": f"Session {session_id} cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear session")

@router.post("/cleanup")
async def cleanup_expired_sessions() -> Dict[str, Any]:
    """Manually trigger cleanup of expired sessions"""
    try:
        rag_chain = RAGChain()
        rag_chain.cleanup_expired_sessions()
        
        # Get updated stats
        stats = rag_chain.get_session_stats()
        return {
            "message": "Expired sessions cleaned up successfully",
            "current_stats": stats
        }
    except Exception as e:
        logger.error(f"Error during session cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup sessions")
