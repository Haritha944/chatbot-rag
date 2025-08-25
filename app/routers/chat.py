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

