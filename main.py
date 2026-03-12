"""
Rekapo Backend - Meeting Summarizer API

FastAPI application providing:
- Real-time audio transcription via WebSocket
- Google OAuth authentication
- Session and recording management
- Admin dashboard with analytics
- Mobile and web client support

Startup lifecycle:
1. Initialize database (SQLAlchemy)
2. Create upload directories
3. Start background scheduler (statistics, cleanup)
4. Mount routes and static files
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from routes.whisper import router as transcribe_router
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.sessions import router as sessions_router
from routes.logs import router as logs_router
from admin.admin_auth import router as admin_auth_router
from admin.admin_users import router as admin_users_router
from admin.admin_statistics import router as admin_statistics_router
from admin.admin_sessions import router as admin_sessions_router
from admin.admin_user_analytics import router as admin_user_analytics_router
from admin.admin_logs import router as admin_logs_router
from db.db import init_db
from config.config import (
    PROFILE_PHOTOS_DIR,
    CORS_ALLOWED_ORIGINS,
    CORS_ALLOWED_ORIGIN_REGEX,
    CORS_ALLOW_CREDENTIALS,
)
from utils.scheduler import start_scheduler, stop_scheduler

# ============================================================================
# Application Lifespan Management
# Handles startup initialization and graceful shutdown
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    import logging
    logger = logging.getLogger("rekapo.startup")
    logger.info("="*70)
    logger.info("🚀 Starting Rekapo API Server")
    logger.info("="*70)
    logger.info("Initializing database...")
    init_db()
    logger.info("✅ Database initialized successfully")
    
    # Ensure upload directories exist
    PROFILE_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Upload directory ensured: {PROFILE_PHOTOS_DIR}")
    
    # Start background scheduler for automated tasks
    start_scheduler()
    
    logger.info("="*70)
    
    yield
    # Shutdown: cleanup if needed
    logger.info("="*70)
    logger.info("🛑 Shutting down Rekapo API Server")
    stop_scheduler()
    logger.info("="*70)

# ============================================================================
# FastAPI Application Instance
# Registers all routes, middleware, and static file serving
# ============================================================================

app = FastAPI(
    title="Rekapo - Meeting Summarizer API",
    description="Mobile-based near real-time meeting summarizer with Taglish support",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# CORS Middleware
# Allows mobile app and admin web interface to access API
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_origin_regex=CORS_ALLOWED_ORIGIN_REGEX,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Route Registration
# Mobile endpoints: /api/* (auth, users, sessions, transcription)
# Admin endpoints: /admin/* (auth, users, sessions, logs, analytics)
# ============================================================================

app.include_router(transcribe_router, prefix="/api", tags=["Transcription"])
app.include_router(auth_router, prefix="/api", tags=["Auth"])
app.include_router(users_router, prefix="/api", tags=["Users"])
app.include_router(sessions_router, prefix="/api", tags=["Sessions"])
app.include_router(logs_router, prefix="/api", tags=["Logs"])
app.include_router(admin_auth_router, tags=["Admin Auth"])
app.include_router(admin_users_router, tags=["Admin Users"])
app.include_router(admin_statistics_router, tags=["Admin Statistics"])
app.include_router(admin_sessions_router, tags=["Admin Sessions"])
app.include_router(admin_user_analytics_router, tags=["Admin User Analytics"])
app.include_router(admin_logs_router, tags=["Admin Logs"])

# ============================================================================
# Static File Serving
# Serves user-uploaded profile photos when R2 storage is disabled
# Production should use R2 for better scalability
# ============================================================================
from config.config import UPLOADS_DIR
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# ============================================================================
# Health Check and Info Endpoints
# Provides API information and service health status
# ============================================================================

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

