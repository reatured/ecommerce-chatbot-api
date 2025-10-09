# E-commerce Chatbot API

FastAPI backend providing AI-powered chat and search capabilities via streaming endpoints.

## Available APIs

### 1. Anthropic Chat Stream
**Endpoint:** `POST /api/chat/anthropic/stream`

Streams AI chat responses from Claude (Anthropic).

**Request:**
```json
{
  "message": "Hello, recommend some products",
  "image": "base64_encoded_image_data",  // optional
  "image_media_type": "image/jpeg",       // optional, default: "image/jpeg"
  "model": "claude-3-5-sonnet-20241022",  // optional
  "max_tokens": 1024                      // optional
}
```

**Response:** Server-Sent Events (SSE) stream
```
data: {"type": "content", "text": "Hello! I'd be happy to..."}
data: {"type": "content", "text": " recommend some products..."}
data: {"type": "done"}
```

**Example:**
```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Recommend gift ideas for coffee lovers"}'
```

---

### 2. Perplexity Search Stream
**Endpoint:** `POST /api/chat/perplexity/stream`

Streams web search results from Perplexity AI.

**Request:**
```json
{
  "query": "best wireless headphones 2025"
}
```

**Response:** Server-Sent Events (SSE) stream
```
data: {"type": "search_id", "id": "..."}
data: {"type": "result", "index": 0, "title": "...", "url": "...", "snippet": "..."}
data: {"type": "result", "index": 1, "title": "...", "url": "...", "snippet": "..."}
data: {"type": "done", "total_results": 5}
```

**Example:**
```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/perplexity/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "best wireless headphones 2025"}'
```

---

### 3. Health Check
**Endpoint:** `GET /`

Returns API status and available endpoints.

**Response:**
```json
{
  "status": "ok",
  "message": "E-commerce Chatbot API is running",
  "endpoints": {
    "perplexity_search": "/api/chat/perplexity/stream",
    "anthropic_chat": "/api/chat/anthropic/stream"
  }
}
```

---

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run server
uvicorn api.index:app --reload --port 8000
```

**Required environment variables:**
- `ANTHROPIC_API_KEY`
- `PERPLEXITY_API_KEY`