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

# Import tool use functions
from api.tools import get_all_tools, execute_tool

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
    image: UploadFile | None = File(None),
    request: Request = None
):
    """🚀 Simple Claude Chat Endpoint (No safety checks, for testing)
    - Accepts text message and optional image
    - Frontend combines system prompt with message before sending
    - Returns direct text response from Claude
    """
    # Parse multipart form data manually to handle all fields including empty image
    form = await request.form()

    # Extract remaining form fields with defaults
    conversation_history = form.get("conversation_history", '[{"role": "assistant", "content": "Hi there! I am your shopping assistant."}]')
    image_media_type = form.get("image_media_type", "image/jpeg")
    model = form.get("model", "claude-3-5-haiku-latest")

    # Handle max_tokens - convert to int
    try:
        max_tokens = int(form.get("max_tokens", 512))
    except (ValueError, TypeError):
        max_tokens = 512

    # Image is now passed as a function parameter, no need to extract from form

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
    print(f"🖼️  IMAGE DEBUG:")
    print(f"   - image exists: {image is not None}")
    print(f"   - image type: {type(image)}")
    print(f"   - isinstance UploadFile: {isinstance(image, UploadFile) if image else 'N/A'}")
    if image:
        print(f"   - image.filename: {getattr(image, 'filename', 'NO ATTR')}")
        print(f"   - image.content_type: {getattr(image, 'content_type', 'NO ATTR')}")

    if image:
        print("   ✅ Entering image processing block")
        img_data = await image.read()
        print(f"   - img_data length: {len(img_data) if img_data else 0} bytes")
        if img_data:  # Only process if there's actual data
            print("   ✅ img_data has content, encoding to base64...")
            img_b64 = base64.b64encode(img_data).decode("utf-8")
            content = [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": image.content_type or image_media_type,
                    "data": img_b64
                }},
                {"type": "text", "text": message}
            ]
            print("   ✅ Created multipart content with image")
        else:
            print("   ❌ img_data is empty, falling back to text-only")
            content = message
    else:
        print("   ❌ Image check failed, using text-only content")
        content = message

    messages.append({"role": "user", "content": content})

    # 📤 LOG REQUEST TO CLAUDE
    print("\n" + "="*70)
    print("📤 SENDING TO CLAUDE")
    print("="*70)
    print(f"Model: {model}")
    print(f"Max Tokens: {max_tokens}")
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

    # Get Claude response with tool use support
    try:
        # System instruction for tool use
        system_instruction = """You are a helpful shopping assistant with access to a product database.

CRITICAL RULES FOR TOOL USE:
1. ALWAYS use search_products or filter_products tools IMMEDIATELY when user mentions:
   - Any brand name (e.g., "BMW", "Nike", "Sony")
   - Any product type (e.g., "sedan", "backpack", "laptop")
   - Any category or color
2. NEVER suggest or mention specific product models without first checking the database
3. ONLY present products that exist in the tool results - do not make up or suggest products
4. When presenting products, include ALL product details returned by the tool (name, price, color, description, etc.)

When you receive product data from tools, present it naturally and include all the product information so users can see details."""

        # Initial request with tools
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system_instruction,
            tools=get_all_tools()  # Add tool definitions
        )

        # 📥 LOG RESPONSE FROM CLAUDE
        print("\n" + "="*70)
        print("📥 RECEIVED FROM CLAUDE")
        print("="*70)
        print(f"Model: {resp.model}")
        print(f"Stop Reason: {resp.stop_reason}")
        print(f"Usage: {resp.usage.input_tokens} input tokens, {resp.usage.output_tokens} output tokens")
        print("="*70 + "\n")

        # Tool Use Loop - handle tool calls from Claude
        while resp.stop_reason == "tool_use":
            print("\n" + "🔧"*35)
            print("🔧 TOOL USE DETECTED")
            print("🔧"*35)

            # Extract tool use blocks
            tool_use_blocks = [block for block in resp.content if block.type == "tool_use"]

            # Add assistant's response to conversation
            messages.append({
                "role": "assistant",
                "content": resp.content
            })

            # Execute each tool and collect results
            tool_results = []
            for tool_block in tool_use_blocks:
                tool_name = tool_block.name
                tool_input = tool_block.input
                tool_use_id = tool_block.id

                print(f"\n🔧 Executing tool: {tool_name}")
                print(f"   Input: {tool_input}")

                # Execute the tool
                result = execute_tool(tool_name, tool_input)

                print(f"   Result: {result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result)
                })

            # Add tool results to conversation
            messages.append({
                "role": "user",
                "content": tool_results
            })

            print("🔧"*35 + "\n")

            # Continue conversation with tool results
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
                system=system_instruction,
                tools=get_all_tools()
            )

            print("\n" + "="*70)
            print("📥 RECEIVED FROM CLAUDE (after tool use)")
            print("="*70)
            print(f"Stop Reason: {resp.stop_reason}")
            print("="*70 + "\n")

        # Extract final text response
        reply_text = ""
        for block in resp.content:
            if hasattr(block, "text"):
                reply_text += block.text

        print(f"\n✅ Final Response ({len(reply_text)} chars):")
        print(reply_text)
        print("="*70 + "\n")

        # Extract product data from tool results if any
        products_mentioned = []
        for msg in messages:
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                # Check for tool results
                for content_block in msg.get("content", []):
                    if content_block.get("type") == "tool_result":
                        try:
                            result_data = json.loads(content_block.get("content", "{}"))
                            # Check if result contains product data
                            if result_data.get("success") and "products" in result_data:
                                products_mentioned.extend(result_data["products"])
                            elif result_data.get("success") and "product" in result_data:
                                products_mentioned.append(result_data["product"])
                        except:
                            pass

        # Return response with optional product data
        response = {"reply": reply_text}
        if products_mentioned:
            # Deduplicate products by ID
            seen_ids = set()
            unique_products = []
            for product in products_mentioned:
                product_id = product.get("id")
                if product_id not in seen_ids:
                    seen_ids.add(product_id)
                    unique_products.append(product)
            response["products"] = unique_products
            print(f"📦 Including {len(unique_products)} products in response\n")

        return response
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))
