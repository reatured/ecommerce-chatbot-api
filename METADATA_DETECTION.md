# Metadata Detection Feature

This document explains the metadata detection feature that automatically separates JSON structure from message content during streaming.

## Overview

When using structured JSON responses (with `stage`, `summary`, and `message` fields), the backend now intelligently detects when it reaches the `"message"` field and switches event types.

### Problem Solved

**Before:**
```javascript
// Frontend sees raw JSON streaming in chat:
{"stage": 0, "summary": "Looking for clothes", "message": "Hello! I'd be happy to help..."}
```

**After:**
```javascript
// Frontend sees only the message:
Hello! I'd be happy to help...

// Stage and summary are available but not displayed
```

---

## How It Works

### Backend Detection Logic

1. **Buffer accumulation**: Backend buffers streamed text to detect patterns
2. **Pattern detection**: Looks for `"message":` in the buffer
3. **Type switching**:
   - Before `"message":` → Emits `type: "metadata"`
   - After `"message":` → Emits `type: "content"`
4. **Frontend filtering**: Frontend ignores `metadata` type, displays only `content` type

### Stream Flow Example

**Input (from Claude):**
```json
{
  "stage": 0,
  "summary": "Looking for summer clothes",
  "message": "Hello! I'd be happy to help you find summer clothes..."
}
```

**Output (streaming events):**
```
data: {"type": "metadata", "delta": "{", "index": 0}
data: {"type": "metadata", "delta": "\n  \"stage\": 0,", "index": 0}
data: {"type": "metadata", "delta": "\n  \"summary\": \"Looking for summer clothes\",", "index": 0}
data: {"type": "metadata", "delta": "\n  \"message\": \"", "index": 0}
                                    ↑ Detection happens here
data: {"type": "content", "delta": "Hello!", "index": 0}
data: {"type": "content", "delta": " I'd", "index": 0}
data: {"type": "content", "delta": " be happy", "index": 0}
data: {"type": "content", "delta": " to help", "index": 0}
data: {"type": "content", "delta": " you", "index": 0}
data: {"type": "content", "delta": " find", "index": 0}
data: {"type": "content", "delta": " summer", "index": 0}
data: {"type": "content", "delta": " clothes", "index": 0}
data: {"type": "content", "delta": "...", "index": 0}
data: {"type": "content", "delta": "\"", "index": 0}
data: {"type": "metadata", "delta": "\n}", "index": 0}
data: {"type": "finish", "finish_reason": "end_turn"}
data: {"type": "done"}
```

---

## Frontend Integration

### Basic Implementation

```javascript
for (const line of lines) {
  if (line.startsWith('data: ')) {
    const data = JSON.parse(line.slice(6));

    if (data.type === 'metadata') {
      // Ignore - don't display in chat
      continue;

    } else if (data.type === 'content') {
      // Accumulate and display message
      fullResponse += data.delta;
      setCurrentResponse(fullResponse);

    } else if (data.type === 'done') {
      // Save message to history
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: fullResponse  // Clean message only!
      }]);
      setCurrentResponse('');
    }
  }
}
```

### Advanced Implementation (Extract Metadata)

```javascript
let fullResponse = '';
let fullJSON = '';

for (const line of lines) {
  if (line.startsWith('data: ')) {
    const data = JSON.parse(line.slice(6));

    if (data.type === 'metadata') {
      // Accumulate for later parsing
      fullJSON += data.delta;

    } else if (data.type === 'content') {
      // Display in chat
      fullResponse += data.delta;
      setCurrentResponse(fullResponse);

      // Also add to JSON buffer
      fullJSON += data.delta;

    } else if (data.type === 'done') {
      // Parse complete JSON
      try {
        const parsed = JSON.parse(fullJSON);

        // Extract metadata (update state silently)
        setCurrentStage(parsed.stage);
        setConversationSummary(parsed.summary);

        // Save clean message
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: parsed.message
        }]);

      } catch (e) {
        console.warn('Could not parse metadata:', e);
        // Fallback: use accumulated response
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: fullResponse
        }]);
      }

      setCurrentResponse('');
      fullJSON = '';
    }
  }
}
```

---

## System Prompt Requirements

For this feature to work properly, your system prompt must instruct Claude to return JSON with a `"message"` field:

### ✅ Correct Format

```javascript
const systemPrompt = `
IMPORTANT: You must respond with a JSON object in the following format:
{
  "stage": 0,
  "message": "your response message here",
  "summary": "brief summary"
}
`;
```

### ❌ Won't Work

```javascript
// Missing "message" field
{
  "stage": 0,
  "text": "your response"  // Wrong field name!
}

// No JSON structure
"Just plain text response"
```

---

## Event Types Reference

| Type | Description | Frontend Action |
|------|-------------|-----------------|
| `metadata` | JSON structure fields (stage, summary, braces, commas) | Ignore or buffer for parsing |
| `content` | The actual message text inside `"message": "..."` | Display in chat UI |
| `finish` | Stream completion with finish reason | Optional: Log or handle |
| `done` | Final completion marker | Parse metadata, save message |
| `error` | Error occurred | Display error message |

---

## Testing

### Start Your Server

```bash
uvicorn api.index:app --reload --port 8000
```

### Run Test Script

```bash
./test_metadata_detection.sh
```

### Manual Test with curl

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Hello! I'm looking for summer clothes." \
  -F 'system_prompt=IMPORTANT: Respond with JSON: {"stage": 0, "message": "your response", "summary": "brief summary"}' \
  -F "stream=true"
```

### Verify Output

Look for the type switching:
```
data: {"type": "metadata", "delta": "{"}          ← Before "message":
data: {"type": "metadata", "delta": "\"stage\":"}
data: {"type": "metadata", "delta": " 0,"}
data: {"type": "metadata", "delta": "\"message\":\""}
data: {"type": "content", "delta": "Hello!"}      ← After "message":
data: {"type": "content", "delta": " I'd be"}
```

---

## Benefits

✅ **Cleaner Chat UI** - No JSON structure visible to users
✅ **Real-time Streaming** - Message appears character-by-character
✅ **Metadata Extraction** - Still get stage/summary data
✅ **Backward Compatible** - Non-JSON responses still work
✅ **Simple Frontend** - Just filter by event type

---

## Edge Cases

### 1. Non-JSON Responses

If Claude doesn't return JSON (e.g., system prompt ignored):
- All chunks will be `type: "content"` (no `"message"` field detected)
- Frontend displays normally
- No breaking changes

### 2. Multiple "message" Fields

The detection triggers on the **first** occurrence of `"message":` in the buffer.

### 3. Malformed JSON

If JSON is malformed:
- Detection still works based on pattern matching
- Frontend JSON parsing might fail (use try-catch)
- Fallback: display accumulated `fullResponse`

---

## Troubleshooting

### Issue: Still seeing JSON in chat

**Check:**
1. Is frontend filtering `type: "metadata"`?
2. Is system prompt instructing JSON format correctly?
3. Is the `"message"` field present in the JSON?

**Solution:**
```javascript
// Make sure you're ignoring metadata
if (data.type === 'metadata') {
  continue;  // Don't add to chat!
}
```

### Issue: Message not streaming

**Check:**
1. Is `"message":` properly detected in buffer?
2. Is there spacing issues like `"message" : "` (extra space)?

**Solution:**
The detection handles both `':"'` and `': "'` patterns.

### Issue: Metadata not parsing

**Check:**
1. Are you accumulating both metadata and content deltas?
2. Is JSON.parse being called on the complete buffer?

**Solution:**
```javascript
// Accumulate BOTH types
fullJSON += data.delta;  // For both metadata and content
```

---

## Migration Guide

### Before (Old Implementation)

```javascript
// Old: Everything is "content"
if (data.type === 'content') {
  fullResponse += data.delta;
}

// Frontend had to parse JSON from fullResponse
const parsed = JSON.parse(fullResponse);
setMessages([...messages, { content: parsed.message }]);
```

### After (New Implementation)

```javascript
// New: Filter by type
if (data.type === 'metadata') {
  fullJSON += data.delta;  // For parsing
} else if (data.type === 'content') {
  fullResponse += data.delta;  // For display
  setCurrentResponse(fullResponse);  // Real-time update!
}

// On done: parse JSON for metadata
const parsed = JSON.parse(fullJSON);
setStage(parsed.stage);
setMessages([...messages, { content: parsed.message }]);
```

---

## API Changes

### No Breaking Changes

- Existing implementations continue to work
- `type: "content"` is still emitted (for message field)
- Added: `type: "metadata"` for JSON structure
- Backward compatible with non-JSON responses

### New Response Format

**Before:**
```
All chunks: type: "content"
```

**After:**
```
JSON structure: type: "metadata"
Message content: type: "content"
```

---

## Complete Example

See `STRUCTURED_OUTPUT_GUIDE.md` for complete frontend implementation examples.

For questions or issues, refer to the main README.md documentation.
