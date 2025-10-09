# Frontend Integration Guide

Complete guide for integrating the E-commerce Chatbot API into your frontend application.

## Table of Contents
1. [Quick Start](#quick-start)
2. [API Endpoints](#api-endpoints)
3. [Streaming vs Non-Streaming](#streaming-vs-non-streaming)
4. [Complete Examples](#complete-examples)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)

---

## Quick Start

### Installation
No additional packages needed - uses native `fetch` API available in all modern browsers.

### Base URL
```typescript
const API_BASE_URL = "http://127.0.0.1:8000"; // Change to your deployed URL
```

---

## API Endpoints

### Anthropic Chat (Claude)
**URL:** `POST /api/chat/anthropic/stream`

**Parameters:**
- `message` (string, required) - User message
- `conversation_history` (JSON string, optional) - Previous messages for context
- `system` (string, optional) - System message to control AI behavior
- `stream` (boolean, optional, default: true) - Enable streaming
- `image` (file, optional) - Image file upload
- `image_media_type` (string, optional) - MIME type (default: "image/jpeg")
- `model` (string, optional) - Model name (default: "claude-3-5-haiku-latest")
- `max_tokens` (integer, optional) - Max response tokens (default: 1024)

**💡 See [CONVERSATION_HISTORY.md](CONVERSATION_HISTORY.md) for conversation history examples.**

---

## Streaming vs Non-Streaming

### Streaming Mode (`stream: true`)
- **Response Type:** Server-Sent Events (SSE)
- **Use Case:** Real-time chat with typing effect
- **User Experience:** Text appears word-by-word

**Response Format:**
```
data: {"type": "content", "delta": "Hello", "index": 0}
data: {"type": "content", "delta": " world", "index": 0}
data: {"type": "finish", "finish_reason": "stop"}
data: {"type": "done"}
```

### Non-Streaming Mode (`stream: false`)
- **Response Type:** JSON
- **Use Case:** Complete responses needed at once
- **User Experience:** Full text appears instantly

**Response Format:**
```json
{
  "type": "complete",
  "content": "Hello world...",
  "finish_reason": "end_turn",
  "model": "claude-3-5-haiku-20241022",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 50
  }
}
```

---

## Complete Examples

### Example 1: Simple Text Chat (Streaming)

```typescript
async function sendMessage(userMessage: string): Promise<void> {
  const formData = new FormData();
  formData.append('message', userMessage);
  formData.append('stream', 'true');

  const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
    method: 'POST',
    body: formData
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) throw new Error('No reader available');

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));

        if (data.type === 'content') {
          console.log(data.delta); // Display this chunk
        } else if (data.type === 'done') {
          console.log('Stream complete!');
        }
      }
    }
  }
}

// Usage
sendMessage("What are the best coffee makers?");
```

### Example 2: Non-Streaming Request

```typescript
async function sendMessageSync(userMessage: string): Promise<string> {
  const formData = new FormData();
  formData.append('message', userMessage);
  formData.append('stream', 'false');

  const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
    method: 'POST',
    body: formData
  });

  const data = await response.json();

  if (data.type === 'complete') {
    return data.content;
  } else if (data.type === 'error') {
    throw new Error(data.message);
  }

  throw new Error('Unexpected response type');
}

// Usage
const answer = await sendMessageSync("What are the best coffee makers?");
console.log(answer);
```

### Example 3: React Component with Conversation History

```typescript
import { useState } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

function ChatBot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [isStreaming, setIsStreaming] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (userMessage: string) => {
    // Add user message
    const newUserMessage: Message = { role: 'user', content: userMessage };
    setMessages(prev => [...prev, newUserMessage]);
    setIsLoading(true);
    setCurrentResponse('');

    // Prepare conversation history (all messages except the one we're sending)
    const history = messages;

    try {
      if (isStreaming) {
        // Streaming mode
        const formData = new FormData();
        formData.append('message', userMessage);
        formData.append('stream', 'true');
        if (history.length > 0) {
          formData.append('conversation_history', JSON.stringify(history));
        }

        const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
          method: 'POST',
          body: formData
        });

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';

        if (!reader) throw new Error('No reader available');

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'content') {
                fullResponse += data.delta;
                setCurrentResponse(fullResponse);
              } else if (data.type === 'done') {
                setMessages(prev => [...prev, { role: 'assistant', content: fullResponse }]);
                setCurrentResponse('');
              }
            }
          }
        }
      } else {
        // Non-streaming mode
        const formData = new FormData();
        formData.append('message', userMessage);
        formData.append('stream', 'false');
        if (history.length > 0) {
          formData.append('conversation_history', JSON.stringify(history));
        }

        const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();

        if (data.type === 'complete') {
          setMessages(prev => [...prev, { role: 'assistant', content: data.content }]);
        }
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chatbot">
      {/* Streaming Toggle */}
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
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}

        {/* Streaming response */}
        {currentResponse && (
          <div className="message assistant streaming">
            {currentResponse}
            <span className="cursor">▋</span>
          </div>
        )}
      </div>

      {/* Input */}
      <input
        type="text"
        placeholder="Type a message..."
        onKeyPress={(e) => {
          if (e.key === 'Enter' && e.currentTarget.value) {
            sendMessage(e.currentTarget.value);
            e.currentTarget.value = '';
          }
        }}
        disabled={isLoading}
      />
    </div>
  );
}
```

### Example 4: Image Upload

```typescript
async function sendMessageWithImage(
  message: string,
  imageFile: File
): Promise<void> {
  const formData = new FormData();
  formData.append('message', message);
  formData.append('image', imageFile);
  formData.append('stream', 'true');

  const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
    method: 'POST',
    body: formData // Don't set Content-Type header, browser will set it
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) throw new Error('No reader available');

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));

        if (data.type === 'content') {
          console.log(data.delta);
        }
      }
    }
  }
}

// Usage with file input
const fileInput = document.querySelector<HTMLInputElement>('#image-input');
const file = fileInput?.files?.[0];

if (file) {
  await sendMessageWithImage("What's in this image?", file);
}
```

### Example 5: With System Message

```typescript
async function sendMessageWithSystem(
  userMessage: string,
  systemMessage: string
): Promise<void> {
  const formData = new FormData();
  formData.append('message', userMessage);
  formData.append('system', systemMessage);
  formData.append('stream', 'true');

  const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
    method: 'POST',
    body: formData
  });

  // Process streaming response...
}

// Usage
await sendMessageWithSystem(
  "Recommend some products",
  "You are a helpful e-commerce shopping assistant. Be concise and friendly."
);
```

---

## Error Handling

### Handle Network Errors

```typescript
async function sendMessageWithErrorHandling(message: string) {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, stream: true })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Process response...

  } catch (error) {
    if (error instanceof TypeError) {
      console.error('Network error - check if API is running');
    } else if (error instanceof Error) {
      console.error('Error:', error.message);
    }
  }
}
```

### Handle API Errors

```typescript
for (const line of lines) {
  if (line.startsWith('data: ')) {
    const data = JSON.parse(line.slice(6));

    if (data.type === 'error') {
      console.error('API Error:', data.message);
      // Show error to user
      showErrorNotification(data.message);
      break;
    }
  }
}
```

---

## Best Practices

### 1. Use Environment Variables

```typescript
// .env
VITE_API_BASE_URL=http://127.0.0.1:8000

// config.ts
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
```

### 2. Create Reusable Hooks (React)

```typescript
// hooks/useChat.ts
import { useState } from 'react';

export function useChat(apiUrl: string) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (message: string, stream: boolean = true) => {
    setIsLoading(true);
    // Implementation...
    setIsLoading(false);
  };

  return { messages, isLoading, sendMessage };
}
```

### 3. Handle Abort/Cancel

```typescript
const abortController = new AbortController();

const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: userMessage }),
  signal: abortController.signal
});

// To cancel:
abortController.abort();
```

### 4. Add Loading States

```typescript
const [isLoading, setIsLoading] = useState(false);

const sendMessage = async (message: string) => {
  setIsLoading(true);
  try {
    // API call...
  } finally {
    setIsLoading(false);
  }
};

return (
  <button onClick={() => sendMessage(input)} disabled={isLoading}>
    {isLoading ? 'Sending...' : 'Send'}
  </button>
);
```

### 5. Debounce Typing Indicator

```typescript
import { useEffect, useState } from 'react';

function useTypingIndicator(isStreaming: boolean) {
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    if (!isStreaming) return;

    const interval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);

    return () => clearInterval(interval);
  }, [isStreaming]);

  return showCursor;
}
```

### 6. Retry Failed Requests

```typescript
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  maxRetries = 3
): Promise<Response> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return response;

      if (response.status >= 500) {
        // Server error, retry
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        continue;
      }

      throw new Error(`HTTP ${response.status}`);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
  throw new Error('Max retries exceeded');
}
```

---

## TypeScript Types

```typescript
// types.ts
export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface StreamChunk {
  type: 'content' | 'finish' | 'done' | 'error';
  delta?: string;
  index?: number;
  finish_reason?: string;
  message?: string;
}

export interface CompleteResponse {
  type: 'complete';
  content: string;
  finish_reason: string;
  model: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

export interface ChatOptions {
  message: string;
  conversation_history?: Message[];
  system?: string;
  stream?: boolean;
  image?: File;
  image_media_type?: string;
  model?: string;
  max_tokens?: number;
}
```

---

## CORS Setup

If you encounter CORS errors, ensure your API has CORS middleware configured (already set up in the backend):

```python
# Already configured in api/index.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, restrict origins:
```python
allow_origins=["https://yourfrontend.com"]
```

---

## Production Checklist

- [ ] Update API base URL to production endpoint
- [ ] Add request timeout handling
- [ ] Implement retry logic for failed requests
- [ ] Add proper error messages for users
- [ ] Add loading/typing indicators
- [ ] Test with slow network conditions
- [ ] Handle connection drops gracefully
- [ ] Add analytics/logging
- [ ] Secure API keys (use environment variables)
- [ ] Implement rate limiting on frontend
- [ ] Add request cancellation support
- [ ] Test image upload size limits

---

## Need Help?

- Check the main [README.md](./README.md) for API documentation
- Test endpoints at `http://127.0.0.1:8000/docs` (Swagger UI)
- Review example requests in the API docs

---

**Last Updated:** 2025-10-09
