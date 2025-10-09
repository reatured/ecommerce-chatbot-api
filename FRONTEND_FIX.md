# Frontend Fix: Empty Content in Conversation History

## The Problem

Your frontend is sending conversation history with **empty `content`** fields, which causes this error:

```
Error code: 400 - messages.4: all messages must have non-empty content except for the optional final assistant message
```

## The Solution

The backend API has been updated to **automatically filter out** messages with empty content, so the workflow should now work. However, it's better to fix this in the frontend as well.

---

## Frontend Code Fixes

### Issue 1: Storing Empty Messages

**Problem:** When a message is sent, the frontend might be storing it with empty content temporarily.

**Bad Code:**
```typescript
// ❌ Don't do this
const sendMessage = async (userMessage: string) => {
  // Adding empty message before getting response
  setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

  // Then updating it later...
  setMessages(prev => [...prev.slice(0, -1), { role: 'assistant', content: response }]);
};
```

**Good Code:**
```typescript
// ✅ Do this instead
const sendMessage = async (userMessage: string) => {
  // Add user message
  const newUserMessage: Message = { role: 'user', content: userMessage };
  setMessages(prev => [...prev, newUserMessage]);

  // Use separate state for streaming response
  let fullResponse = '';
  setCurrentResponse(''); // Temporary state, not in messages array

  // ... stream response

  // Only add to messages when complete
  setMessages(prev => [...prev, { role: 'assistant', content: fullResponse }]);
  setCurrentResponse('');
};
```

---

### Issue 2: Filtering Before Sending

**Solution:** Filter out empty messages before sending to API:

```typescript
const sendMessage = async (userMessage: string) => {
  // Add user message
  setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

  // Filter out empty messages from history
  const validHistory = messages.filter(msg => {
    if (typeof msg.content === 'string') {
      return msg.content.trim().length > 0;
    }
    if (Array.isArray(msg.content)) {
      return msg.content.length > 0;
    }
    return false;
  });

  // Send to API
  const formData = new FormData();
  formData.append('message', userMessage);
  if (validHistory.length > 0) {
    formData.append('conversation_history', JSON.stringify(validHistory));
  }
  formData.append('stream', 'true');

  const response = await fetch(API_URL, {
    method: 'POST',
    body: formData
  });

  // ... handle response
};
```

---

### Issue 3: Complete Working Example

Here's a complete React component that handles this correctly:

```typescript
import { useState } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string | Array<any>;
}

function ChatBot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (userMessage: string, imageFile?: File) => {
    if (!userMessage.trim() && !imageFile) return;

    // Add user message to state
    const newUserMessage: Message = {
      role: 'user',
      content: userMessage
    };
    setMessages(prev => [...prev, newUserMessage]);
    setIsLoading(true);
    setCurrentResponse('');

    try {
      // Filter valid history (non-empty messages only)
      const validHistory = messages.filter(msg => {
        if (typeof msg.content === 'string') {
          return msg.content.trim().length > 0;
        }
        if (Array.isArray(msg.content)) {
          return msg.content.length > 0;
        }
        return false;
      });

      // Prepare form data
      const formData = new FormData();
      formData.append('message', userMessage);
      formData.append('stream', 'true');

      if (validHistory.length > 0) {
        formData.append('conversation_history', JSON.stringify(validHistory));
      }

      if (imageFile) {
        formData.append('image', imageFile);
      }

      // Send request
      const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Handle streaming
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      if (!reader) throw new Error('No reader');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'content') {
                fullResponse += data.delta;
                setCurrentResponse(fullResponse);
              } else if (data.type === 'done') {
                // Add complete response to messages
                setMessages(prev => [...prev, {
                  role: 'assistant',
                  content: fullResponse
                }]);
                setCurrentResponse('');
              } else if (data.type === 'error') {
                console.error('API Error:', data.message);
                alert(`Error: ${data.message}`);
              }
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Failed to send message. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(input);
      setInput('');
    }
  };

  return (
    <div className="chatbot">
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {typeof msg.content === 'string' ? msg.content : '[Image + Text]'}
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

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

export default ChatBot;
```

---

## Key Points to Remember

1. **Never add empty messages to your messages array**
   - Use a separate `currentResponse` state for streaming
   - Only add to `messages` when response is complete

2. **Filter before sending**
   - Remove any messages with empty `content` before sending to API
   - Backend now does this automatically, but frontend should too

3. **Handle streaming correctly**
   - Build up response in temporary state
   - Add to messages array only when stream is done

4. **Validate input**
   - Check that user message is not empty
   - Check that image file exists if required

---

## Testing Your Fix

Use the browser DevTools Network tab to inspect the request:

1. Open DevTools → Network tab
2. Send a message with image
3. Click on the request to `/api/chat/anthropic/stream`
4. Check the Form Data section
5. Verify `conversation_history` doesn't have empty content

**Example of valid conversation_history:**
```json
[
  {"role": "user", "content": "Hello"},
  {"role": "assistant", "content": "Hi there!"},
  {"role": "user", "content": "What's this?"}
]
```

**Example of invalid conversation_history (will be filtered out by backend):**
```json
[
  {"role": "user", "content": ""},  ← Empty!
  {"role": "assistant", "content": "Hi there!"},
  {"role": "user", "content": "What's this?"}
]
```

---

## Backend Protection

The backend now includes automatic filtering of empty messages:

```python
# In api/index.py lines 177-184
valid_history = [
    msg for msg in history
    if msg.get('content') and (
        isinstance(msg['content'], str) and msg['content'].strip()
        or isinstance(msg['content'], list) and len(msg['content']) > 0
    )
]
```

This means your workflow should now work **even if** the frontend sends empty messages, but it's still best practice to fix the frontend.

---

## Common Mistakes

### Mistake 1: Pre-adding Assistant Message
```typescript
// ❌ Don't do this
setMessages([...messages, { role: 'assistant', content: '' }]);
// Then trying to update it later
```

### Mistake 2: Not Trimming Strings
```typescript
// ❌ Bad
if (msg.content) { ... }

// ✅ Good
if (msg.content && msg.content.trim()) { ... }
```

### Mistake 3: Mixing Streaming State with Messages Array
```typescript
// ❌ Don't add partial responses to messages
setMessages([...messages, { role: 'assistant', content: partialResponse }]);

// ✅ Use separate state
setCurrentResponse(partialResponse);
```

---

**The fix is now live on the backend. Your workflow should work!**

If you still encounter issues, check your frontend code for the patterns above.
