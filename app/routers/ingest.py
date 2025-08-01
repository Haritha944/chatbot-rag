from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
from app.schemas.ingest import IngestResponse
from app.services.vector_store import VectorStoreService
from app.common.logger import get_logger
import time
import tempfile
import os

logger = get_logger(__name__)
router = APIRouter()

vector_store_service = VectorStoreService()

@router.post("/", response_model=IngestResponse)
async def ingest_documents(
    files: List[UploadFile] = File(..., description="Files to upload and ingest"),
    client_id: Optional[str] = Form(None, description="Optional client ID. If not provided, a new one will be generated"),
    chunk_size: int = Form(1000, description="Size of text chunks"),
    chunk_overlap: int = Form(200, description="Overlap between chunks")
):
    """
    Upload and ingest multiple documents into the vector store.
    
    - **files**: List of files to upload (PDF, TXT, DOCX, etc.)
    - **client_id**: Optional client ID for document isolation
    - **chunk_size**: Size of text chunks for processing
    - **chunk_overlap**: Overlap between text chunks
    """
    start_time = time.time()
    logger.info(f"Ingest request for {len(files)} files, client_id: {client_id}")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate file types
    allowed_extensions = {'.pdf', '.txt', '.docx', '.doc', '.md'}
    for file in files:
        if file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File type {ext} not supported. Allowed: {', '.join(allowed_extensions)}"
                )
    
    temp_files = []
    try:
        # Save uploaded files to temporary directory
        for file in files:
            if not file.filename:
                continue
                
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=os.path.splitext(file.filename)[1],
                prefix=f"upload_{file.filename.replace(' ', '_')}_"
            )
            
            # Write uploaded content to temp file
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            
            temp_files.append(temp_file.name)
            logger.info(f"Saved uploaded file: {file.filename} -> {temp_file.name}")
        
        if not temp_files:
            raise HTTPException(status_code=400, detail="No valid files to process")
        
        # Process files using existing vector store service
        result = await vector_store_service.ingest_documents(
            file_paths=temp_files,
            client_id=client_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        execution_time = time.time() - start_time
        logger.info(f"Ingest completed for client {result.client_id} in {execution_time:.4f}s")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Ingest error after {execution_time:.4f}s: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_file}: {str(e)}")