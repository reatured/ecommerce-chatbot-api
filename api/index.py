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

# Import products router
from api.products import router as products_router

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include products router
app.include_router(products_router)




# Health check endpoint
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "E-commerce Chatbot API is running",
        "endpoints": {
            "init": "/api/init",
            "anthropic_chat": "/api/chat/anthropic/stream",
            "products_list": "/api/products?category={category}&color={color}",
            "products_search": "/api/products/search?q={query}",
            "product_by_id": "/api/products/{id}"
        },
        "notes": {
            "init": "Initialize app, wake up backend, get categories for quick actions (call on app load)",
            "anthropic_chat": "Accepts both JSON and multipart/form-data (file uploads)",
            "streaming": "Supports streaming toggle via 'stream' parameter (default: true)",
            "products_list": "Get all products with optional category and color filters",
            "products_search": "Search products by name, description, brand, tags, or color",
            "product_by_id": "Get detailed product information by ID"
        }
    }


# Helper function for Anthropic chat processing
async def _process_anthropic_chat(
    client,
    messages: list,
    model: str,
    max_tokens: int,
    stream: bool,
    system: Optional[str] = None
):
    """
    Internal helper to process Anthropic chat requests
    Returns either JSONResponse or StreamingResponse

    Args:
        messages: List of message dicts with 'role' and 'content' keys
    """
    from fastapi.responses import JSONResponse

    # Prepare request parameters
    request_params = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages
    }

    # Add system message if provided
    if system:
        request_params["system"] = system

    # Non-streaming mode
    if not stream:
        response = client.messages.create(**request_params)

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
            message_content_started = False
            message_content_ended = False
            buffer = ""
            emitted_buffer = ""  # Track what we've already emitted
            message_start_pos = -1
            message_end_pos = -1

            with client.messages.stream(**request_params) as stream:
                for text in stream.text_stream:
                    buffer += text

                    # Detect when we've found the complete "message": " pattern
                    if not message_content_started:
                        # Try pattern with space: "message": "
                        pattern1 = '"message": "'
                        pattern1_idx = buffer.find(pattern1)

                        if pattern1_idx != -1:
                            # Found complete pattern "message": "
                            message_start_pos = pattern1_idx + len(pattern1)
                            message_content_started = True

                            # Emit everything up to and including "message": " as metadata
                            metadata_to_emit = buffer[len(emitted_buffer):message_start_pos]
                            if metadata_to_emit:
                                yield f"data: {json.dumps({'type': 'metadata', 'delta': metadata_to_emit, 'index': 0})}\n\n"
                                emitted_buffer = buffer[:message_start_pos]
                            continue

                        # Try pattern without space: "message":"
                        pattern2 = '"message":"'
                        pattern2_idx = buffer.find(pattern2)

                        if pattern2_idx != -1:
                            # Found complete pattern "message":"
                            message_start_pos = pattern2_idx + len(pattern2)
                            message_content_started = True

                            # Emit everything up to and including "message":" as metadata
                            metadata_to_emit = buffer[len(emitted_buffer):message_start_pos]
                            if metadata_to_emit:
                                yield f"data: {json.dumps({'type': 'metadata', 'delta': metadata_to_emit, 'index': 0})}\n\n"
                                emitted_buffer = buffer[:message_start_pos]
                            continue

                        # Pattern not found yet, but might be split across chunks
                        # Only emit if we have enough buffer and pattern won't be split
                        safe_to_emit = len(buffer) - len(emitted_buffer) > 15  # "message": " is 12 chars
                        if safe_to_emit:
                            # Emit all but last 15 chars as metadata (keep buffer for pattern detection)
                            metadata_to_emit = buffer[len(emitted_buffer):-15]
                            if metadata_to_emit:
                                yield f"data: {json.dumps({'type': 'metadata', 'delta': metadata_to_emit, 'index': 0})}\n\n"
                                emitted_buffer += metadata_to_emit
                        continue

                    # Detect when message content ends (closing quote)
                    if message_content_started and not message_content_ended:
                        # Look for unescaped closing quote
                        content_so_far = buffer[message_start_pos:]

                        for i, char in enumerate(content_so_far):
                            if char == '"' and (i == 0 or content_so_far[i-1] != '\\'):
                                # Found the closing quote
                                message_end_pos = message_start_pos + i
                                message_content_ended = True

                                # Emit content (without the closing quote)
                                content_to_emit = buffer[len(emitted_buffer):message_end_pos]
                                if content_to_emit:
                                    yield f"data: {json.dumps({'type': 'content', 'delta': content_to_emit, 'index': 0})}\n\n"
                                    emitted_buffer = buffer[:message_end_pos]

                                # Emit the closing quote and anything after as metadata
                                metadata_to_emit = buffer[message_end_pos:len(buffer)]
                                if metadata_to_emit:
                                    yield f"data: {json.dumps({'type': 'metadata', 'delta': metadata_to_emit, 'index': 0})}\n\n"
                                    emitted_buffer = buffer
                                break

                        if not message_content_ended:
                            # Haven't found closing quote yet, emit content so far
                            content_to_emit = buffer[len(emitted_buffer):]
                            if content_to_emit:
                                yield f"data: {json.dumps({'type': 'content', 'delta': content_to_emit, 'index': 0})}\n\n"
                                emitted_buffer = buffer

                    # After message ended, everything is metadata
                    elif message_content_ended:
                        metadata_to_emit = buffer[len(emitted_buffer):]
                        if metadata_to_emit:
                            yield f"data: {json.dumps({'type': 'metadata', 'delta': metadata_to_emit, 'index': 0})}\n\n"
                            emitted_buffer = buffer

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
    message: str = Form(...),
    conversation_history: Optional[str] = Form(None),
    system: Optional[str] = Form(None),
    system_prompt: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    image_media_type: Optional[str] = Form("image/jpeg"),
    model: Optional[str] = Form("claude-3-5-haiku-latest"),
    max_tokens: Optional[int] = Form(1024),
    stream: Optional[bool] = Form(True)
):
    """
    Chat responses from Anthropic API with optional image support and conversation history.
    Accepts multipart/form-data with file upload.
    Supports both streaming and non-streaming modes via 'stream' parameter.

    Parameters:
    - message: User message text (required)
    - conversation_history: JSON string of previous messages (optional)
      Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    - system: System message to set AI behavior (optional)
    - system_prompt: Alternative name for system parameter (optional, takes precedence over 'system')
    - image: Image file upload (optional)
    - image_media_type: MIME type of image (default: image/jpeg)
    - model: Claude model to use (default: claude-3-5-haiku-latest)
    - max_tokens: Maximum tokens in response (default: 1024)
    - stream: Enable streaming mode (default: true)
    """
    try:
        from anthropic import Anthropic

        # Validate message is not empty
        if not message or not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

        client = Anthropic(api_key=api_key)

        # Build messages array
        messages = []

        # Add conversation history if provided
        if conversation_history:
            try:
                history = json.loads(conversation_history)
                if isinstance(history, list):
                    # Filter out messages with empty content
                    valid_history = [
                        msg for msg in history
                        if msg.get('content') and (
                            isinstance(msg['content'], str) and msg['content'].strip()
                            or isinstance(msg['content'], list) and len(msg['content']) > 0
                        )
                    ]
                    messages.extend(valid_history)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid conversation_history JSON format")

        # Process image input for current message
        img_base64 = None
        if image:
            # File upload
            image_data = await image.read()
            img_base64 = base64.b64encode(image_data).decode('utf-8')
            image_media_type = image.content_type or image_media_type

        # Prepare current message content
        if img_base64:
            # Include both image and text
            current_content = [
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
            current_content = message

        # Add current user message
        messages.append({
            "role": "user",
            "content": current_content
        })

        # Use system_prompt if provided, otherwise fall back to system
        final_system_prompt = system_prompt or system

        # Process request using helper function
        return await _process_anthropic_chat(client, messages, model, max_tokens, stream, final_system_prompt)

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
