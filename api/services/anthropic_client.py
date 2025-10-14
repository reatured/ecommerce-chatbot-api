"""
Anthropic Claude Client
Non-streaming chat with JSON mode response
"""

import os
import anthropic
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def chat_completion(
    message: str,
    conversation_history: Optional[List[Dict]] = None,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
    system_prompt: Optional[str] = None
) -> Dict:
    """
    Send a chat message to Claude and get JSON response

    Args:
        message: User's message
        conversation_history: Optional list of previous messages
        model: Claude model to use
        max_tokens: Maximum tokens in response
        system_prompt: Optional system prompt (usually from frontend)

    Returns:
        Dict with response text and metadata
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured in environment variables")

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Build messages array
        messages = []

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add current user message
        messages.append({
            "role": "user",
            "content": message
        })

        # Prepare API call parameters
        params = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }

        # Add system prompt if provided
        if system_prompt:
            params["system"] = system_prompt

        # Make API call
        response = client.messages.create(**params)

        # Extract text from response
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text += block.text

        return {
            "response": response_text,
            "model": response.model,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }

    except anthropic.APIError as e:
        raise Exception(f"Anthropic API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error in chat completion: {str(e)}")
