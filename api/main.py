"""
E-commerce Chatbot API
Main FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers from basic endpoints
from api.basic.init import router as init_router
from api.basic.chat import router as chat_router
from api.basic.metadata import router as metadata_router

# Create FastAPI app
app = FastAPI(
    title="E-commerce Chatbot API",
    description="Basic API for chat and product metadata search",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(init_router, tags=["Health"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(metadata_router, tags=["Metadata"])


# Startup event
@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("E-commerce Chatbot API Starting...")
    print("=" * 50)
    print("📍 Health Check: http://localhost:8000/")
    print("💬 Chat Endpoint: http://localhost:8000/api/chat")
    print("🔍 Metadata Endpoint: http://localhost:8000/api/metadata")
    print("📚 API Docs: http://localhost:8000/docs")
    print("=" * 50)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print("E-commerce Chatbot API shutting down...")
