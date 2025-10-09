# E-commerce Chatbot API

FastAPI backend providing AI-powered chat capabilities via streaming endpoints. Compatible with OpenAI-style chat completions format.

## Available APIs

### 1. Anthropic Chat
**Endpoint:** `POST /api/chat/anthropic/stream`

Chat responses from Claude (Anthropic). Supports both streaming and non-streaming modes.
Accepts file uploads via `multipart/form-data`.

**Request Parameters:**
- `message` (text, required) - Your message to Claude
- `conversation_history` (text, optional) - JSON string of previous messages to maintain context
  - Format: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`
  - See [CONVERSATION_HISTORY.md](CONVERSATION_HISTORY.md) for detailed guide
- `system` (text, optional) - System message to set Claude's behavior and context
- `image` (file, optional) - Image file to upload
- `image_media_type` (text, optional, default: "image/jpeg") - Image MIME type
- `model` (text, optional, default: "claude-3-5-haiku-latest") - Model name
- `max_tokens` (integer, optional, default: 1024) - Max response tokens
- `stream` (boolean, optional, default: true) - Enable streaming

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

**Examples:**

```bash
# Text only (streaming)
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Recommend gift ideas for coffee lovers" \
  -F "stream=true"

# With system message
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Recommend some products" \
  -F "system=You are a helpful e-commerce shopping assistant. Be concise and friendly." \
  -F "stream=true"

# With image upload
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=What's in this image?" \
  -F "image=@photo.jpg" \
  -F "stream=true"

# With conversation history (multi-turn conversation)
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Which one is best for music?" \
  -F 'conversation_history=[{"role":"user","content":"What are good headphones?"},{"role":"assistant","content":"I recommend Sony WH-1000XM5, Bose QuietComfort, or Apple AirPods Max..."}]' \
  -F "stream=false"

# Complete example with all parameters
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=What product is this and where can I buy it?" \
  -F "system=You are a product identification expert. Identify products and suggest where to purchase them." \
  -F "image=@product.jpg" \
  -F "model=claude-3-5-haiku-latest" \
  -F "max_tokens=2048" \
  -F "stream=false"
```

**📚 Documentation:**
- Conversation history guide: [CONVERSATION_HISTORY.md](CONVERSATION_HISTORY.md)
- Error reference: [ERROR_REFERENCE.md](ERROR_REFERENCE.md)
- Frontend fixes: [FRONTEND_FIX.md](FRONTEND_FIX.md)

---

### 2. Health Check
**Endpoint:** `GET /`

Returns API status and available endpoints.

**Response:**
```json
{
  "status": "ok",
  "message": "E-commerce Chatbot API is running",
  "endpoints": {
    "anthropic_chat": "/api/chat/anthropic/stream"
  },
  "notes": {
    "anthropic_chat": "Accepts multipart/form-data with optional file uploads",
    "streaming": "Supports streaming toggle via 'stream' parameter (default: true)"
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
  message: string,
  conversationHistory?: Array<{role: string, content: string}>,
  onChunk: (text: string) => void,
  onComplete: () => void,
  onError: (error: string) => void
) {
  try {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('stream', 'true');

    if (conversationHistory && conversationHistory.length > 0) {
      formData.append('conversation_history', JSON.stringify(conversationHistory));
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      body: formData,
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
  message: string,
  conversationHistory?: Array<{role: string, content: string}>,
  onComplete: (content: string) => void,
  onError: (error: string) => void
) {
  try {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('stream', 'false');

    if (conversationHistory && conversationHistory.length > 0) {
      formData.append('conversation_history', JSON.stringify(conversationHistory));
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      body: formData,
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

// 3. Use in your chat component with toggle and conversation history
interface Message {
  role: 'user' | 'assistant';
  content: string;
}

function ChatComponent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [isStreaming, setIsStreaming] = useState(true);

  const sendMessage = async (userMessage: string) => {
    // Add user message to chat
    const newUserMessage: Message = { role: 'user', content: userMessage };
    setMessages(prev => [...prev, newUserMessage]);
    setCurrentResponse('');

    // Prepare conversation history (all messages except the one we're about to send)
    const history = messages;

    if (isStreaming) {
      // Streaming mode
      let fullResponse = '';
      await streamChatResponse(
        'http://127.0.0.1:8000/api/chat/anthropic/stream',
        userMessage,
        history,
        (delta) => {
          fullResponse += delta;
          setCurrentResponse(fullResponse);
        },
        () => {
          setMessages(prev => [
            ...prev,
            { role: 'assistant', content: fullResponse }
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
        userMessage,
        history,
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

1. **Conversation History Management**
   - Store all messages in React state
   - Send conversation history with each new message
   - API is stateless - frontend manages all context

2. **Streaming State Management**
   - Use a temporary state (`currentResponse`) for the streaming message
   - Append `delta` values as they arrive
   - Move to permanent messages array when stream completes

3. **Visual Feedback**
   - Show a typing cursor while streaming
   - Render text incrementally for better UX
   - Handle loading/error states

4. **Error Handling**
   - Catch network errors
   - Handle API errors from `type: "error"` events
   - Show user-friendly error messages

5. **Image Support**
   - Use FormData to append image files directly
   - API accepts multipart/form-data for file uploads

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

**Test in browser:**
- API docs UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/`