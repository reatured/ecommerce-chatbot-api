#!/bin/bash

# Test script to simulate the frontend image upload workflow

echo "Test 1: Simple message with empty conversation history"
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Test message" \
  -F 'conversation_history=[]' \
  -F "stream=false"
echo -e "\n"

echo "Test 2: Message with conversation history containing empty content"
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=What do you see?" \
  -F 'conversation_history=[{"role":"user","content":""},{"role":"assistant","content":"I can help!"}]' \
  -F "stream=false"
echo -e "\n"

echo "Test 3: Message with valid conversation history"
curl -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -F "message=Tell me more" \
  -F 'conversation_history=[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hi there!"}]' \
  -F "stream=false"
echo -e "\n"
