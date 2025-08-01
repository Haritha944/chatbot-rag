from pydantic import BaseModel, Field
from typing import List, Optional

# Note: For file uploads, we'll use FastAPI's UploadFile directly in the router
# This schema is for query parameters only
class IngestQueryParams(BaseModel):
    chunk_size: int = Field(1000, description="Size of text chunks")
    chunk_overlap: int = Field(200, description="Overlap between chunks")
    client_id: Optional[str] = Field(
        None, 
        description="Optional client ID. If not provided, a new client ID will be generated",
        example=None
    )

class IngestResponse(BaseModel):
    message: str
    documents_processed: int
    chunks_created: int
    client_id: str = Field(..., description="Client ID (generated or provided)", example="client_a1b2c3d4")