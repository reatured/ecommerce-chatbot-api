import os
import json
import re
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

# Default system prompt for the shopping assistant
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI shopping assistant for an e-commerce store.

PRODUCT CATALOG:
- We sell backpacks (hiking, school, travel, laptop bags, sports)
- We sell cars (sedans, SUVs, electric vehicles, luxury, economy)

YOUR CAPABILITIES:
1. General conversation - Answer questions about yourself and help users
2. Product recommendations - Help users find products based on text descriptions
3. Image-based search - When users upload images, analyze them and recommend matching products
4. **TOOLS**: You have access to tools to search products and get product details

TOOL USAGE GUIDELINES:
- Use the `search_products` tool when users ask about products (e.g., "show me backpacks", "find blue cars")
- Use the `get_product_details` tool when users ask about a specific product by ID
- **IMPORTANT**: For text-based product queries, ALWAYS use the search_products tool to get actual results
- Only recommend products that you found via the tools - do NOT make up product names or prices
- After using tools, reference the actual products found (name, brand, price)

RESPONSE GUIDELINES:
- Be friendly, conversational, and helpful
- For product questions, use tools to search, then provide specific recommendations from results
- When products are shown in the side panel, reference them by name
- Ask clarifying questions to understand user needs better
- **IMPORTANT**: When suggesting quick actions, provide maximum 4 options
- **ALWAYS provide a response** - never leave your message empty

HANDLING "NO RESULTS FOUND":
When search_products or image analysis returns 0 results:
1. Acknowledge what the user was looking for
2. Politely explain we don't have that product in our catalog
3. Suggest alternatives from our available categories (backpacks or cars)
4. Offer to help with something else

Example for no results:
"I searched for [product] but unfortunately we don't have that in our catalog right now. However, I can help you find great backpacks or cars! What are you interested in?"

EXAMPLES:
User: "What's your name?"
You: "I'm your AI shopping assistant! I can help you find backpacks and cars from our catalog."

User: "I need a backpack for hiking"
You: [Use search_products tool with query="hiking backpack"]
You: "I found several great hiking backpacks! The [actual product name from search] by [brand] is $[price] and has [features]. Would you like to see more options?"

User: "Do you have books?"
You: [Use search_products tool with query="books"]
You: "I searched our catalog but we don't currently sell books. However, we have a great selection of backpacks and cars! Can I help you find something from those categories?"

User: [uploads image]
You: "I can see this is a [description]. I found several similar products in our catalog - the [product name] at $[price] is very similar!"
"""

# Tool definitions for Anthropic API
TOOLS = [
    {
        "name": "search_products",
        "description": "Search for products in the catalog by keyword. Searches across product names, descriptions, brands, tags, and colors. Optionally filter by category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'blue hiking backpack', 'electric car', 'waterproof')"
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter (e.g., 'car', 'backpack', 'home_appliance')",
                    "enum": ["car", "backpack", "home_appliance"]
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_product_details",
        "description": "Get detailed information about a specific product by its ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "The ID of the product to retrieve"
                }
            },
            "required": ["product_id"]
        }
    }
]


# Health check endpoint
@app.api_route("/", methods=["GET", "HEAD"])
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


# Image-based product search helper
async def analyze_image_and_find_products(image_base64: str, message: str = "") -> dict:
    """
    Analyze uploaded image with Claude Vision and find matching products

    Args:
        image_base64: Base64 encoded image data
        message: Optional user message accompanying the image

    Returns:
        Dictionary with products, analysis, category, and features
    """
    from anthropic import Anthropic
    from api.products import fetch_products_from_sheet

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Step 1: Analyze image with Vision API
    try:
        vision_response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": """Analyze this product image and respond in this EXACT format:

CATEGORY: [car OR backpack - choose one]
COLOR: [primary color seen in image]
STYLE: [brief style description]
FEATURES: [key visible features, comma-separated]
SEARCH_QUERY: [best keywords to search for similar products]

Example response:
CATEGORY: backpack
COLOR: blue
STYLE: hiking
FEATURES: large capacity, multiple compartments, padded straps
SEARCH_QUERY: blue hiking backpack large

If this is not a product image (car or backpack), respond with:
CATEGORY: none
COLOR: none
STYLE: not a product
FEATURES: none
SEARCH_QUERY: none"""
                    }
                ]
            }]
        )

        analysis_text = vision_response.content[0].text
        print(f"📸 Vision Analysis: {analysis_text}")

    except Exception as e:
        print(f"❌ Vision API error: {e}")
        return {
            "products": [],
            "analysis": f"Error analyzing image: {str(e)}",
            "category": None,
            "features": []
        }

    # Step 2: Parse the analysis
    category = None
    color = None
    style = None
    features = []
    search_query = ""

    for line in analysis_text.strip().split('\n'):
        line = line.strip()
        if line.startswith('CATEGORY:'):
            category = line.split(':', 1)[1].strip().lower()
        elif line.startswith('COLOR:'):
            color = line.split(':', 1)[1].strip().lower()
        elif line.startswith('STYLE:'):
            style = line.split(':', 1)[1].strip()
        elif line.startswith('FEATURES:'):
            features_str = line.split(':', 1)[1].strip()
            features = [f.strip() for f in features_str.split(',')]
        elif line.startswith('SEARCH_QUERY:'):
            search_query = line.split(':', 1)[1].strip()

    # Step 3: Check if it's a valid product
    if category == 'none' or category not in ['car', 'backpack']:
        return {
            "products": [],
            "analysis": analysis_text,
            "category": None,
            "features": features,
            "message": "I can see this image, but it doesn't appear to be a car or backpack product. Please upload an image of a car or backpack to search for similar products."
        }

    # Step 4: Search products
    try:
        all_products = fetch_products_from_sheet()

        # Filter by category
        products = [p for p in all_products if p.get('category', '').lower() == category]

        # Filter by color if detected (and color is valid)
        if color and color != 'none':
            color_filtered = [p for p in products if color in p.get('color', '').lower()]
            if color_filtered:
                products = color_filtered

        # Rank products by keyword matching
        if search_query and search_query != 'none':
            scored_products = []
            search_terms = search_query.lower().split()

            for product in products:
                # Build searchable text
                searchable = ' '.join([
                    product.get('name', ''),
                    product.get('description', ''),
                    product.get('brand', ''),
                    product.get('tags', ''),
                    product.get('color', '')
                ]).lower()

                # Score based on term matches
                score = sum(1 for term in search_terms if term in searchable)

                if score > 0:
                    scored_products.append((product, score))

            # Sort by score descending
            scored_products.sort(key=lambda x: x[1], reverse=True)
            products = [p[0] for p in scored_products]

        # Limit to top 10
        products = products[:10]

        return {
            "products": products,
            "analysis": analysis_text,
            "category": category,
            "color": color,
            "style": style,
            "features": features,
            "search_query": search_query,
            "count": len(products)
        }

    except Exception as e:
        print(f"❌ Product search error: {e}")
        return {
            "products": [],
            "analysis": analysis_text,
            "category": category,
            "features": features,
            "error": f"Error searching products: {str(e)}"
        }


# Tool execution handler
def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Execute a tool call from the AI and return results

    Args:
        tool_name: Name of the tool to execute
        tool_input: Input parameters for the tool

    Returns:
        Dictionary with tool results
    """
    from api.products import fetch_products_from_sheet

    try:
        if tool_name == "search_products":
            # Get search parameters
            query = tool_input.get("query", "")
            category = tool_input.get("category")

            if not query or len(query.strip()) < 2:
                return {
                    "error": "Search query must be at least 2 characters",
                    "products": []
                }

            # Fetch all products
            products = fetch_products_from_sheet()

            # Filter by category if provided
            if category:
                products = [p for p in products if p.get('category', '').lower() == category.lower()]

            # Search across multiple fields
            q_lower = query.lower()
            results = []

            for product in products:
                # Build searchable text
                searchable_text = ' '.join([
                    product.get('name', ''),
                    product.get('description', ''),
                    product.get('brand', ''),
                    product.get('tags', ''),
                    product.get('color', '')
                ]).lower()

                if q_lower in searchable_text:
                    results.append(product)

            # Limit to top 10 results
            results = results[:10]

            print(f"🔧 Tool search_products: query='{query}', category={category}, found {len(results)} products")

            # Format results for AI
            if len(results) == 0:
                return {
                    "products": [],
                    "count": 0,
                    "message": f"No products found for '{query}'" + (f" in category '{category}'" if category else "")
                }

            # Return formatted product list
            return {
                "products": [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "brand": p.get("brand"),
                        "price": p.get("price"),
                        "color": p.get("color"),
                        "category": p.get("category"),
                        "description": p.get("description", "")[:200]  # Truncate long descriptions
                    }
                    for p in results
                ],
                "count": len(results),
                "query": query,
                "category": category
            }

        elif tool_name == "get_product_details":
            # Get product ID
            product_id = tool_input.get("product_id")

            if not product_id:
                return {"error": "Product ID is required"}

            # Fetch all products
            products = fetch_products_from_sheet()

            # Find product by ID
            product = next((p for p in products if p.get('id') == product_id), None)

            if not product:
                return {"error": f"Product with ID {product_id} not found"}

            print(f"🔧 Tool get_product_details: product_id={product_id}, found '{product.get('name')}'")

            # Return full product details
            return {
                "product": {
                    "id": product.get("id"),
                    "name": product.get("name"),
                    "brand": product.get("brand"),
                    "price": product.get("price"),
                    "color": product.get("color"),
                    "category": product.get("category"),
                    "description": product.get("description"),
                    "tags": product.get("tags"),
                    "image_url": product.get("image_url"),
                    "publish_time": product.get("publish_time"),
                    "selling_quantity": product.get("selling_quantity")
                }
            }

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        print(f"❌ Tool execution error for {tool_name}: {e}")
        return {"error": f"Error executing tool: {str(e)}"}


def validate_and_fix_json_response(response_text: str) -> tuple[dict | None, str]:
    """
    Validate and attempt to fix JSON responses from Claude.

    Args:
        response_text: The raw response text from Claude

    Returns:
        Tuple of (parsed_json_dict_or_None, cleaned_text)
        - If valid JSON found: (dict, original_text)
        - If invalid but fixable: (dict, fixed_text)
        - If unfixable: (None, original_text)
    """
    # Try direct parse first
    try:
        parsed = json.loads(response_text.strip())
        if isinstance(parsed, dict) and "message" in parsed:
            return (parsed, response_text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON object from mixed text
    # Pattern: Look for {...} containing "message" field
    json_pattern = r'\{[^{}]*?"message"[^{}]*?\}'
    matches = re.finditer(json_pattern, response_text, re.DOTALL)

    for match in matches:
        json_str = match.group(0)
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "message" in parsed:
                print(f"✅ Extracted valid JSON from position {match.start()}-{match.end()}")
                return (parsed, json_str)
        except json.JSONDecodeError:
            continue

    # Try fixing common JSON issues
    fixed_text = response_text.strip()

    # Fix: Remove markdown code blocks if present
    if fixed_text.startswith("```json"):
        fixed_text = re.sub(r'^```json\s*', '', fixed_text)
        fixed_text = re.sub(r'\s*```$', '', fixed_text)
        try:
            parsed = json.loads(fixed_text)
            if isinstance(parsed, dict):
                print("✅ Fixed JSON by removing markdown code blocks")
                return (parsed, fixed_text)
        except json.JSONDecodeError:
            pass

    # Fix: Remove trailing commas
    fixed_text = re.sub(r',\s*([}\]])', r'\1', response_text)
    try:
        parsed = json.loads(fixed_text)
        if isinstance(parsed, dict):
            print("✅ Fixed JSON by removing trailing commas")
            return (parsed, fixed_text)
    except json.JSONDecodeError:
        pass

    # If all fixes fail, return None
    print(f"⚠️ Could not extract or fix JSON from response (length: {len(response_text)} chars)")
    return (None, response_text)


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
    Internal helper to process Anthropic chat requests with tool calling support
    Returns either JSONResponse or StreamingResponse

    Args:
        messages: List of message dicts with 'role' and 'content' keys
    """
    from fastapi.responses import JSONResponse

    # Tool use loop: AI may request tools, we execute them, then AI generates final response
    max_tool_iterations = 3  # Prevent infinite loops
    iteration = 0

    while iteration < max_tool_iterations:
        iteration += 1

        # Prepare request parameters
        request_params = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
            "tools": TOOLS  # Add tool definitions
        }

        # Add system message if provided
        if system:
            request_params["system"] = system

        # Non-streaming mode with tools
        if not stream:
            response = client.messages.create(**request_params)

            # Check if AI wants to use tools
            if response.stop_reason == "tool_use":
                print(f"🔧 AI requested tool use (iteration {iteration})")

                # Extract tool use blocks
                tool_results = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input
                        tool_use_id = content_block.id

                        print(f"🔧 Executing tool: {tool_name} with input: {tool_input}")

                        # Execute the tool
                        tool_result = execute_tool(tool_name, tool_input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(tool_result)
                        })

                # Add assistant message with tool use to history
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Add tool results as user message
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # Continue loop to get AI's final response
                continue

            # No tool use - return final response
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

        # Streaming mode with tools
        # For streaming, we need to handle tool use BEFORE starting the stream
        # First, make a non-streaming call to check for tool use
        check_response = client.messages.create(**request_params)

        # Check if AI wants to use tools
        if check_response.stop_reason == "tool_use":
            print(f"🔧 AI requested tool use in streaming mode (iteration {iteration})")

            # Extract tool use blocks
            tool_results = []
            for content_block in check_response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_use_id = content_block.id

                    print(f"🔧 Executing tool: {tool_name} with input: {tool_input}")

                    # Execute the tool
                    tool_result = execute_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(tool_result)
                    })

            # Add assistant message with tool use to history
            messages.append({
                "role": "assistant",
                "content": check_response.content
            })

            # Add tool results as user message
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Continue loop to get AI's final response (will stream next iteration)
            continue

        # No tool use needed - break out and stream the response
        break

    # Now stream the final response (either no tools needed, or tools already executed)
    async def generate():
        try:
            message_content_started = False
            message_content_ended = False
            buffer = ""
            emitted_buffer = ""  # Track what we've already emitted
            message_start_pos = -1
            message_end_pos = -1
            has_emitted_any_content = False  # NEW: Track if we've sent any content chunks

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
                                    has_emitted_any_content = True  # NEW: Mark that we sent content

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
                                has_emitted_any_content = True  # NEW: Mark that we sent content

                    # After message ended, everything is metadata
                    elif message_content_ended:
                        metadata_to_emit = buffer[len(emitted_buffer):]
                        if metadata_to_emit:
                            yield f"data: {json.dumps({'type': 'metadata', 'delta': metadata_to_emit, 'index': 0})}\n\n"
                            emitted_buffer = buffer

                # Get the final response message
                final_message = stream.get_final_message()

                # NEW: HYBRID FALLBACK - If no content was emitted, treat entire buffer as plain text
                if not has_emitted_any_content and buffer:
                    print(f"⚠️ FALLBACK: No JSON structure detected, streaming entire response as plain text ({len(buffer)} chars)")
                    # Send entire buffer as content
                    yield f"data: {json.dumps({'type': 'content', 'delta': buffer, 'index': 0})}\n\n"
                    has_emitted_any_content = True

                # NEW: Additional safety check - extract from final_message if still no content
                if not has_emitted_any_content:
                    print(f"⚠️ FALLBACK 2: Extracting text from final_message")
                    if hasattr(final_message, 'content') and final_message.content:
                        # Extract text from content blocks
                        text_content = ""
                        for block in final_message.content:
                            if hasattr(block, 'text'):
                                text_content += block.text

                        if text_content:
                            print(f"✅ Extracted {len(text_content)} chars from final_message")
                            yield f"data: {json.dumps({'type': 'content', 'delta': text_content, 'index': 0})}\n\n"
                            has_emitted_any_content = True

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
        image_search_results = None

        if image:
            # File upload
            image_data = await image.read()
            img_base64 = base64.b64encode(image_data).decode('utf-8')
            image_media_type = image.content_type or image_media_type

            # IMPORTANT: Perform image-based product search
            print("🔍 Performing image-based product search...")
            image_search_results = await analyze_image_and_find_products(img_base64, message)
            print(f"✅ Found {image_search_results.get('count', 0)} products matching image")

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

        # Use system_prompt if provided, otherwise use default
        final_system_prompt = system_prompt or system or DEFAULT_SYSTEM_PROMPT

        # If image search found products, add context to system prompt
        if image_search_results and image_search_results.get('products'):
            products = image_search_results['products']
            category = image_search_results.get('category', 'products')
            color = image_search_results.get('color', '')

            product_context = f"""

IMAGE ANALYSIS RESULTS:
The user uploaded an image of a {color + ' ' if color else ''}{category}.
I found {len(products)} matching products in our catalog:

"""
            for i, p in enumerate(products[:5], 1):
                product_context += f"{i}. {p['name']} by {p['brand']} - ${p['price']}"
                if p.get('color'):
                    product_context += f" ({p['color']})"
                product_context += "\n"

            if len(products) > 5:
                product_context += f"\n...and {len(products) - 5} more similar products.\n"

            product_context += """
IMPORTANT: The user can see these products in the side panel. Reference them by name in your response.
Recommend specific products from this list and mention their prices.
"""

            final_system_prompt = (final_system_prompt or "") + product_context

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
