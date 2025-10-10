# Frontend Integration Guide - E-commerce Chatbot

## API Overview

Your backend API is running at: `http://127.0.0.1:8000` (local) or your deployed Vercel URL (production)

## Available Endpoints

### 1. Chat with AI (Streaming)
**Endpoint:** `POST /api/chat/anthropic/stream`

**Purpose:** Send messages to Claude AI and receive streaming responses with metadata detection

**Request Format:** `multipart/form-data`

**Parameters:**
- `message` (required): User's message text
- `conversation_history` (optional): JSON string of previous messages
- `system_prompt` (optional): System instructions for AI behavior
- `image` (optional): Image file upload
- `image_media_type` (optional): Image MIME type (default: "image/jpeg")
- `model` (optional): Claude model (default: "claude-3-5-haiku-latest")
- `max_tokens` (optional): Max response tokens (default: 1024)
- `stream` (optional): Enable streaming (default: true)

**Response:** Server-Sent Events (SSE) stream with event types:
- `type: "metadata"` - JSON structure (stage, summary, etc.)
- `type: "content"` - Actual message content to display
- `type: "finish"` - End of response
- `type: "done"` - Stream complete

**Example Request:**
```javascript
const formData = new FormData();
formData.append('message', 'I want to buy a car');
formData.append('system_prompt', JSON.stringify({
  instructions: "Return JSON with: stage (0-3), message (user-facing), summary (keywords)"
}));
formData.append('conversation_history', JSON.stringify([
  { role: "user", content: "Hello" },
  { role: "assistant", content: "Hi! How can I help?" }
]));

const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
  method: 'POST',
  body: formData
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));

      if (data.type === 'content') {
        // Display this in chat UI
        appendToMessage(data.delta);
      } else if (data.type === 'metadata') {
        // Parse for stage/summary (don't show to user)
        parseMetadata(data.delta);
      }
    }
  }
}
```

---

### 2. Search Products by Name
**Endpoint:** `GET /api/products/search?q={query}`

**Purpose:** Search for products by name, description, brand, tags, or color

**Parameters:**
- `q` (required): Search query (min 2 characters)
- `category` (optional): Limit search to specific category

**Response:**
```json
{
  "products": [
    {
      "id": 1,
      "name": "2028 Toyota Camry",
      "category": "car",
      "brand": "Toyota",
      "price": 28000.0,
      "color": "Silver",
      "description": "Reliable sedan with great fuel economy",
      "image_url": "https://...",
      "tags": "sedan,reliable,fuel-efficient",
      "publish_time": "2025-01-24",
      "selling_quantity": "1924"
    }
  ],
  "count": 1,
  "query": "toyota",
  "category": null
}
```

**Example Request:**
```javascript
const searchProducts = async (query) => {
  const response = await fetch(
    `http://127.0.0.1:8000/api/products/search?q=${encodeURIComponent(query)}`
  );
  const data = await response.json();
  return data.products;
};

// Usage
const results = await searchProducts('toyota');
console.log(`Found ${results.length} products`);
```

---

### 3. Get Product by ID
**Endpoint:** `GET /api/products/{id}`

**Purpose:** Get detailed information about a specific product

**Parameters:**
- `id` (path parameter): Product ID

**Response:**
```json
{
  "id": 1,
  "name": "2028 Toyota Camry",
  "category": "car",
  "brand": "Toyota",
  "price": 28000.0,
  "color": "Silver",
  "description": "Reliable sedan with great fuel economy",
  "image_url": "https://...",
  "tags": "sedan,reliable,fuel-efficient",
  "publish_time": "2025-01-24",
  "selling_quantity": "1924"
}
```

**Example Request:**
```javascript
const getProductById = async (productId) => {
  const response = await fetch(
    `http://127.0.0.1:8000/api/products/${productId}`
  );

  if (!response.ok) {
    throw new Error(`Product ${productId} not found`);
  }

  return await response.json();
};

// Usage
const product = await getProductById(1);
console.log(product.name);
```

---

## Integration Workflow

### Step 1: User Sends Message
```javascript
// User types: "I want to buy a toyota"

const formData = new FormData();
formData.append('message', userInput);
formData.append('conversation_history', JSON.stringify(chatHistory));

// Send to AI
const aiResponse = await streamChatResponse(formData);
```

### Step 2: AI Parses Intent and Searches
```javascript
// AI responds with structured JSON in metadata
// Example metadata: {"stage": 1, "message": "...", "summary": "category:car,brand:toyota"}

// Frontend extracts search keywords from summary
const keywords = parseSearchKeywords(metadata.summary);

// Search for products
const products = await searchProducts(keywords.brand || keywords.name);
```

### Step 3: Display Products to User
```javascript
// Show AI message
displayMessage(aiResponse.content);

// Show product cards
products.forEach(product => {
  displayProductCard(product);
});
```

### Step 4: User Selects Product
```javascript
// User clicks on a product card
const selectedProduct = await getProductById(productId);

// Show detailed view
displayProductDetails(selectedProduct);
```

---

## Complete Example Implementation

```javascript
// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';

// Chat with AI
async function sendMessage(userMessage, conversationHistory = []) {
  const formData = new FormData();
  formData.append('message', userMessage);

  if (conversationHistory.length > 0) {
    formData.append('conversation_history', JSON.stringify(conversationHistory));
  }

  // Optional: Add system prompt for structured output
  formData.append('system_prompt',
    'You are a shopping assistant. Extract product search keywords and return JSON: ' +
    '{"stage": 0-3, "message": "user-facing response", "summary": "keywords"}'
  );

  const response = await fetch(`${API_BASE_URL}/api/chat/anthropic/stream`, {
    method: 'POST',
    body: formData
  });

  return response;
}

// Parse streaming response
async function parseStreamingResponse(response, onContent, onMetadata) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));

          if (data.type === 'content') {
            onContent(data.delta);
          } else if (data.type === 'metadata') {
            onMetadata(data.delta);
          } else if (data.type === 'done') {
            return;
          }
        } catch (e) {
          console.error('Parse error:', e);
        }
      }
    }
  }
}

// Search products
async function searchProducts(query) {
  if (!query || query.length < 2) return [];

  const response = await fetch(
    `${API_BASE_URL}/api/products/search?q=${encodeURIComponent(query)}`
  );

  if (!response.ok) {
    throw new Error('Search failed');
  }

  const data = await response.json();
  return data.products;
}

// Get product by ID
async function getProductById(id) {
  const response = await fetch(`${API_BASE_URL}/api/products/${id}`);

  if (!response.ok) {
    throw new Error(`Product ${id} not found`);
  }

  return await response.json();
}

// Usage Example
async function handleUserMessage(message) {
  let aiMessage = '';
  let metadata = '';

  const response = await sendMessage(message);

  await parseStreamingResponse(
    response,
    (content) => {
      aiMessage += content;
      updateChatUI(aiMessage);
    },
    (meta) => {
      metadata += meta;
    }
  );

  // Parse metadata to extract search keywords
  try {
    const metadataObj = JSON.parse(metadata);
    const summary = metadataObj.summary || '';

    // Extract search term from summary
    const searchMatch = summary.match(/brand:(\w+)|name:(\w+)/i);
    if (searchMatch) {
      const searchTerm = searchMatch[1] || searchMatch[2];
      const products = await searchProducts(searchTerm);
      displayProducts(products);
    }
  } catch (e) {
    console.log('No structured metadata');
  }
}
```

---

## Error Handling

```javascript
// Handle API errors
async function safeApiCall(apiFunction, ...args) {
  try {
    return await apiFunction(...args);
  } catch (error) {
    if (error.response?.status === 404) {
      console.error('Resource not found');
    } else if (error.response?.status === 400) {
      console.error('Invalid request');
    } else if (error.response?.status === 500) {
      console.error('Server error');
    }
    throw error;
  }
}

// Usage
const products = await safeApiCall(searchProducts, 'toyota');
```

---

## Environment Variables

Create a `.env.local` file in your frontend project:

```bash
# Development
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# Production
# NEXT_PUBLIC_API_URL=https://your-vercel-app.vercel.app
```

Then use:
```javascript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
```

---

## Quick Start Checklist

- [ ] Set up API base URL in your frontend config
- [ ] Implement streaming chat response parser
- [ ] Create search products function
- [ ] Create get product by ID function
- [ ] Handle metadata vs content event types
- [ ] Display products in cards/list
- [ ] Add error handling
- [ ] Test with real user messages

---

## Testing Endpoints

### Test Chat
```bash
curl -X POST "http://127.0.0.1:8000/api/chat/anthropic/stream" \
  -F "message=I want to buy a toyota" \
  -F "stream=false"
```

### Test Search
```bash
curl "http://127.0.0.1:8000/api/products/search?q=toyota"
```

### Test Get by ID
```bash
curl "http://127.0.0.1:8000/api/products/1"
```

---

## Summary

Your frontend needs to:
1. **Send user messages** to `/api/chat/anthropic/stream` with SSE streaming
2. **Parse streaming responses** separating `metadata` from `content`
3. **Search products** using `/api/products/search?q={query}` when AI extracts keywords
4. **Display product details** using `/api/products/{id}` when user clicks a product

**Key Feature:** The API automatically separates metadata (JSON structure) from message content during streaming, so your frontend can parse search keywords without showing them to the user.
