from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import time
from app.routers import chat, ingest, sessions
from app.config import settings
from app.common.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Conversational RAG API",
    description="LangChain-based conversational RAG system with Groq",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Document Ingestion"]) 
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Session Management"])

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Conversational RAG API with SQLite session storage")
    logger.info(f"Model: {settings.model_name}, Vector Store: {settings.vector_store_type}")
    logger.info(f"Session Storage: {settings.session_store_type}, Database: {settings.session_db_path}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Conversational RAG API")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "model": settings.model_name,
        "vector_store": settings.vector_store_type,
        "session_storage": settings.session_store_type,
        "database_path": settings.session_db_path
    }

if __name__ == "__main__":
    logger.info("Starting server")
    uvicorn.run(app, host="0.0.0.0", port=8000)