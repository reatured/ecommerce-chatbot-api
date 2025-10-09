# Frontend Setup Instructions

Step-by-step guide to set up and integrate the E-commerce Chatbot API in your frontend application.

---

## Prerequisites

- Node.js 16+ installed
- npm or yarn package manager
- Modern browser with fetch API support
- Code editor (VS Code recommended)

---

## Step 1: Get the API Running

### Option A: Run Locally

```bash
# Clone or navigate to the API directory
cd ecommerce-chatbot-api

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

# Edit .env and add your API key
# ANTHROPIC_API_KEY=your_key_here

# Run the server
uvicorn api.index:app --reload --port 8000
```

API will be available at: `http://127.0.0.1:8000`

### Option B: Use Deployed API

If the API is already deployed (e.g., on Vercel/Render), get the URL from your backend team.

Example: `https://your-api.vercel.app`

---

## Step 2: Test the API

### Using Browser

Visit: `http://127.0.0.1:8000/docs`

You'll see the interactive API documentation (Swagger UI) where you can test endpoints.

### Using curl

```bash
# Test health endpoint
curl http://127.0.0.1:8000/

# Test Anthropic chat (non-streaming)
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Hello!" \
  -F "stream=false"

```

---

## Step 3: Setup Your Frontend Project

### For React/Vite Projects

```bash
# Create new Vite project (if starting fresh)
npm create vite@latest my-chatbot-app -- --template react-ts
cd my-chatbot-app

# Install dependencies
npm install

# Create environment file
touch .env
```

Add to `.env`:
```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### For Next.js Projects

```bash
# Create new Next.js project (if starting fresh)
npx create-next-app@latest my-chatbot-app --typescript
cd my-chatbot-app

# Create environment file
touch .env.local
```

Add to `.env.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

### For Lovable Projects

Lovable projects are typically React-based. Add environment variable in your Lovable project settings:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## Step 4: Create API Configuration File

Create `src/config/api.ts`:

```typescript
// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',

  ENDPOINTS: {
    ANTHROPIC_CHAT: '/api/chat/anthropic/stream',
  },

  DEFAULTS: {
    MODEL: 'claude-3-5-haiku-latest',
    MAX_TOKENS: 1024,
    STREAM: true,
  }
};

// Helper to build full URL
export const getApiUrl = (endpoint: string) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};
```

---

## Step 5: Create Type Definitions

Create `src/types/chat.ts`:

```typescript
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
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
    input_tokens?: number;
    output_tokens?: number;
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
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

## Step 6: Create API Service

Create `src/services/chatApi.ts`:

```typescript
import { API_CONFIG, getApiUrl } from '../config/api';
import { StreamChunk, CompleteResponse, ChatOptions } from '../types/chat';

// Streaming chat with Anthropic
export async function streamAnthropicChat(
  options: ChatOptions,
  onChunk: (chunk: string) => void,
  onComplete: () => void,
  onError: (error: string) => void
): Promise<void> {
  try {
    const formData = new FormData();
    formData.append('message', options.message);
    formData.append('stream', 'true');
    formData.append('model', options.model || API_CONFIG.DEFAULTS.MODEL);
    formData.append('max_tokens', String(options.max_tokens || API_CONFIG.DEFAULTS.MAX_TOKENS));

    if (options.conversation_history) {
      formData.append('conversation_history', JSON.stringify(options.conversation_history));
    }

    if (options.system) {
      formData.append('system', options.system);
    }

    if (options.image) {
      formData.append('image', options.image);
    }

    const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.ANTHROPIC_CHAT), {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

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
          try {
            const data: StreamChunk = JSON.parse(line.slice(6));

            if (data.type === 'content') {
              onChunk(data.delta || '');
            } else if (data.type === 'done') {
              onComplete();
            } else if (data.type === 'error') {
              onError(data.message || 'Unknown error');
            }
          } catch (e) {
            console.error('Failed to parse chunk:', e);
          }
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error.message : 'Network error');
  }
}

// Non-streaming chat with Anthropic
export async function sendAnthropicChat(
  options: ChatOptions
): Promise<string> {
  const formData = new FormData();
  formData.append('message', options.message);
  formData.append('stream', 'false');
  formData.append('model', options.model || API_CONFIG.DEFAULTS.MODEL);
  formData.append('max_tokens', String(options.max_tokens || API_CONFIG.DEFAULTS.MAX_TOKENS));

  if (options.conversation_history) {
    formData.append('conversation_history', JSON.stringify(options.conversation_history));
  }

  if (options.system) {
    formData.append('system', options.system);
  }

  if (options.image) {
    formData.append('image', options.image);
  }

  const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.ANTHROPIC_CHAT), {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data: CompleteResponse = await response.json();

  if (data.type === 'complete') {
    return data.content;
  }

  throw new Error('Unexpected response type');
}

```

**💡 Note:** For conversation history support, see [CONVERSATION_HISTORY.md](CONVERSATION_HISTORY.md)

---

## Step 7: Create React Hook

Create `src/hooks/useChat.ts`:

```typescript
import { useState, useCallback } from 'react';
import { Message } from '../types/chat';
import { streamAnthropicChat, sendAnthropicChat } from '../services/chatApi';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (
    userMessage: string,
    stream: boolean = true
  ) => {
    // Add user message
    const userMsg: Message = {
      role: 'user',
      content: userMessage,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);
    setCurrentResponse('');

    // Prepare conversation history (exclude the message we're about to send)
    const history = messages.slice(); // All previous messages

    try {
      if (stream) {
        // Streaming mode
        let fullResponse = '';

        await streamAnthropicChat(
          {
            message: userMessage,
            conversation_history: history,
            stream: true
          },
          (chunk) => {
            fullResponse += chunk;
            setCurrentResponse(fullResponse);
          },
          () => {
            const assistantMsg: Message = {
              role: 'assistant',
              content: fullResponse,
              timestamp: new Date()
            };
            setMessages(prev => [...prev, assistantMsg]);
            setCurrentResponse('');
            setIsLoading(false);
          },
          (errorMsg) => {
            setError(errorMsg);
            setIsLoading(false);
          }
        );
      } else {
        // Non-streaming mode
        const response = await sendAnthropicChat({
          message: userMessage,
          conversation_history: history,
          stream: false
        });
        const assistantMsg: Message = {
          role: 'assistant',
          content: response,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, assistantMsg]);
        setIsLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      setIsLoading(false);
    }
  }, [messages]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentResponse('');
    setError(null);
  }, []);

  return {
    messages,
    currentResponse,
    isLoading,
    error,
    sendMessage,
    clearMessages
  };
}
```

---

## Step 8: Create Chat Component

Create `src/components/ChatBot.tsx`:

```typescript
import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import './ChatBot.css';

export function ChatBot() {
  const { messages, currentResponse, isLoading, error, sendMessage, clearMessages } = useChat();
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      sendMessage(input, isStreaming);
      setInput('');
    }
  };

  return (
    <div className="chatbot-container">
      {/* Header */}
      <div className="chatbot-header">
        <h2>E-commerce Chatbot</h2>
        <div className="controls">
          <label className="toggle">
            <input
              type="checkbox"
              checked={isStreaming}
              onChange={(e) => setIsStreaming(e.target.checked)}
            />
            <span>Streaming Mode</span>
          </label>
          <button onClick={clearMessages} className="clear-btn">
            Clear Chat
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="chatbot-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}

        {/* Streaming response */}
        {currentResponse && (
          <div className="message assistant streaming">
            <div className="message-content">
              {currentResponse}
              <span className="cursor">▋</span>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="chatbot-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
```

Create `src/components/ChatBot.css`:

```css
.chatbot-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.chatbot-header {
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chatbot-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.clear-btn {
  padding: 0.5rem 1rem;
  background: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.clear-btn:hover {
  background: #d32f2f;
}

.chatbot-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message {
  display: flex;
  max-width: 70%;
}

.message.user {
  align-self: flex-end;
}

.message.user .message-content {
  background: #2196f3;
  color: white;
  padding: 0.75rem 1rem;
  border-radius: 12px 12px 0 12px;
}

.message.assistant {
  align-self: flex-start;
}

.message.assistant .message-content {
  background: #f5f5f5;
  color: #333;
  padding: 0.75rem 1rem;
  border-radius: 12px 12px 12px 0;
}

.message.streaming .cursor {
  animation: blink 1s infinite;
  margin-left: 2px;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.error-message {
  background: #ffebee;
  color: #c62828;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border-left: 4px solid #f44336;
}

.chatbot-input {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid #e0e0e0;
}

.chatbot-input input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.chatbot-input input:focus {
  outline: none;
  border-color: #2196f3;
}

.chatbot-input button {
  padding: 0.75rem 1.5rem;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.chatbot-input button:hover:not(:disabled) {
  background: #1976d2;
}

.chatbot-input button:disabled {
  background: #ccc;
  cursor: not-allowed;
}
```

---

## Step 9: Use the Component

Update `src/App.tsx`:

```typescript
import { ChatBot } from './components/ChatBot';
import './App.css';

function App() {
  return (
    <div className="App">
      <ChatBot />
    </div>
  );
}

export default App;
```

---

## Step 10: Run Your Frontend

```bash
# Start development server
npm run dev

# Open browser
# Vite: http://localhost:5173
# Next.js: http://localhost:3000
```

---

## Troubleshooting

### Issue: CORS Error

**Error:** `Access to fetch at 'http://127.0.0.1:8000' blocked by CORS policy`

**Solution:** Make sure the backend API is running and has CORS enabled (already configured).

### Issue: Connection Refused

**Error:** `Failed to fetch` or `Network error`

**Solution:**
1. Check if API is running: `curl http://127.0.0.1:8000/`
2. Verify API URL in `.env` file
3. Check firewall settings

### Issue: API Key Error

**Error:** `ANTHROPIC_API_KEY not configured`

**Solution:** Add your API keys to the backend `.env` file

### Issue: Streaming Not Working

**Error:** Response appears all at once instead of streaming

**Solution:**
1. Check `stream: true` is set in request
2. Verify you're using `response.body.getReader()` correctly
3. Check browser console for errors

---

## Production Deployment

### Update Environment Variables

```bash
# For production API URL
VITE_API_BASE_URL=https://your-api-domain.com
```

### Build for Production

```bash
# Vite
npm run build

# Next.js
npm run build
npm start
```

---

## Next Steps

1. ✅ Read [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md) for advanced examples
2. ✅ Test all endpoints in Swagger UI: `http://127.0.0.1:8000/docs`
3. ✅ Implement image upload feature
4. ✅ Add error boundaries
5. ✅ Implement retry logic
6. ✅ Add analytics/logging
7. ✅ Test on mobile devices

---

## Resources

- **API Documentation:** `http://127.0.0.1:8000/docs`
- **Integration Guide:** [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md)
- **Main README:** [README.md](./README.md)

---

**Need Help?** Contact the backend team or check the API documentation.

**Last Updated:** 2025-10-09
