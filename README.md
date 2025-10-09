# E-commerce Chatbot API

FastAPI backend providing AI-powered chat and search capabilities via streaming endpoints. Compatible with OpenAI-style chat completions format.

## Available APIs

### 1. Anthropic Chat Stream
**Endpoint:** `POST /api/chat/anthropic/stream`

Streams AI chat responses from Claude (Anthropic) using Server-Sent Events (SSE).

**Request:**
```json
{
  "message": "Recommend gift ideas for coffee lovers",
  "image": "base64_encoded_image_data",  // optional
  "image_media_type": "image/jpeg",       // optional, default: "image/jpeg"
  "model": "claude-3-5-sonnet-20241022",  // optional
  "max_tokens": 1024                      // optional
}
```

**Response Format:** Server-Sent Events (SSE)
```
data: {"type": "content", "delta": "Hello", "index": 0}
data: {"type": "content", "delta": "! I'd", "index": 0}
data: {"type": "content", "delta": " be happy", "index": 0}
data: {"type": "finish", "finish_reason": "stop"}
data: {"type": "done"}
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

### 2. Anthropic Chat with File Upload
**Endpoint:** `POST /api/chat/anthropic/stream/upload`

Same as above but accepts file uploads (perfect for testing in `/docs` UI).

**Request:** `multipart/form-data`
- `message` (text, required)
- `image` (file, optional)
- `model` (text, optional)
- `max_tokens` (integer, optional)

**Response:** Same SSE format as regular Anthropic endpoint

**Example:**
```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream/upload \
  -F "message=What's in this image?" \
  -F "image=@photo.jpg"
```

---

### 3. Perplexity Chat Stream
**Endpoint:** `POST /api/chat/perplexity/stream`

Streams web-grounded chat responses from Perplexity AI using the Sonar model.

**Request:**
```json
{
  "query": "What are the latest AI developments?"
}
```

**Response Format:** Server-Sent Events (SSE)
```
data: {"type": "content", "delta": "Based on", "index": 0}
data: {"type": "content", "delta": " recent information", "index": 0}
data: {"type": "finish", "finish_reason": "stop"}
data: {"type": "done"}
```

**Response Event Types:**
- `content` - Text chunks from the AI response
  - `delta`: The text content chunk
  - `index`: Choice index
- `finish` - Completion indicator
  - `finish_reason`: Reason for completion
- `done` - Stream completion marker
- `error` - Error message if something fails

**Example:**
```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/perplexity/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "best wireless headphones 2025"}'
```

---

### 4. Health Check
**Endpoint:** `GET /`

Returns API status and available endpoints.

**Response:**
```json
{
  "status": "ok",
  "message": "E-commerce Chatbot API is running",
  "endpoints": {
    "perplexity_search": "/api/chat/perplexity/stream",
    "anthropic_chat": "/api/chat/anthropic/stream",
    "anthropic_chat_upload": "/api/chat/anthropic/stream/upload"
  }
}
```

---

## Integration Guide for Lovable

### Frontend Implementation (React/TypeScript)

Here's how to integrate these streaming endpoints into your Lovable chatbot application:

```typescript
// 1. Set up EventSource to consume SSE
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
              // Append the delta to your chat message
              onChunk(parsed.delta);
            } else if (parsed.type === 'finish') {
              // Stream finished successfully
              console.log('Finish reason:', parsed.finish_reason);
            } else if (parsed.type === 'done') {
              // All done
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

// 2. Use in your chat component
function ChatComponent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');

  const sendMessage = async (userMessage: string) => {
    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    // Reset current response
    setCurrentResponse('');

    // Stream AI response
    await streamChatResponse(
      'http://127.0.0.1:8000/api/chat/anthropic/stream',
      { message: userMessage },
      (delta) => {
        // Append each chunk to the current response
        setCurrentResponse(prev => prev + delta);
      },
      () => {
        // When complete, add to messages array
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: currentResponse }
        ]);
        setCurrentResponse('');
      },
      (error) => {
        console.error('Stream error:', error);
        // Show error to user
      }
    );
  };

  return (
    <div className="chat-container">
      {messages.map((msg, i) => (
        <div key={i} className={msg.role}>
          {msg.content}
        </div>
      ))}
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