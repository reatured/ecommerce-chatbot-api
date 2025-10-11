# E-commerce Chatbot API

FastAPI backend for the AI-powered shopping assistant. Provides streaming chat responses, product search, and image analysis capabilities powered by Anthropic Claude.

**Live API**: [https://ecommerce-chatbot-api-09va.onrender.com](https://ecommerce-chatbot-api-09va.onrender.com)
**API Docs**: [https://ecommerce-chatbot-api-09va.onrender.com/docs](https://ecommerce-chatbot-api-09va.onrender.com/docs)

---

## Features

### Core Capabilities
- **Streaming Chat Responses**: Real-time AI responses via Server-Sent Events (SSE)
- **Tool Calling**: Claude intelligently uses tools to search products
- **Image Analysis**: Claude Vision analyzes product images and finds similar items
- **Product Catalog**: RESTful API for product browsing and search
- **Conversation History**: Stateless API with client-side history management

### Technical Features
- Async/await for high concurrency
- CORS enabled for cross-origin requests
- Automatic API documentation (Swagger UI)
- Environment-based configuration
- Error handling with structured responses

---

## Technology Stack

| Technology | Purpose |
|-----------|---------|
| **FastAPI** | Modern, high-performance Python web framework |
| **Anthropic Claude 3.5 Sonnet** | LLM with vision and tool-calling capabilities |
| **Uvicorn** | Lightning-fast ASGI server |
| **Pydantic** | Data validation and settings management |
| **Google Sheets API** | Simple product catalog (easily replaceable) |
| **python-multipart** | Multipart form data handling for file uploads |

---

## Quick Start

### Prerequisites

- **Python** 3.9+ ([Download](https://www.python.org/downloads/))
- **Anthropic API Key** ([Get one here](https://console.anthropic.com))

```bash
# Check Python version
python --version  # Should be 3.9 or higher
```

### Installation

```bash
# Navigate to backend directory
cd ecommerce-chatbot-api

# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Running the Server

```bash
# Development mode (auto-reload on file changes)
uvicorn api.index:app --reload --port 8000

# Production mode
uvicorn api.index:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Main API**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## API Documentation

### Health Check

**GET** `/`

Returns API status and available endpoints.

```bash
curl http://localhost:8000/
```

**Response**:
```json
{
  "status": "ok",
  "message": "E-commerce Chatbot API is running",
  "endpoints": {
    "chat": "/api/chat/anthropic/stream",
    "products_list": "/api/products",
    "products_search": "/api/products/search?q={query}",
    "product_by_id": "/api/products/{id}"
  }
}
```

---

### Chat Endpoint (Main)

**POST** `/api/chat/anthropic/stream`

Unified streaming chat endpoint that handles all three use cases:
1. General conversation
2. Text-based product search (via tool calling)
3. Image-based product search (via vision + tool calling)

**Request** (multipart/form-data):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | text | ✅ | User's message |
| `conversation_history` | text (JSON) | ❌ | Array of previous messages for context |
| `image` | file | ❌ | Product image for visual search |
| `image_media_type` | text | ❌ | Image MIME type (default: image/jpeg) |
| `stream` | boolean | ❌ | Enable streaming (default: true) |
| `model` | text | ❌ | Claude model (default: claude-3-5-sonnet-20241022) |
| `max_tokens` | integer | ❌ | Max response length (default: 4096) |

**Conversation History Format**:
```json
[
  {"role": "user", "content": "What backpacks do you have?"},
  {"role": "assistant", "content": "We have 15 backpacks ranging from $29 to $199..."}
]
```

**Response** (Server-Sent Events):

```
data: {"type": "content", "delta": "I found "}
data: {"type": "content", "delta": "several great "}
data: {"type": "content", "delta": "backpacks! "}
data: {"type": "tool_use", "name": "search_products", "input": {"query": "backpack"}}
data: {"type": "tool_result", "tool_use_id": "...", "content": "{\"products\": [...]}"}
data: {"type": "content", "delta": "The Explorer Pro..."}
data: {"type": "finish", "finish_reason": "stop"}
data: {"type": "done"}
```

**Event Types**:

| Type | Description |
|------|-------------|
| `content` | Text chunk from AI response |
| `tool_use` | AI is calling a tool (e.g., search_products) |
| `tool_result` | Result from tool execution |
| `finish` | Response complete (`finish_reason`: "stop", "length", or "error") |
| `done` | Stream end marker |
| `error` | Error occurred |

**Example: Text-Only Chat**

```bash
curl -N -X POST http://localhost:8000/api/chat/anthropic/stream \
  -F "message=What's your name?" \
  -F "stream=true"
```

**Example: Product Search**

```bash
curl -N -X POST http://localhost:8000/api/chat/anthropic/stream \
  -F "message=Show me hiking backpacks" \
  -F "stream=true"
```

**Example: Image Search**

```bash
curl -N -X POST http://localhost:8000/api/chat/anthropic/stream \
  -F "message=Find similar products" \
  -F "image=@/path/to/backpack.jpg" \
  -F "stream=true"
```

**Example: With Conversation History**

```bash
curl -N -X POST http://localhost:8000/api/chat/anthropic/stream \
  -F "message=Which one is best for hiking?" \
  -F 'conversation_history=[{"role":"user","content":"Show me backpacks"},{"role":"assistant","content":"I found 15 backpacks..."}]' \
  -F "stream=false"
```

---

### Product Endpoints

#### List All Products

**GET** `/api/products`

Get all products with optional filtering.

**Query Parameters**:
- `category` (optional): Filter by category (e.g., "backpacks", "cars")
- `color` (optional): Filter by color (e.g., "blue", "red")

```bash
# Get all products
curl http://localhost:8000/api/products

# Get backpacks only
curl http://localhost:8000/api/products?category=backpacks

# Get blue backpacks
curl http://localhost:8000/api/products?category=backpacks&color=blue
```

#### Search Products

**GET** `/api/products/search`

Search products by keyword.

**Query Parameters**:
- `q` (required): Search query
- `category` (optional): Filter by category

```bash
# Search for "hiking"
curl http://localhost:8000/api/products/search?q=hiking

# Search for "waterproof" in backpacks category
curl http://localhost:8000/api/products/search?q=waterproof&category=backpacks
```

#### Get Product by ID

**GET** `/api/products/{id}`

Get detailed information for a specific product.

```bash
curl http://localhost:8000/api/products/1
```

**Response**:
```json
{
  "id": "1",
  "name": "Explorer Pro Backpack",
  "brand": "Outdoor Essentials",
  "price": 79.99,
  "color": "Blue",
  "category": "backpacks",
  "description": "Waterproof hiking backpack with 30L capacity",
  "tags": "hiking, waterproof, durable",
  "image_url": "https://...",
  "publish_time": "2024-01-15",
  "selling_quantity": 245
}
```

---

## How It Works

### Agent Architecture

The API uses Claude's **tool calling** capability to create a unified agent that handles all three use cases:

```python
# System prompt defines capabilities
SYSTEM_PROMPT = """
You are a helpful e-commerce shopping assistant.

Your capabilities:
1. General conversation - Answer questions about yourself
2. Product recommendations - Help users find products using tools
3. Image-based search - Analyze product images

TOOLS available:
- search_products(query, category?) - Search product catalog
- get_product_details(product_id) - Get specific product info
"""

# Tools configuration
tools = [
    {
        "name": "search_products",
        "description": "Search for products by keyword...",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "category": {"type": "string", "description": "Optional category filter"}
            },
            "required": ["query"]
        }
    }
]
```

### Request Flow

1. **User sends message** (with optional image)
2. **Image preprocessing** (if image included):
   - Claude Vision analyzes image
   - Extracts: category, color, style, features
   - Searches catalog for matching products
   - Injects top results into context
3. **Agent processing**:
   - Determines if tool call needed
   - Executes `search_products` or `get_product_details` if needed
   - Generates natural language response with actual product data
4. **Streaming response** via SSE
5. **Frontend receives** chunks in real-time

### Tool Execution Example

```
User: "I need a hiking backpack"

Agent: [Calls search_products(query="hiking backpack", category="backpacks")]
       ↓
       [Tool returns 5 products]
       ↓
       [Agent references actual products in response]

Response: "I found several great hiking backpacks! The Explorer Pro
Backpack by Outdoor Essentials ($79.99) features waterproof material
and 30L capacity. The Mountain Trail Pack by Adventure Co ($129.99)
has extra padding and multiple compartments..."
```

---

## Environment Configuration

Create a `.env` file in the root directory:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional
PORT=8000
DEBUG=false
```

**Getting an Anthropic API Key**:
1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Navigate to API Keys section
3. Create a new key
4. Add to `.env` file

---

## Product Catalog

The current implementation uses **Google Sheets** as a lightweight, editable database.

**Sheet Structure**:
| Column | Type | Description |
|--------|------|-------------|
| id | string | Unique product ID |
| name | string | Product name |
| brand | string | Brand/manufacturer |
| price | float | Price in USD |
| color | string | Primary color |
| category | string | Product category |
| description | string | Product description |
| tags | string | Comma-separated tags |
| image_url | string | Product image URL |
| publish_time | date | Publication date |
| selling_quantity | integer | Units sold |

**Replacing with a Database**:

To use PostgreSQL, MongoDB, or another database:

1. Install database driver: `pip install psycopg2-binary` (PostgreSQL)
2. Update `api/products.py`:
```python
# Replace fetch_products_from_sheet() with:
def fetch_products_from_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    return cursor.fetchall()
```
3. Update `SHEET_URL` references to use DB connection

---

## Project Structure

```
ecommerce-chatbot-api/
├── api/
│   ├── __init__.py
│   ├── index.py          # Main API routes & agent logic
│   └── products.py       # Product catalog & search logic
│
├── requirements.txt      # Python dependencies
├── .env.example         # Environment template
├── .env                 # Your environment (not in git)
├── render.yaml          # Render.com deployment config
├── vercel.json          # Vercel deployment config
└── README.md            # This file
```

### Key Files

**`api/index.py`** - Main API logic
- Chat streaming endpoint
- Tool calling implementation
- Image analysis and product search
- SSE response formatting

**`api/products.py`** - Product catalog
- Google Sheets integration
- Product search and filtering
- RESTful product endpoints

---

## Deployment

### Render.com (Current)

The API is deployed on **Render.com** with automatic deployments from the main branch.

**Manual Deployment**:
1. Create new Web Service on Render
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn api.index:app --host 0.0.0.0 --port $PORT`
5. Add environment variable: `ANTHROPIC_API_KEY`

### Vercel (Alternative)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

**Note**: Vercel requires the Mangum adapter (already configured in `api/index.py`).

### Docker (For Self-Hosting)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t chatbot-api .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=your_key chatbot-api
```

---

## Development

### Testing Endpoints

**Using curl**:
```bash
# Health check
curl http://localhost:8000/

# Chat (streaming)
curl -N -X POST http://localhost:8000/api/chat/anthropic/stream \
  -F "message=Hello" \
  -F "stream=true"

# Products
curl http://localhost:8000/api/products
```

**Using Swagger UI**:
Visit `http://localhost:8000/docs` for interactive API testing.

### Debugging

Enable debug logs:
```python
# In api/index.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

View logs:
```bash
# Development
uvicorn api.index:app --reload --log-level debug

# Production (Render)
# Check Render dashboard → Logs tab
```

---

## Error Handling

The API returns structured error responses:

**Example Error Response**:
```json
{
  "type": "error",
  "error": "Invalid API key",
  "details": "Please check your ANTHROPIC_API_KEY environment variable"
}
```

**Common Errors**:

| Status | Error | Solution |
|--------|-------|----------|
| 400 | Missing message | Include `message` in request |
| 401 | Invalid API key | Check `ANTHROPIC_API_KEY` in `.env` |
| 413 | File too large | Reduce image size (< 5MB) |
| 500 | Internal error | Check server logs for details |

---

## Performance

### Optimization Tips

1. **Use streaming**: Reduces perceived latency
2. **Limit max_tokens**: Shorter responses = faster + cheaper
3. **Cache products**: Reduce Google Sheets API calls
4. **Use CDN**: Host product images on CDN
5. **Enable compression**: Gzip responses

### Benchmarks

Tested on Render.com free tier:
- **Cold start**: ~15s (first request after inactivity)
- **Warm response**: ~1-2s (time to first byte)
- **Streaming**: ~50-100 tokens/second
- **Image analysis**: +2-3s overhead

---

## Security

### Best Practices

- ✅ API keys stored in environment variables (never in code)
- ✅ CORS configured for specific origins
- ✅ File upload size limits enforced
- ✅ Input validation with Pydantic
- ✅ HTTPS enforced in production

### Production Checklist

- [ ] Rotate API keys regularly
- [ ] Set up rate limiting (e.g., using Cloudflare)
- [ ] Monitor usage in Anthropic dashboard
- [ ] Enable logging for security events
- [ ] Use secrets manager (AWS Secrets Manager, etc.)

---

## Troubleshooting

### Issue: "Missing ANTHROPIC_API_KEY"
**Solution**: Add key to `.env` file or environment variables

### Issue: "ModuleNotFoundError"
**Solution**: Activate venv and run `pip install -r requirements.txt`

### Issue: "Connection refused"
**Solution**: Check if server is running and port is correct

### Issue: "Tool call failed"
**Solution**: Check Google Sheets URL is accessible and correctly formatted

### Issue: "Streaming stops mid-response"
**Solution**: Check Anthropic API key is valid and has credits

---

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# Run with coverage
pytest --cov=api tests/
```

---

## Contributing

This is a portfolio project for interview evaluation. Contributions are not currently accepted.

---

## License

This project is part of a take-home assignment and is not licensed for public use.

---

## Support

For questions about this API, please contact the repository maintainer.
