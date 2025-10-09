# E-commerce Chatbot API

FastAPI backend providing AI-powered chat and search capabilities via streaming endpoints. Compatible with OpenAI-style chat completions format.

## Available APIs

### 1. Anthropic Chat
**Endpoint:** `POST /api/chat/anthropic/stream`

Chat responses from Claude (Anthropic). Supports both streaming and non-streaming modes.
Accepts both JSON (`application/json`) and file uploads (`multipart/form-data`).

**Request:**
```json
{
  "message": "Recommend gift ideas for coffee lovers",
  "image": "base64_encoded_image_data",  // optional
  "image_media_type": "image/jpeg",       // optional, default: "image/jpeg"
  "model": "claude-3-5-sonnet-20241022",  // optional
  "max_tokens": 1024,                     // optional
  "stream": true                          // optional, default: true
}
```

**Streaming Response (`stream: true`):** Server-Sent Events (SSE)
```
data: {"type": "content", "delta": "Hello", "index": 0}
data: {"type": "content", "delta": "! I'd", "index": 0}
data: {"type": "content", "delta": " be happy", "index": 0}
data: {"type": "finish", "finish_reason": "stop"}
data: {"type": "done"}
```

**Non-Streaming Response (`stream: false`):** JSON
```json
{
  "type": "complete",
  "content": "Hello! I'd be happy to recommend some gift ideas for coffee lovers...",
  "finish_reason": "stop",
  "model": "claude-3-5-sonnet-20241022",
  "usage": {
    "input_tokens": 15,
    "output_tokens": 120
  }
}
```

**Response Event Types:**
- `content` - Text chunks from the AI response
  - `delta`: The text content chunk
  - `index`: Choice index (always 0 for single responses)
- `finish` - Indicates completion with reason
  - `finish_reason`: `"stop"`, `"length"`, or `"error"`
- `done` - Stream completion marker
- `error` - Error message if something fails

**Example:**
```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Recommend gift ideas for coffee lovers"}'
```

---

**File Upload Support:**

The same endpoint accepts `multipart/form-data` for file uploads (perfect for testing in `/docs` UI).

**Form Fields:**
- `message` (text, required)
- `image` (file, optional)
- `model` (text, optional)
- `max_tokens` (integer, optional)
- `stream` (boolean, optional, default: true)

**Examples with File Upload:**
```bash
# Streaming mode with file upload
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=What's in this image?" \
  -F "image=@photo.jpg" \
  -F "stream=true"

# Non-streaming mode with file upload
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=What's in this image?" \
  -F "image=@photo.jpg" \
  -F "stream=false"
```

---

### 2. Perplexity Chat
**Endpoint:** `POST /api/chat/perplexity/stream`

Web-grounded chat responses from Perplexity AI using the Sonar model. Supports both streaming and non-streaming modes.

**Request:**
```json
{
  "query": "What are the latest AI developments?",
  "stream": true  // optional, default: true
}
```

**Streaming Response (`stream: true`):** Server-Sent Events (SSE)
```
data: {"type": "content", "delta": "Based on", "index": 0}
data: {"type": "content", "delta": " recent information", "index": 0}
data: {"type": "finish", "finish_reason": "stop"}
data: {"type": "done"}
```

**Non-Streaming Response (`stream: false`):** JSON
```json
{
  "type": "complete",
  "content": "Based on recent information, here are the latest AI developments...",
  "finish_reason": "stop",
  "model": "sonar",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 150,
    "total_tokens": 160
  }
}
```

**Response Event Types:**
- `content` - Text chunks from the AI response
  - `delta`: The text content chunk
  - `index`: Choice index
- `finish` - Completion indicator
  - `finish_reason`: Reason for completion
- `done` - Stream completion marker
- `error` - Error message if something fails

**Examples:**
```bash
# Streaming mode
curl -N -X POST http://127.0.0.1:8000/api/chat/perplexity/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "best wireless headphones 2025", "stream": true}'

# Non-streaming mode
curl -X POST http://127.0.0.1:8000/api/chat/perplexity/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "best wireless headphones 2025", "stream": false}'
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
    "perplexity_chat": "/api/chat/perplexity/stream",
    "anthropic_chat": "/api/chat/anthropic/stream"
  },
  "notes": {
    "anthropic_chat": "Accepts both JSON and multipart/form-data (file uploads)",
    "streaming": "All endpoints support streaming toggle via 'stream' parameter (default: true)"
  }
}
```

---

## Integration Guide for Lovable

### Frontend Implementation (React/TypeScript)

Here's how to integrate these endpoints into your Lovable chatbot application with streaming toggle:

```typescript
// 1. Chat with streaming support
async function streamChatResponse(
  endpoint: string,
  payload: any,
  onChunk: (text: string) => void,
  onComplete: () => void,
  onError: (error: string) => void
) {
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No reader available');
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonData = line.slice(6);
          try {
            const parsed = JSON.parse(jsonData);

            if (parsed.type === 'content') {
              onChunk(parsed.delta);
            } else if (parsed.type === 'finish') {
              console.log('Finish reason:', parsed.finish_reason);
            } else if (parsed.type === 'done') {
              onComplete();
              break;
            } else if (parsed.type === 'error') {
              onError(parsed.message);
              break;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error.message : 'Unknown error');
  }
}

// 2. Non-streaming chat
async function chatResponse(
  endpoint: string,
  payload: any,
  onComplete: (content: string) => void,
  onError: (error: string) => void
) {
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, stream: false }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (data.type === 'complete') {
      onComplete(data.content);
    } else if (data.type === 'error') {
      onError(data.message);
    }
  } catch (error) {
    onError(error instanceof Error ? error.message : 'Unknown error');
  }
}

// 3. Use in your chat component with toggle
function ChatComponent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [isStreaming, setIsStreaming] = useState(true); // Toggle state

  const sendMessage = async (userMessage: string) => {
    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setCurrentResponse('');

    if (isStreaming) {
      // Streaming mode
      await streamChatResponse(
        'http://127.0.0.1:8000/api/chat/anthropic/stream',
        { message: userMessage, stream: true },
        (delta) => {
          setCurrentResponse(prev => prev + delta);
        },
        () => {
          setMessages(prev => [
            ...prev,
            { role: 'assistant', content: currentResponse }
          ]);
          setCurrentResponse('');
        },
        (error) => {
          console.error('Stream error:', error);
        }
      );
    } else {
      // Non-streaming mode
      await chatResponse(
        'http://127.0.0.1:8000/api/chat/anthropic/stream',
        { message: userMessage },
        (content) => {
          setMessages(prev => [
            ...prev,
            { role: 'assistant', content }
          ]);
        },
        (error) => {
          console.error('Chat error:', error);
        }
      );
    }
  };

  return (
    <div className="chat-container">
      {/* Streaming toggle */}
      <div className="controls">
        <label>
          <input
            type="checkbox"
            checked={isStreaming}
            onChange={(e) => setIsStreaming(e.target.checked)}
          />
          Enable Streaming
        </label>
      </div>

      {/* Messages */}
      {messages.map((msg, i) => (
        <div key={i} className={msg.role}>
          {msg.content}
        </div>
      ))}

      {/* Streaming response indicator */}
      {currentResponse && (
        <div className="assistant streaming">
          {currentResponse}
          <span className="cursor">▋</span>
        </div>
      )}
    </div>
  );
}
```

### Key Integration Points

1. **Streaming State Management**
   - Use a temporary state (`currentResponse`) for the streaming message
   - Append `delta` values as they arrive
   - Move to permanent messages array when stream completes

2. **Visual Feedback**
   - Show a typing cursor while streaming
   - Render text incrementally for better UX
   - Handle loading/error states

3. **Error Handling**
   - Catch network errors
   - Handle API errors from `type: "error"` events
   - Show user-friendly error messages

4. **Image Support**
   - Convert file to base64 for Anthropic endpoint
   - Use the `/upload` endpoint for simpler multipart uploads

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

**Test in browser:**
- API docs UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/`