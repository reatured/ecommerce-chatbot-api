from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from anthropic import Anthropic
from dotenv import load_dotenv
import os, json, base64
import time

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="E-commerce Chatbot API")

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log incoming request
    print(f"\n{'='*70}")
    print(f"🌐 INCOMING REQUEST")
    print(f"{'='*70}")
    print(f"Method: {request.method}")
    print(f"Path: {request.url.path}")
    print(f"Client: {request.client.host if request.client else 'unknown'}")
    print(f"User-Agent: {request.headers.get('user-agent', 'unknown')[:80]}")
    print(f"{'='*70}\n")

    # Process request
    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    print(f"✅ Response: {response.status_code} | Time: {process_time:.3f}s\n")

    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include products router
from api.products import router as products_router
app.include_router(products_router)

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {
        "status": "ok",
        "message": "E-commerce Chatbot API is running",
        "endpoints": {
            "chat": "/api/chat/anthropic/stream",
            "products": "/api/products",
            "docs": "/docs"
        }
    }

@app.post("/api/chat/anthropic/stream")
async def anthropic_chat_stream(
    message: str = Form("Hello, what can you do?"),
    system_prompt: str | None = Form(None),
    request: Request = None
):
    """🚀 Simple Claude Chat Endpoint (No safety checks, for testing)
    - Supports optional `system` or `system_prompt`
    - Accepts text or optional image
    - Returns direct text response from Claude
    """
    # Parse multipart form data manually to handle all fields including empty image
    form = await request.form()

    # Extract remaining form fields with defaults
    conversation_history = form.get("conversation_history", '[{"role": "assistant", "content": "Hi there! I am your shopping assistant."}]')
    system = form.get("system", "You are a friendly e-commerce chatbot that helps users find products.")
    image_media_type = form.get("image_media_type", "image/jpeg")
    model = form.get("model", "claude-3-5-haiku-latest")

    # Handle max_tokens - convert to int
    try:
        max_tokens = int(form.get("max_tokens", 512))
    except (ValueError, TypeError):
        max_tokens = 512

    # Handle image field - convert empty string to None
    image_field = form.get("image")
    image = None
    if image_field and isinstance(image_field, UploadFile) and image_field.filename:
        image = image_field

    # 📨 LOG INCOMING REQUEST
    print("\n" + "🔷"*35)
    print("📨 NEW CHAT REQUEST RECEIVED")
    print("🔷"*35)
    print(f"Message: {message[:100]}..." if len(message) > 100 else f"Message: {message}")
    print(f"Model: {model}")
    print(f"Max Tokens: {max_tokens}")
    print(f"Has Image: {'Yes' if image else 'No'}")
    print("🔷"*35 + "\n")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ERROR: ANTHROPIC_API_KEY not found in environment\n")
        raise HTTPException(status_code=500, detail="Missing ANTHROPIC_API_KEY")

    client = Anthropic(api_key=api_key)
    messages = []

    # Add conversation history if provided
    if conversation_history:
        try:
            messages.extend(json.loads(conversation_history))
        except Exception:
            pass  # ignore errors, no validation

    # Handle image (optional)
    # Check if image is actually an UploadFile and has content
    if image and isinstance(image, UploadFile) and image.filename:
        img_data = await image.read()
        if img_data:  # Only process if there's actual data
            img_b64 = base64.b64encode(img_data).decode("utf-8")
            content = [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": image.content_type or image_media_type,
                    "data": img_b64
                }},
                {"type": "text", "text": message}
            ]
        else:
            content = message
    else:
        content = message

    messages.append({"role": "user", "content": content})

    # Combine system + system_prompt
    system_msg = system_prompt or system or ""

    # 📤 LOG REQUEST TO CLAUDE
    print("\n" + "="*70)
    print("📤 SENDING TO CLAUDE")
    print("="*70)
    print(f"Model: {model}")
    print(f"Max Tokens: {max_tokens}")
    print(f"System Prompt: {system_msg[:200]}..." if len(system_msg) > 200 else f"System Prompt: {system_msg}")
    print(f"\nMessages ({len(messages)} total):")
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, str):
            preview = content[:150] + "..." if len(content) > 150 else content
            print(f"  [{i}] {role}: {preview}")
        elif isinstance(content, list):
            print(f"  [{i}] {role}: [multipart content with {len(content)} parts]")
            for j, part in enumerate(content):
                if part.get("type") == "text":
                    text = part.get("text", "")
                    preview = text[:100] + "..." if len(text) > 100 else text
                    print(f"       - text: {preview}")
                elif part.get("type") == "image":
                    print(f"       - image: base64 data ({len(part.get('source', {}).get('data', ''))} chars)")
    print("="*70 + "\n")

    # Get Claude response
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_msg,
            messages=messages
        )

        # 📥 LOG RESPONSE FROM CLAUDE
        reply_text = resp.content[0].text
        print("\n" + "="*70)
        print("📥 RECEIVED FROM CLAUDE")
        print("="*70)
        print(f"Model: {resp.model}")
        print(f"Stop Reason: {resp.stop_reason}")
        print(f"Usage: {resp.usage.input_tokens} input tokens, {resp.usage.output_tokens} output tokens")
        print(f"\nResponse ({len(reply_text)} chars):")
        print(reply_text)
        print("="*70 + "\n")

        return {"reply": reply_text}
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))
