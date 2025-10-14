"""
Init/Health Check Endpoint
Returns API status and basic information
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """
    Health check endpoint
    Returns API status and version information
    """
    return {
        "status": "ok",
        "message": "E-commerce Chatbot API is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/",
            "chat": "/api/chat",
            "metadata": "/api/metadata"
        }
    }
