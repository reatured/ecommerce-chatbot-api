# API Error Reference Guide

Complete reference for all error messages and responses from the E-commerce Chatbot API.

---

## Table of Contents
1. [Error Response Format](#error-response-format)
2. [HTTP Status Codes](#http-status-codes)
3. [API Error Messages](#api-error-messages)
4. [Streaming Error Events](#streaming-error-events)
5. [Common Issues & Solutions](#common-issues--solutions)

---

## Error Response Format

### Streaming Mode (`stream: true`)
Errors are sent as SSE events:
```
data: {"type": "error", "message": "Error description here"}
```

### Non-Streaming Mode (`stream: false`)
Errors return HTTP status codes with JSON:
```json
{
  "detail": "Error description here"
}
```

---

## HTTP Status Codes

| Status Code | Meaning | When It Happens |
|-------------|---------|-----------------|
| **200** | Success | Request processed successfully |
| **400** | Bad Request | Invalid input parameters or malformed data |
| **500** | Internal Server Error | Server-side error or API key issues |
| **422** | Validation Error | Missing required fields or wrong data types |

---

## API Error Messages

### Configuration Errors

#### `ANTHROPIC_API_KEY not configured`
**HTTP Status:** 500
**Cause:** The backend `.env` file is missing the `ANTHROPIC_API_KEY` environment variable.
**Solution:**
```bash
# Add to .env file
ANTHROPIC_API_KEY=your_actual_api_key_here
```

---

### Request Validation Errors

#### `Field required` (422 Validation Error)
**HTTP Status:** 422
**Cause:** Missing required parameter (e.g., `message` field).
**Solution:** Ensure all required parameters are included:
```typescript
const formData = new FormData();
formData.append('message', 'Your message here'); // Required!
formData.append('stream', 'true');
```

#### `Input should be a valid string`
**HTTP Status:** 422
**Cause:** Wrong data type for a parameter (e.g., sending number instead of string).
**Solution:** Convert values to correct types:
```typescript
formData.append('max_tokens', '1024'); // String, not number
formData.append('stream', 'true');     // String 'true', not boolean
```

---

### Conversation History Errors

#### `Invalid conversation_history JSON format`
**HTTP Status:** 400
**Cause:** The `conversation_history` parameter contains malformed JSON.
**Solution:** Validate JSON before sending:
```typescript
// ✅ Correct
const history = [
  {"role": "user", "content": "Hello"},
  {"role": "assistant", "content": "Hi there!"}
];
formData.append('conversation_history', JSON.stringify(history));

// ❌ Wrong
formData.append('conversation_history', "not valid json");
```

#### `messages: roles must alternate between 'user' and 'assistant'`
**HTTP Status:** 400 (from Anthropic API)
**Cause:** Conversation history has consecutive messages with the same role.
**Solution:** Ensure alternating roles:
```typescript
// ✅ Correct
const history = [
  {"role": "user", "content": "Hello"},
  {"role": "assistant", "content": "Hi!"},
  {"role": "user", "content": "How are you?"}
];

// ❌ Wrong - two user messages in a row
const history = [
  {"role": "user", "content": "Hello"},
  {"role": "user", "content": "How are you?"}
];
```

---

### Image Upload Errors

#### `messages.0.content.0.image.source.base64: invalid base64 data`
**HTTP Status:** 400 (from Anthropic API)
**Cause:** Image file is corrupted, empty, or not properly encoded.
**Solution:**
- Ensure the uploaded file is a valid image
- Check file is not empty
- Supported formats: JPEG, PNG, GIF, WebP
```typescript
// Verify file exists and is valid
if (file && file.size > 0) {
  formData.append('image', file);
}
```

#### `image.source.media_type: Input should be 'image/jpeg', 'image/png', 'image/gif' or 'image/webp'`
**HTTP Status:** 400 (from Anthropic API)
**Cause:** Unsupported image format.
**Solution:** Use supported image formats only:
```typescript
const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
if (validTypes.includes(file.type)) {
  formData.append('image', file);
} else {
  alert('Please upload a JPEG, PNG, GIF, or WebP image');
}
```

---

### Model & Token Errors

#### `max_tokens: too_long`
**HTTP Status:** 400 (from Anthropic API)
**Cause:** Requested `max_tokens` exceeds model limit.
**Solution:** Reduce max_tokens value:
```typescript
// For claude-3-5-haiku-latest: max is 8192 tokens
formData.append('max_tokens', '4096'); // Safe value
```

#### `prompt is too long: X tokens > Y maximum`
**HTTP Status:** 400 (from Anthropic API)
**Cause:** Combined conversation history + current message exceeds model's context window.
**Solution:**
- Reduce conversation history (keep only recent messages)
- Summarize old messages
- Start a new conversation
```typescript
// Keep only last 10 exchanges (20 messages)
const recentHistory = messages.slice(-20);
formData.append('conversation_history', JSON.stringify(recentHistory));
```

---

### Network & Connection Errors

#### `Failed to fetch` (JavaScript Error)
**Cause:** API is not running or network issue.
**Solution:**
```bash
# Check if API is running
curl http://127.0.0.1:8000/

# Start the API if not running
uvicorn api.index:app --reload --port 8000
```

#### `Network error` / `TypeError: Failed to fetch`
**Cause:**
- API server is down
- Wrong API URL
- CORS issue
- Network connectivity problem

**Solution:**
1. Verify API is running: `curl http://127.0.0.1:8000/`
2. Check API URL in your code matches the running server
3. Ensure CORS is enabled (already configured in the API)
4. Check firewall/network settings

---

### Authentication Errors

#### `authentication_error: invalid x-api-key`
**HTTP Status:** 401 (from Anthropic API)
**Cause:** Invalid or expired Anthropic API key.
**Solution:**
```bash
# Update .env with valid key
ANTHROPIC_API_KEY=sk-ant-api03-...your-valid-key
```

#### `permission_error`
**HTTP Status:** 403 (from Anthropic API)
**Cause:** API key doesn't have permission for requested operation.
**Solution:** Check your Anthropic account permissions and billing status.

---

### Rate Limiting Errors

#### `rate_limit_error: rate limit exceeded`
**HTTP Status:** 429 (from Anthropic API)
**Cause:** Too many requests in a short time period.
**Solution:**
- Implement exponential backoff retry logic
- Add delays between requests
- Upgrade Anthropic API plan if needed

```typescript
// Retry with exponential backoff
async function fetchWithRetry(url: string, options: RequestInit, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.status === 429) {
        // Wait before retrying: 1s, 2s, 4s...
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
        continue;
      }
      return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
    }
  }
  throw new Error('Max retries exceeded');
}
```

---

## Streaming Error Events

During streaming, errors are sent as events:

### `{"type": "error", "message": "..."}`
**When:** Error occurs during streaming response
**Action:** Stop processing stream and show error to user

Example handling:
```typescript
for (const line of lines) {
  if (line.startsWith('data: ')) {
    const data = JSON.parse(line.slice(6));

    if (data.type === 'error') {
      console.error('Stream error:', data.message);
      showErrorToUser(data.message);
      break; // Stop processing stream
    }
  }
}
```

---

## Common Issues & Solutions

### Issue: "Response appears all at once instead of streaming"
**Cause:** `stream` parameter set to `false` or not handling SSE correctly.
**Solution:**
```typescript
// Ensure stream is 'true' as string
formData.append('stream', 'true');

// Use proper SSE reader
const reader = response.body?.getReader();
const decoder = new TextDecoder();
// ... process chunks
```

### Issue: "CORS policy blocked"
**Error:** `Access to fetch at 'http://127.0.0.1:8000' blocked by CORS policy`
**Cause:** API not running or CORS misconfigured.
**Solution:**
- API already has CORS enabled for all origins
- Check if API is actually running: `curl http://127.0.0.1:8000/`
- For production, update CORS origins in `api/index.py`

### Issue: "Empty or incomplete responses"
**Cause:** Not reading stream completely or closing connection early.
**Solution:**
```typescript
// Read until stream is done
while (true) {
  const { done, value } = await reader.read();
  if (done) break; // Important!

  // Process chunk...
}
```

### Issue: "Context doesn't persist across messages"
**Cause:** Not sending conversation history.
**Solution:** See [CONVERSATION_HISTORY.md](CONVERSATION_HISTORY.md) for complete guide.
```typescript
// Send conversation history with each request
formData.append('conversation_history', JSON.stringify(messages));
```

---

## Error Handling Best Practices

### 1. Always Handle Errors in Streaming

```typescript
async function streamChat(message: string) {
  try {
    const response = await fetch(API_URL, { method: 'POST', body: formData });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    // ... process stream

  } catch (error) {
    if (error instanceof TypeError) {
      console.error('Network error - API may be down');
    } else {
      console.error('Error:', error);
    }
    // Show user-friendly message
    showErrorToUser('Failed to send message. Please try again.');
  }
}
```

### 2. Validate Input Before Sending

```typescript
function validateMessage(message: string): boolean {
  if (!message || message.trim().length === 0) {
    showError('Message cannot be empty');
    return false;
  }

  if (message.length > 10000) {
    showError('Message is too long (max 10,000 characters)');
    return false;
  }

  return true;
}
```

### 3. Show User-Friendly Error Messages

```typescript
function getUserFriendlyError(error: string): string {
  if (error.includes('ANTHROPIC_API_KEY')) {
    return 'Service configuration error. Please contact support.';
  }

  if (error.includes('rate_limit')) {
    return 'Too many requests. Please wait a moment and try again.';
  }

  if (error.includes('too long')) {
    return 'Your message is too long. Please shorten it and try again.';
  }

  if (error.includes('network') || error.includes('fetch')) {
    return 'Network error. Please check your connection and try again.';
  }

  return 'An error occurred. Please try again.';
}
```

### 4. Implement Retry Logic for Transient Errors

```typescript
async function sendWithRetry(formData: FormData, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        body: formData
      });

      // Retry on 5xx errors
      if (response.status >= 500 && i < maxRetries - 1) {
        await new Promise(r => setTimeout(r, 1000 * (i + 1)));
        continue;
      }

      return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
}
```

---

## Quick Error Lookup Table

| Error Message | Status | Quick Fix |
|---------------|--------|-----------|
| `ANTHROPIC_API_KEY not configured` | 500 | Add API key to `.env` |
| `Field required` | 422 | Add missing parameter |
| `Invalid conversation_history JSON` | 400 | Fix JSON syntax |
| `roles must alternate` | 400 | Fix message order |
| `invalid base64 data` | 400 | Check image file |
| `Failed to fetch` | - | Start API server |
| `rate_limit_error` | 429 | Wait and retry |
| `authentication_error` | 401 | Check API key |
| `too long` | 400 | Reduce message/history length |

---

## Testing Error Handling

Test your error handling with these scenarios:

```bash
# 1. Test missing required field
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "stream=false"
# Expected: 422 - Field required

# 2. Test invalid JSON
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Hello" \
  -F "conversation_history=not-json" \
  -F "stream=false"
# Expected: 400 - Invalid conversation_history JSON format

# 3. Test with API stopped
# Stop the server, then try request
# Expected: Network error / Connection refused
```

---

## Getting Help

If you encounter an error not listed here:

1. **Check the API logs** - The server console shows detailed error traces
2. **Test in Swagger UI** - http://127.0.0.1:8000/docs
3. **Enable browser DevTools** - Check Network tab for detailed errors
4. **Review the docs**:
   - [README.md](README.md) - Main documentation
   - [CONVERSATION_HISTORY.md](CONVERSATION_HISTORY.md) - Conversation errors
   - [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) - Integration examples

---

**Last Updated:** 2025-10-09
