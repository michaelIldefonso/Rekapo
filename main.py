from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routes.whisper import router as transcribe_router
from routes.auth import router as auth_router
from db.db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    print("Initializing database...")
    init_db()
    print("Database initialized successfully")
    yield
    # Shutdown: cleanup if needed
    print("Shutting down...")

app = FastAPI(
    title="Rekapo - Meeting Summarizer API",
    description="Mobile-based near real-time meeting summarizer with Taglish support",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for mobile app support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(transcribe_router, prefix="/api", tags=["Transcription"])
app.include_router(auth_router, prefix="/api", tags=["Auth"])

@app.get("/")
async def root():
    return {
        "message": "Rekapo Meeting Summarizer API",
        "description": "Near real-time meeting transcription with Taglish support",
        "websocket_endpoint": "/api/ws/transcribe",
        "docs": "/docs",
        "features": [
            "Real-time transcription with faster-whisper",
            "WebSocket support for mobile voice chunks",
            "VAD-based audio segmentation",
            "Taglish support (Tagalog + English)",
            "Meeting session management"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rekapo-api"}
