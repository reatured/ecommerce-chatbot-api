"""
Chat Endpoint
Non-streaming chat completion with Claude
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from api.services.anthropic_client import chat_completion

router = APIRouter()


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request payload"""
    message: str = Field(..., description="User's message")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Optional conversation history"
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional system prompt (usually from frontend)"
    )
    model: Optional[str] = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model to use"
    )
    max_tokens: Optional[int] = Field(
        default=4096,
        description="Maximum tokens in response"
    )


class ChatResponse(BaseModel):
    """Chat response payload"""
    response: str
    model: str
    stop_reason: str
    usage: Dict


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat completion endpoint

    Sends message to Claude and returns JSON response (non-streaming)

    Request body:
    {
        "message": "What products do you have?",
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"}
        ],
        "system_prompt": "You are a helpful shopping assistant",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096
    }

    Response:
    {
        "response": "We have various products...",
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 123,
            "output_tokens": 456
        }
    }
    """
    try:
        # Convert Pydantic models to dicts for the service layer
        history = None
        if request.conversation_history:
            history = [msg.model_dump() for msg in request.conversation_history]

        # Call Anthropic service
        result = chat_completion(
            message=request.message,
            conversation_history=history,
            model=request.model,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat completion: {str(e)}")
