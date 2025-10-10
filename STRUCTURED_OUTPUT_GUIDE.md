# Structured Output Guide

This guide shows how to get structured JSON responses from the chatbot API for multi-stage conversations or product search extraction.

## Overview

The API now supports a `system_prompt` parameter (in addition to the existing `system` parameter) that allows you to instruct Claude to return structured JSON responses.

## How It Works

1. **Frontend sends a system prompt** that instructs Claude to respond in JSON format
2. **Backend passes it to Anthropic API** via the `system` parameter
3. **Claude returns structured JSON** according to your instructions
4. **Frontend parses the JSON** from the streamed or complete response

## API Parameters

The endpoint `/api/chat/anthropic/stream` now accepts:

- `system_prompt` (string, optional) - System prompt for structured output (takes precedence)
- `system` (string, optional) - Alternative parameter name (for backward compatibility)

## Example 1: Multi-Stage Conversation

### System Prompt (Stage 0 - General Conversation)

```javascript
const systemPrompt = `You are a friendly AI shopping assistant. Your role is to engage in general conversation and understand the customer's needs.

IMPORTANT: You must respond with a JSON object in the following format:
{
  "stage": 0,
  "message": "your response message here"
}

Stage 0 Guidelines:
- Welcome users warmly and be conversational
- Ask questions to understand what they're looking for
- When you identify a clear product need, suggest moving to product search
- Be helpful, friendly, and patient

Always include "stage": 0 in your JSON response.`;
```

### Frontend Request

```javascript
const formData = new FormData();
formData.append('message', 'Hello');
formData.append('system_prompt', systemPrompt);
formData.append('stream', 'true');

const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
  method: 'POST',
  body: formData,
});
```

### Expected Response (Streaming)

```
data: {"type": "content", "delta": "{"}
data: {"type": "content", "delta": "\"stage"}
data: {"type": "content", "delta": "\": 0,"}
data: {"type": "content", "delta": " \"message\""}
data: {"type": "content", "delta": ": \"Hello!"}
data: {"type": "content", "delta": " I'm your"}
data: {"type": "content", "delta": " AI shopping"}
data: {"type": "content", "delta": " assistant...\""}
data: {"type": "content", "delta": "}"}
data: {"type": "done"}
```

### Frontend Parsing

```javascript
let fullResponse = '';

// As chunks arrive during streaming
for (const line of lines) {
  if (line.startsWith('data: ')) {
    const data = JSON.parse(line.slice(6));

    if (data.type === 'content') {
      fullResponse += data.delta;
    } else if (data.type === 'done') {
      // Parse the complete JSON response
      try {
        const parsed = JSON.parse(fullResponse);
        console.log('Stage:', parsed.stage);
        console.log('Message:', parsed.message);

        // Update UI based on stage
        setCurrentStage(parsed.stage);
        setAssistantMessage(parsed.message);
      } catch (e) {
        console.error('Failed to parse JSON:', e);
      }
    }
  }
}
```

## Example 2: Product Search Extraction

### System Prompt (Search Tags)

```javascript
const systemPrompt = `You are a helpful e-commerce shopping assistant.

When users describe products they want, respond with JSON in this format:
{
  "search_params": {
    "category": "t-shirt/dress/shoes/etc or null",
    "color": "red/blue/etc or null",
    "size": "S/M/L/XL or null",
    "price_range": "under_25/25_50/50_100/over_100 or null",
    "style": "casual/formal/etc or null"
  },
  "message": "Your conversational response here"
}

Extract search parameters from the user's request and provide a friendly response.`;
```

### User Query

```
"I'm looking for a blue t-shirt under $30"
```

### Expected JSON Response

```json
{
  "search_params": {
    "category": "t-shirt",
    "color": "blue",
    "size": null,
    "price_range": "under_25",
    "style": "casual"
  },
  "message": "I'd be happy to help you find a blue t-shirt under $30! What size are you looking for?"
}
```

### Frontend Usage

```javascript
// Parse the complete response
const parsed = JSON.parse(fullResponse);

// Use search params to query product database
if (parsed.search_params) {
  const products = await searchProducts(parsed.search_params);
  displayProducts(products);
}

// Display conversational message
displayAssistantMessage(parsed.message);
```

## Best Practices

### 1. Clear JSON Instructions

Always be explicit in your system prompt:
- Specify exact JSON structure
- Include example format
- Use "IMPORTANT" or "REQUIRED" keywords

### 2. Handle Parsing Errors

```javascript
try {
  const parsed = JSON.parse(fullResponse);
  // Use parsed data
} catch (e) {
  console.error('JSON parsing failed:', e);
  // Fall back to treating as plain text
  displayAssistantMessage(fullResponse);
}
```

### 3. Validate Response Structure

```javascript
const parsed = JSON.parse(fullResponse);

// Validate required fields exist
if (!parsed.stage || !parsed.message) {
  console.warn('Missing required fields in response');
}

// Type checking
if (typeof parsed.stage !== 'number') {
  console.warn('Invalid stage type');
}
```

### 4. Handle Edge Cases

- **Empty responses**: Check if `fullResponse` is not empty before parsing
- **Partial JSON**: In streaming mode, ensure the full JSON is received before parsing
- **Malformed JSON**: Have fallback to plain text display
- **Missing fields**: Provide defaults for optional fields

## Complete Example: Multi-Stage Chat

```javascript
import { useState } from 'react';

const STAGE_PROMPTS = {
  0: `You are a friendly AI shopping assistant...
      Respond with: {"stage": 0, "message": "..."}`,
  1: `You are helping users narrow down products...
      Respond with: {"stage": 1, "message": "..."}`,
  2: `You are providing detailed product information...
      Respond with: {"stage": 2, "message": "..."}`
};

function ChatBot() {
  const [messages, setMessages] = useState([]);
  const [currentStage, setCurrentStage] = useState(0);
  const [currentResponse, setCurrentResponse] = useState('');

  const sendMessage = async (userMessage) => {
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    // Prepare request
    const formData = new FormData();
    formData.append('message', userMessage);
    formData.append('system_prompt', STAGE_PROMPTS[currentStage]);
    formData.append('stream', 'true');

    // Include conversation history
    const history = messages.filter(msg => msg.content?.trim());
    if (history.length > 0) {
      formData.append('conversation_history', JSON.stringify(history));
    }

    // Send request
    const response = await fetch('http://127.0.0.1:8000/api/chat/anthropic/stream', {
      method: 'POST',
      body: formData,
    });

    // Handle streaming response
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';

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
            // Parse final JSON
            try {
              const parsed = JSON.parse(fullResponse);

              // Update stage if changed
              if (parsed.stage !== currentStage) {
                setCurrentStage(parsed.stage);
              }

              // Add assistant message
              setMessages(prev => [...prev, {
                role: 'assistant',
                content: parsed.message
              }]);

              setCurrentResponse('');
            } catch (e) {
              console.error('Failed to parse JSON:', e);
              // Fallback: treat as plain text
              setMessages(prev => [...prev, {
                role: 'assistant',
                content: fullResponse
              }]);
            }
          }
        }
      }
    }
  };

  return (
    <div>
      <div>Current Stage: {currentStage}</div>
      {/* Render messages */}
      {/* Input field */}
    </div>
  );
}
```

## Testing

### Test with curl

```bash
# Test with system_prompt parameter
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Hello" \
  -F 'system_prompt=You must respond with JSON: {"stage": 0, "message": "your response"}' \
  -F "stream=true"
```

### Expected Output

```
data: {"type": "content", "delta": "{", "index": 0}
data: {"type": "content", "delta": "\"stage\"", "index": 0}
data: {"type": "content", "delta": ": 0,", "index": 0}
...
data: {"type": "finish", "finish_reason": "end_turn"}
data: {"type": "done"}
```

## Troubleshooting

### Issue: Getting plain text instead of JSON

**Solution**: Make your system prompt more explicit:
- Add "REQUIRED:" or "IMPORTANT:" prefix
- Include example JSON in the prompt
- Use strong language: "You MUST respond with valid JSON"

### Issue: JSON parsing fails

**Causes**:
- Partial JSON in streaming mode (wait for `type: "done"`)
- Claude added extra text before/after JSON
- Malformed JSON

**Solutions**:
- Wrap parsing in try-catch
- Extract JSON using regex: `/\{[\s\S]*\}/`
- Improve system prompt to ensure clean JSON output

### Issue: Inconsistent stage values

**Solution**: Be explicit about when stages should change:
- "Keep stage at 0 unless user explicitly asks for products"
- "Only move to stage 2 when discussing a specific product"

## API Reference

### Endpoint

`POST /api/chat/anthropic/stream`

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | User's message |
| `system_prompt` | string | No | System prompt for structured output (takes precedence over `system`) |
| `system` | string | No | Alternative parameter name |
| `conversation_history` | string | No | JSON array of previous messages |
| `stream` | boolean | No | Enable streaming (default: true) |
| `model` | string | No | Claude model (default: claude-3-5-haiku-latest) |
| `max_tokens` | integer | No | Max response tokens (default: 1024) |

### Response Format

Same as existing API:
- Streaming: Server-Sent Events with `type: "content"`, `type: "done"`
- Non-streaming: JSON with `type: "complete"`

The content will be structured JSON if your system prompt instructs it correctly.

---

**Note**: This feature requires no backend changes beyond accepting the `system_prompt` parameter. All structured output formatting is handled by Claude through the system prompt instructions.
