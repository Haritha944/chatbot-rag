#!/usr/bin/env python3
"""
Startup script for Conversational RAG API with SQLite session storage
"""
import os
import sys
import uvicorn
from app.main import app
from app.config import settings
from app.common.logger import get_logger

logger = get_logger(__name__)

def main():
    """Start the Conversational RAG API server"""
    
    # Print startup banner
    print("=" * 60)
    print("🚀 Conversational RAG API with SQLite Sessions")
    print("=" * 60)
    print(f"📝 Model: {settings.model_name}")
    print(f"🗄️ Session Storage: {settings.session_store_type}")
    print(f"💾 Database: {settings.session_db_path}")
    print(f"🔧 Vector Store: {settings.vector_store_type}")
    print("=" * 60)
    
    # Check environment variables
    if not settings.groq_api_key:
        print("⚠️  WARNING: GROQ_API_KEY not set in environment!")
        print("   Please set your Groq API key in .env file")
        print("   Example: GROQ_API_KEY=your_groq_api_key_here")
        sys.exit(1)
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(settings.session_db_path), exist_ok=True)
    
    # Start server
    logger.info("Starting Conversational RAG API server...")
    print(f"🌐 Server starting at: http://localhost:8000")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"❤️  Health Check: http://localhost:8000/health")
    print(f"📊 Session Stats: http://localhost:8000/api/v1/sessions/stats")
    print("=" * 60)
    
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown by user")
        print("\n👋 Server stopped gracefully")

if __name__ == "__main__":
    main()
