from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_chain import RAGChain
from app.services.vector_store import VectorStoreService
from app.common.logger import get_logger
import time

logger = get_logger(__name__)
router = APIRouter()

rag_chain = RAGChain()
vector_store_service = VectorStoreService()

@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    start_time = time.time()
    
    # ✅ Handle optional client_id
    if not request.client_id:
        raise HTTPException(status_code=400, detail={"error": "client_id is required","message": "Please provide a client_id to access your documents. Upload documents first to get a client_id.",
                "suggestion": "Use POST /api/v1/ingest/ to upload documents and get your client_id"})
    else:
        client_id = request.client_id
    
    logger.info(f"Chat request for client {client_id}, session: {request.session_id}")
    
    try:
        response = await rag_chain.get_response(
            message=request.message,
            client_id=client_id,  
            session_id=request.session_id,
            use_memory=request.use_memory
        )
        
        execution_time = time.time() - start_time
        logger.info(f"Chat response sent in {execution_time:.4f}s")
        return response
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Chat error after {execution_time:.4f}s: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def clear_session(session_id: str):
    logger.info(f"Clear session request: {session_id}")
    
    try:
        rag_chain.clear_session(session_id)  
        logger.info("Session cleared successfully")
        return {"message": f"Session {session_id} cleared"}
        
    except Exception as e:
        logger.error(f"Clear session error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collections")
async def list_client_collections():
    """List all client collections"""
    try:
        collections = vector_store_service.list_client_collections()
        return {
            "collections": collections,
            "total": len(collections)
        }
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collections/{client_id}/stats")
async def get_client_stats(client_id: str):
    """Get statistics for a specific client's collection"""
    try:
        stats = vector_store_service.get_client_stats(client_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting client stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/collections/{client_id}")
async def delete_client_collection(client_id: str):
    """Delete a specific client's collection"""
    try:
        vector_store_service.delete_collection(client_id)
        return {"message": f"Collection for client {client_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting client collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))