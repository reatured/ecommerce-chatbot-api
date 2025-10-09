# Conversation History Guide

## Understanding Stateless APIs

The E-commerce Chatbot API is **stateless** - it does NOT automatically remember previous messages. Each API request is independent.

**To maintain a conversation, you must send the entire conversation history with each request.**

---

## How It Works

### 1. First Message (No History)

```bash
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=What are good gifts for coffee lovers?" \
  -F "stream=false"
```

**Response:**
```
"Consider a French press, artisan coffee beans, or a milk frother..."
```

### 2. Follow-up Message (With History)

To continue the conversation, send the previous messages as JSON:

```bash
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=What about under $50?" \
  -F 'conversation_history=[
    {"role":"user","content":"What are good gifts for coffee lovers?"},
    {"role":"assistant","content":"Consider a French press, artisan coffee beans, or a milk frother..."}
  ]' \
  -F "stream=false"
```

**Response:**
```
"For under $50, I'd recommend a pour-over coffee maker ($25), specialty coffee subscription ($30/month), or a quality burr grinder ($45)..."
```

Claude now understands the context!

---

## Conversation History Format

### JSON Structure

```json
[
  {
    "role": "user",
    "content": "First user message"
  },
  {
    "role": "assistant",
    "content": "First assistant response"
  },
  {
    "role": "user",
    "content": "Second user message"
  },
  {
    "role": "assistant",
    "content": "Second assistant response"
  }
]
```

### Rules

1. **Alternating roles**: user → assistant → user → assistant
2. **Always end with assistant's last response** before your new message
3. **Don't include the current message** - that goes in the `message` parameter
4. **Valid roles**: `"user"` or `"assistant"` only
5. **Content can be**:
   - String for text-only
   - Array for multimodal (images + text)

---

## Complete Examples

### Example 1: Basic Conversation

**Request 1** (First message):
```bash
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Tell me about the iPhone 15" \
  -F "stream=false"
```

**Response 1:**
```
"The iPhone 15 features a 6.1-inch display, A16 Bionic chip, and improved camera system..."
```

**Request 2** (Follow-up):
```bash
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=How much does it cost?" \
  -F 'conversation_history=[
    {"role":"user","content":"Tell me about the iPhone 15"},
    {"role":"assistant","content":"The iPhone 15 features a 6.1-inch display, A16 Bionic chip, and improved camera system..."}
  ]' \
  -F "stream=false"
```

**Response 2:**
```
"The iPhone 15 starts at $799 for the 128GB model..."
```

---

### Example 2: Multi-Turn Conversation

```bash
# Turn 1: User asks
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=I need a laptop for programming" \
  -F "stream=false"

# Response: "I'd recommend the MacBook Pro or Dell XPS..."

# Turn 2: User follows up
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Which is better for Python development?" \
  -F 'conversation_history=[
    {"role":"user","content":"I need a laptop for programming"},
    {"role":"assistant","content":"I'\''d recommend the MacBook Pro or Dell XPS..."}
  ]' \
  -F "stream=false"

# Response: "For Python development, either works well. The MacBook Pro has..."

# Turn 3: User asks more
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=What about the price difference?" \
  -F 'conversation_history=[
    {"role":"user","content":"I need a laptop for programming"},
    {"role":"assistant","content":"I'\''d recommend the MacBook Pro or Dell XPS..."},
    {"role":"user","content":"Which is better for Python development?"},
    {"role":"assistant","content":"For Python development, either works well. The MacBook Pro has..."}
  ]' \
  -F "stream=false"
```

---

### Example 3: Conversation with System Message

```bash
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Can you recommend something?" \
  -F "system=You are a helpful shopping assistant. Be enthusiastic and concise." \
  -F 'conversation_history=[
    {"role":"user","content":"I love outdoor activities"},
    {"role":"assistant","content":"That'\''s awesome! Have you tried hiking or camping?"},
    {"role":"user","content":"Yes, I go camping often"}
  ]' \
  -F "stream=false"
```

**Note:** System message applies to the entire conversation.

---

## Frontend Implementation

### React/TypeScript Example

```typescript
import { useState } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

function ChatBot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    if (!input.trim()) return;

    // Add user message to local state
    const userMessage: Message = { role: 'user', content: input };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);

    // Prepare conversation history (all messages EXCEPT the current one)
    const history = messages; // Don't include the message we're about to send

    // Create form data
    const formData = new FormData();
    formData.append('message', input);
    formData.append('conversation_history', JSON.stringify(history));
    formData.append('stream', 'false');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      // Add assistant response to local state
      if (data.type === 'complete') {
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.content
        };
        setMessages([...updatedMessages, assistantMessage]);
      }
    } catch (error) {
      console.error('Error:', error);
    }

    setInput('');
  };

  return (
    <div>
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role}>
            {msg.content}
          </div>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}
```

### Key Points for Frontend

1. **Store messages locally** in your frontend state
2. **Before each request**: Convert messages array to JSON
3. **After each response**: Add assistant's response to your state
4. **The API doesn't store anything** - your frontend manages all history

---

## Using in Swagger UI (`/docs`)

### Step 1: First Message

1. Go to `http://127.0.0.1:8000/docs`
2. Try out `POST /api/chat/anthropic/stream`
3. Fill in:
   - `message`: "What are good headphones?"
   - `stream`: false
4. Execute
5. **Copy the response** (you'll need it!)

### Step 2: Follow-up Message

1. Click "Try it out" again
2. Fill in:
   - `message`: "Which one is best for music?"
   - `conversation_history`:
   ```json
   [
     {"role":"user","content":"What are good headphones?"},
     {"role":"assistant","content":"<paste the previous response here>"}
   ]
   ```
   - `stream`: false
3. Execute

Claude now remembers the context!

---

## Important Notes

### ✅ Do This

- Store conversation history in your frontend/application
- Send only relevant history (last 5-10 exchanges is usually enough)
- Include both user and assistant messages
- Keep messages in chronological order

### ❌ Don't Do This

- Don't expect the API to remember previous requests
- Don't include the current message in `conversation_history`
- Don't mix up the order of messages
- Don't forget to alternate user/assistant roles

---

## Conversation History Limits

### Token Limits

- **Anthropic Claude**: ~200K tokens total (including history + new message + response)
- Keep conversation history reasonable (last 10-20 exchanges)
- Very old messages can be truncated to save tokens

### Best Practices

1. **Summarize old conversations** if they get too long
2. **Keep only relevant context** - remove very old messages
3. **Monitor token usage** in API responses
4. **Consider conversation "reset"** after topic changes

---

## Troubleshooting

### Error: "messages: roles must alternate between 'user' and 'assistant'"

**Problem:** Your conversation history has consecutive messages with the same role.

**Solution:** Ensure alternating roles:
```json
✅ Correct:
[
  {"role":"user","content":"Hello"},
  {"role":"assistant","content":"Hi!"},
  {"role":"user","content":"How are you?"}
]

❌ Wrong:
[
  {"role":"user","content":"Hello"},
  {"role":"user","content":"How are you?"}  // Two user messages in a row!
]
```

### Error: "Invalid conversation_history JSON format"

**Problem:** The JSON is malformed.

**Solution:** Validate your JSON:
- Use proper quotes (`"` not `'`)
- Escape special characters
- Use a JSON validator tool

### Claude doesn't remember context

**Problem:** Not sending conversation history.

**Solution:** Make sure you're passing `conversation_history` parameter with previous messages.

---

## Examples with cURL

### Complete 3-Turn Conversation

```bash
# Turn 1
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=I'm looking for a gift" \
  -F "stream=false" \
  > response1.json

# Turn 2 (with history)
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=It's for my mom who loves gardening" \
  -F 'conversation_history=[{"role":"user","content":"I'\''m looking for a gift"},{"role":"assistant","content":"I'\''d be happy to help! Could you tell me more about the recipient?"}]' \
  -F "stream=false" \
  > response2.json

# Turn 3 (with full history)
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Budget is around $100" \
  -F 'conversation_history=[{"role":"user","content":"I'\''m looking for a gift"},{"role":"assistant","content":"I'\''d be happy to help! Could you tell me more about the recipient?"},{"role":"user","content":"It'\''s for my mom who loves gardening"},{"role":"assistant","content":"Great! For a gardening enthusiast, you might consider..."}]' \
  -F "stream=false"
```

---

## Summary

| Feature | Details |
|---------|---------|
| **API Type** | Stateless - no automatic memory |
| **To maintain context** | Send `conversation_history` with each request |
| **Format** | JSON array of `{"role": "...", "content": "..."}` objects |
| **Roles** | `"user"` and `"assistant"` only, must alternate |
| **Best practice** | Store messages in frontend, send last 10-20 exchanges |
| **Token limit** | ~200K tokens total (history + new message + response) |

**Remember: The frontend is responsible for managing conversation history!**

---

**Last Updated:** 2025-10-09
