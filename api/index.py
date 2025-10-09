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
    Stream search results from Perplexity API
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

                # Perform search
                # Note: Only query is required, other params may not be supported in all SDK versions
                search_params = {
                    "query": request.query
                }

                search_result = client.search.create(**search_params)

                # Stream the search ID first
                yield f"data: {json.dumps({'type': 'search_id', 'id': search_result.id})}\n\n"

                # Stream each result
                for idx, result in enumerate(search_result.results):
                    result_data = {
                        "type": "result",
                        "index": idx,
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet,
                        "date": getattr(result, 'date', None),
                        "last_updated": getattr(result, 'last_updated', None)
                    }
                    yield f"data: {json.dumps(result_data)}\n\n"
                    await asyncio.sleep(0.1)

                # Send completion message
                yield f"data: {json.dumps({'type': 'done', 'total_results': len(search_result.results)})}\n\n"

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
                            "text": text
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

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
        async def generate():
            try:
                from anthropic import Anthropic

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'ANTHROPIC_API_KEY not configured'})}\n\n"
                    return

                client = Anthropic(api_key=api_key)

                # Prepare message content
                content = []

                # Add image if uploaded
                if image:
                    # Read file and convert to base64
                    image_data = await image.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')

                    # Determine media type from content_type
                    media_type = image.content_type or "image/jpeg"

                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image
                        }
                    })

                # Add text message
                content.append({
                    "type": "text",
                    "text": message
                })

                # If only text, simplify content
                if len(content) == 1:
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
                            "text": text
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

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
