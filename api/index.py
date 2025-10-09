import os
import json
import base64
from typing import Optional
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="E-commerce Chatbot API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Models
class PerplexitySearchRequest(BaseModel):
    query: str


class AnthropicChatRequest(BaseModel):
    message: str
    image: Optional[str] = None
    image_media_type: Optional[str] = "image/jpeg"
    model: Optional[str] = "claude-3-5-sonnet-20241022"
    max_tokens: Optional[int] = 1024


# Health check endpoint
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "E-commerce Chatbot API is running",
        "endpoints": {
            "perplexity_search": "/api/chat/perplexity/stream",
            "anthropic_chat": "/api/chat/anthropic/stream",
            "anthropic_chat_upload": "/api/chat/anthropic/stream/upload"
        }
    }


# Perplexity Search Streaming Endpoint
@app.post("/api/chat/perplexity/stream")
async def perplexity_search_stream(request: PerplexitySearchRequest):
    """
    Stream chat completion responses from Perplexity API using chat.completions.create
    Returns streaming response compatible with OpenAI format
    """
    try:
        async def generate():
            try:
                # Import here to avoid module-level initialization issues
                from perplexity import Perplexity

                api_key = os.getenv("PERPLEXITY_API_KEY")
                if not api_key:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'PERPLEXITY_API_KEY not configured'})}\n\n"
                    return

                client = Perplexity(api_key=api_key)

                # Use chat completions API with streaming
                stream = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": request.query
                        }
                    ],
                    model="sonar",
                    stream=True
                )

                # Stream chunks as they arrive
                for chunk in stream:
                    if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta

                        # Stream content
                        if hasattr(delta, 'content') and delta.content:
                            chunk_data = {
                                "type": "content",
                                "delta": delta.content,
                                "index": chunk.choices[0].index
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"

                        # Handle finish reason
                        if hasattr(chunk.choices[0], 'finish_reason') and chunk.choices[0].finish_reason:
                            finish_data = {
                                "type": "finish",
                                "finish_reason": chunk.choices[0].finish_reason
                            }
                            yield f"data: {json.dumps(finish_data)}\n\n"

                # Send completion message
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                error_data = {"type": "error", "message": str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Anthropic Chat Streaming Endpoint
@app.post("/api/chat/anthropic/stream")
async def anthropic_chat_stream(request: AnthropicChatRequest):
    """
    Stream chat responses from Anthropic API with optional image support
    """
    try:
        async def generate():
            try:
                # Import here to avoid module-level initialization issues
                from anthropic import Anthropic

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'ANTHROPIC_API_KEY not configured'})}\n\n"
                    return

                client = Anthropic(api_key=api_key)

                # Prepare message content
                # If no image is provided, send text-only message
                if not request.image or not request.image.strip():
                    content = request.message
                else:
                    # Include both image and text
                    content = [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": request.image_media_type,
                                "data": request.image
                            }
                        },
                        {
                            "type": "text",
                            "text": request.message
                        }
                    ]

                # Create streaming request
                with client.messages.stream(
                    model=request.model,
                    max_tokens=request.max_tokens,
                    messages=[{
                        "role": "user",
                        "content": content
                    }]
                ) as stream:
                    for text in stream.text_stream:
                        chunk_data = {
                            "type": "content",
                            "delta": text,
                            "index": 0
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                    # Get the final response message
                    final_message = stream.get_final_message()

                    # Send finish reason
                    finish_data = {
                        "type": "finish",
                        "finish_reason": final_message.stop_reason if hasattr(final_message, 'stop_reason') else "stop"
                    }
                    yield f"data: {json.dumps(finish_data)}\n\n"

                # Send completion message
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                error_data = {"type": "error", "message": str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Anthropic Chat with File Upload (for easier testing in /docs)
@app.post("/api/chat/anthropic/stream/upload")
async def anthropic_chat_stream_upload(
    message: str = Form(...),
    image: Optional[UploadFile] = File(None),
    model: Optional[str] = Form("claude-3-5-sonnet-20241022"),
    max_tokens: Optional[int] = Form(1024)
):
    """
    Stream chat responses from Anthropic API with file upload support.
    This endpoint is optimized for testing in FastAPI /docs UI.
    """
    try:
        # Read image data BEFORE the generator function
        image_base64 = None
        image_media_type = None

        if image:
            image_data = await image.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_media_type = image.content_type or "image/jpeg"

        async def generate():
            try:
                from anthropic import Anthropic

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'ANTHROPIC_API_KEY not configured'})}\n\n"
                    return

                client = Anthropic(api_key=api_key)

                # Prepare message content
                if image_base64:
                    # Include both image and text
                    content = [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_media_type,
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": message
                        }
                    ]
                else:
                    # Text only
                    content = message

                # Create streaming request
                with client.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{
                        "role": "user",
                        "content": content
                    }]
                ) as stream:
                    for text in stream.text_stream:
                        chunk_data = {
                            "type": "content",
                            "delta": text,
                            "index": 0
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                    # Get the final response message
                    final_message = stream.get_final_message()

                    # Send finish reason
                    finish_data = {
                        "type": "finish",
                        "finish_reason": final_message.stop_reason if hasattr(final_message, 'stop_reason') else "stop"
                    }
                    yield f"data: {json.dumps(finish_data)}\n\n"

                # Send completion message
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                error_data = {"type": "error", "message": str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# For Vercel serverless function
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    pass

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
