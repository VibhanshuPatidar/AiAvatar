from pydantic import BaseModel
from typing import List, Dict, Any

class ChatRequest(BaseModel):
    message: str

class MessageData(BaseModel):
    text: str
    audio: str
    lipsync: str
    facialExpression: str
    animation: str

class ChatResponse(BaseModel):
    messages: List[MessageData]
