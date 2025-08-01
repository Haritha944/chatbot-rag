from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    client_id: Optional[str] = None  # ✅ Optional client_id
    session_id: Optional[str] = None
    use_memory: bool = True

class ChatResponse(BaseModel):
    response: str
    session_id: str
    client_id: str  # ✅ Return the client_id being used
    sources: List[Dict[str, Any]] = []
    memory_used: bool = True