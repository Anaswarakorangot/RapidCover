from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict
from app.services.ai_service import get_rapidbot_response

router = APIRouter(prefix="/ai", tags=["AI RapidBot"])

class ChatMessage(BaseModel):
    role: str # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    response: str
    status: str = "success"

@router.post("/chat", response_model=ChatResponse)
async def chat_with_rapidbot(request: ChatRequest):
    """
    Direct endpoint for RapidBot chat.
    Sends message history to Groq via the AI service.
    """
    try:
        # Convert Pydantic models to dicts for the service
        messages_dict = [{"role": m.role, "content": m.content} for m in request.messages]
        
        # Get response from Groq
        response_text = await get_rapidbot_response(messages_dict)
        
        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
