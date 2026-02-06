from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from routes.whisper import router as transcribe_router
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.sessions import router as sessions_router
from admin.admin_auth import router as admin_auth_router
from admin.admin_users import router as admin_users_router
from admin.admin_statistics import router as admin_statistics_router
from admin.admin_sessions import router as admin_sessions_router
from admin.admin_user_analytics import router as admin_user_analytics_router
from db.db import init_db
from config.config import PROFILE_PHOTOS_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    print("Initializing database...")
    init_db()
    print("Database initialized successfully")
    
    # Ensure upload directories exist
    PROFILE_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Upload directory ensured: {PROFILE_PHOTOS_DIR}")
    
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
app.include_router(users_router, prefix="/api", tags=["Users"])
app.include_router(sessions_router, prefix="/api", tags=["Sessions"])
app.include_router(admin_auth_router, tags=["Admin Auth"])
app.include_router(admin_users_router, tags=["Admin Users"])
app.include_router(admin_statistics_router, tags=["Admin Statistics"])
app.include_router(admin_sessions_router, tags=["Admin Sessions"])
app.include_router(admin_user_analytics_router, tags=["Admin User Analytics"])

# Mount static files for serving uploaded profile photos
from config.config import UPLOADS_DIR
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

@app.get("/")
async def root():
    return {
        "message": "Rekapo Meeting Summarizer API",
        "description": "Near real-time meeting transcription with Taglish support",
        "websocket_endpoint": "/api/ws/transcribe",
        "docs": "/docs",
        "features": [
            "Real-time transcription with faster-whisper",
            "Automatic translation with NLLB-200 (200+ languages)",
            "Smart summarization every 10 chunks",
            "WebSocket support for mobile voice chunks",
            "VAD-based audio segmentation",
            "Taglish support (Tagalog + English)",
            "Meeting session management"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rekapo-api"}

