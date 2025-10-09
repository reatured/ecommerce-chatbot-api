# E-commerce Chatbot API (Local Deployment)

This repository runs a small FastAPI app that exposes two streaming endpoints:

- `POST /api/chat/perplexity/stream` — Streams Perplexity search results via Server-Sent Events (SSE).
- `POST /api/chat/anthropic/stream` — Streams Anthropic chat responses via SSE (supports optional base64 images).

This README explains how to run the project locally on macOS (zsh).

## Requirements

- Python 3.11+ (recommended)
- zsh (default on macOS)

## Quick start (recommended)

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file from the example and set API keys:

```bash
cp .env.example .env
# Edit .env and set your keys
open .env
```

Required environment variables:

- `ANTHROPIC_API_KEY` — Your Anthropic API key
- `PERPLEXITY_API_KEY` — Your Perplexity API key

4. Run the app with Uvicorn (development):

```bash
uvicorn api.index:app --reload --port 8000
```

This serves the API at `http://127.0.0.1:8000`.

## Test the endpoints

Example request for Perplexity search (curl with SSE):

```bash
curl -N -H "Content-Type: application/json" -X POST http://127.0.0.1:8000/api/chat/perplexity/stream \
  -d '{"query": "best wireless headphones 2025", "max_results": 3 }'
```

Example request for Anthropic chat (simple text):

```bash
curl -N -H "Content-Type: application/json" -X POST http://127.0.0.1:8000/api/chat/anthropic/stream \
  -d '{"message": "Hello, please recommend 3 gift ideas for a 30-year-old who likes coffee."}'
```

Notes:
- The API streams Server-Sent Events (SSE). Using `curl -N` keeps the connection open to receive events incrementally.
- If you plan to use the Perplexity or Anthropic SDKs, ensure you have working API keys and the package versions in `requirements.txt` match your environment.

## Troubleshooting

- If you see import errors, confirm you're using the virtualenv and installed packages correctly.
- If you get authentication errors, verify the env variables in `.env` and restart the server.

## Security

- Do not commit your `.env` file with real API keys.

## Next steps

- Add tests for the streaming endpoints.
- Add example frontend to consume SSEs.
# ecommerce-chatbot