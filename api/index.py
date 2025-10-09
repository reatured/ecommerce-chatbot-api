import os
import json
import base64
from typing import Optional, Union
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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




# Health check endpoint
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "E-commerce Chatbot API is running",
        "endpoints": {
            "perplexity_chat": "/api/chat/perplexity/stream",
            "anthropic_chat": "/api/chat/anthropic/stream"
        },
        "notes": {
            "anthropic_chat": "Accepts both JSON and multipart/form-data (file uploads)",
            "streaming": "All endpoints support streaming toggle via 'stream' parameter (default: true)"
        }
    }


# Perplexity Search Endpoint
@app.post("/api/chat/perplexity/stream")
async def perplexity_search_stream(
    query: str,
    stream: Optional[bool] = True
):
    """
    Chat completion responses from Perplexity API using chat.completions.create
    Supports both streaming and non-streaming modes via 'stream' parameter
    """
    try:
        # Import here to avoid module-level initialization issues
        from perplexity import Perplexity
        from fastapi.responses import JSONResponse

        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="PERPLEXITY_API_KEY not configured")

        client = Perplexity(api_key=api_key)

        # Non-streaming mode
        if not stream:
            try:
                completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": query
                        }
                    ],
                    model="sonar",
                    stream=False
                )

                # Return complete response
                response_data = {
                    "type": "complete",
                    "content": completion.choices[0].message.content,
                    "finish_reason": completion.choices[0].finish_reason if hasattr(completion.choices[0], 'finish_reason') else "stop",
                    "model": completion.model if hasattr(completion, 'model') else "sonar",
                    "usage": {
                        "prompt_tokens": completion.usage.prompt_tokens if hasattr(completion, 'usage') else None,
                        "completion_tokens": completion.usage.completion_tokens if hasattr(completion, 'usage') else None,
                        "total_tokens": completion.usage.total_tokens if hasattr(completion, 'usage') else None
                    } if hasattr(completion, 'usage') else None
                }
                return JSONResponse(content=response_data)

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Streaming mode
        async def generate():
            try:
                stream_response = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": query
                        }
                    ],
                    model="sonar",
                    stream=True
                )

                # Stream chunks as they arrive
                for chunk in stream_response:
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


# Helper function for Anthropic chat processing
async def _process_anthropic_chat(
    client,
    content,
    model: str,
    max_tokens: int,
    stream: bool
):
    """
    Internal helper to process Anthropic chat requests
    Returns either JSONResponse or StreamingResponse
    """
    from fastapi.responses import JSONResponse

    # Non-streaming mode
    if not stream:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{
                "role": "user",
                "content": content
            }]
        )

        # Return complete response
        response_data = {
            "type": "complete",
            "content": response.content[0].text if response.content else "",
            "finish_reason": response.stop_reason if hasattr(response, 'stop_reason') else "stop",
            "model": response.model if hasattr(response, 'model') else model,
            "usage": {
                "input_tokens": response.usage.input_tokens if hasattr(response, 'usage') else None,
                "output_tokens": response.usage.output_tokens if hasattr(response, 'usage') else None
            } if hasattr(response, 'usage') else None
        }
        return JSONResponse(content=response_data)

    # Streaming mode
    async def generate():
        try:
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


# Anthropic Chat Endpoint
@app.post("/api/chat/anthropic/stream")
async def anthropic_chat_stream(
    message: str,
    image: Optional[Union[str, UploadFile]] = None,
    image_media_type: Optional[str] = "image/jpeg",
    model: Optional[str] = "claude-3-5-sonnet-20241022",
    max_tokens: Optional[int] = 1024,
    stream: Optional[bool] = True
):
    """
    Chat responses from Anthropic API with optional image support.
    Accepts both JSON and multipart/form-data (file upload).
    Supports both streaming and non-streaming modes via 'stream' parameter.

    Parameters:
    - message: User message text
    - image: Either base64 string (JSON) or file upload (form-data)
    - image_media_type: MIME type of image (default: image/jpeg)
    - model: Claude model to use
    - max_tokens: Maximum tokens in response
    - stream: Enable streaming mode (default: true)
    """
    try:
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

        client = Anthropic(api_key=api_key)

        # Process image input
        img_base64 = None
        if image:
            if isinstance(image, UploadFile):
                # File upload
                image_data = await image.read()
                img_base64 = base64.b64encode(image_data).decode('utf-8')
                image_media_type = image.content_type or image_media_type
            elif isinstance(image, str) and image.strip():
                # Base64 string from JSON
                img_base64 = image

        # Prepare message content
        if img_base64:
            # Include both image and text
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": img_base64
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

        # Process request using helper function
        return await _process_anthropic_chat(client, content, model, max_tokens, stream)

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
