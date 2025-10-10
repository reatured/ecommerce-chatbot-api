#!/bin/bash

# Test script for metadata detection feature
# This tests that the backend properly separates metadata from message content

API_URL="http://127.0.0.1:8000/api/chat/anthropic/stream"

SYSTEM_PROMPT='You are a friendly AI shopping assistant. Your role is to engage in general conversation and understand the customer'\''s needs.

IMPORTANT: You must respond with a JSON object in the following format:
{
  "stage": 0,
  "message": "your response message here",
  "summary": "key information in minimal words"
}

Stage 0 Guidelines:
- Welcome users warmly and be conversational
- Ask questions to understand what they'\''re looking for
- Engage in general chat if they want to talk about other topics
- When you identify a clear product need, suggest moving to product search
- Be helpful, friendly, and patient

Summary Guidelines for Stage 0:
- Capture user'\''s initial needs, interests, or shopping intent
- Keep it extremely brief (5-10 words max)
- Update with new information from each message
- Example: "User looking for sports shoes" or "General greeting, no specific need yet"

Always include "stage": 0 and "summary" in your JSON response. If you determine the conversation should move to product discovery, you can suggest it in your message, but keep stage at 0 until the user explicitly expresses interest in finding products.'

echo "==================================="
echo "Testing Metadata Detection Feature"
echo "==================================="
echo ""
echo "Sending request to: $API_URL"
echo "User message: 'Hello! I'm looking for summer clothes.'"
echo ""
echo "Expected behavior:"
echo "  - Metadata chunks: {\"type\": \"metadata\", \"delta\": ...}"
echo "  - Content chunks:  {\"type\": \"content\", \"delta\": ...}"
echo ""
echo "-----------------------------------"
echo "Streaming response:"
echo "-----------------------------------"

curl -N -X POST "$API_URL" \
  -F "message=Hello! I'm looking for summer clothes." \
  -F "system_prompt=$SYSTEM_PROMPT" \
  -F "stream=true" \
  2>/dev/null

echo ""
echo "-----------------------------------"
echo "Test complete!"
echo ""
echo "To verify:"
echo "1. Look for 'type': 'metadata' in early chunks (stage, summary fields)"
echo "2. Look for 'type': 'content' after the 'message': field starts"
echo "3. Frontend should ignore 'metadata' type and only display 'content' type"
