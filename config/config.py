""" 
Configuration file for Rekapo backend.
Centralizes all environment variables, file paths, and feature flags.
Used by storage, AI models, and main application.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the project root directory (parent of config directory)
PROJECT_ROOT = Path(__file__).parent.parent

# Upload directories (relative to project root)
# Used when R2 storage is disabled - fallback to local filesystem
UPLOADS_DIR = PROJECT_ROOT / "uploads"
PROFILE_PHOTOS_DIR = UPLOADS_DIR / "profile_photos"

# Relative paths for storage in database
PROFILE_PHOTOS_RELATIVE_PATH = "uploads/profile_photos"

# ============================================================================
# Cloudflare R2 Storage Configuration
# R2 is Cloudflare's S3-compatible object storage service
# Enable in production for scalable file storage
# ============================================================================
R2_ENABLED = os.getenv("R2_ENABLED", "false").lower() == "true"
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "rekapo")
R2_REGION = os.getenv("R2_REGION", "auto")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")

# R2 storage paths (prefixes for organizing files in bucket)
R2_PROFILE_PHOTOS_PREFIX = "profile_photos"
R2_AUDIO_PREFIX = "audios"
R2_LOGS_PREFIX = "logs"

# ============================================================================
# AI Model Paths
# Local paths to fine-tuned models (used when USE_MODAL=false)
# ============================================================================
WHISPER_MODEL_PATH = os.getenv("WHISPER_MODEL_PATH", "ai_models/whisper/models/whisper-small-fine-tuned-ct2")
TRANSLATOR_MODEL_PATH = os.getenv("TRANSLATOR_MODEL_PATH", "ai_models/translator/nllb-1.3b-ct2")
SUMMARIZER_MODEL_PATH = os.getenv("SUMMARIZER_MODEL_PATH", "Qwen/Qwen2.5-1.5B-Instruct")

# ============================================================================
# AI Inference Configuration
# Toggle between serverless Modal deployment and local model inference
# Modal = serverless GPU functions (recommended for production)
# Local = on-premise inference (development/testing)
# ============================================================================
USE_MODAL = os.getenv("USE_MODAL", "true").lower() == "true"

# ============================================================================
# Translation Configuration
# Taglish preprocessing improves translation quality for code-switched text
# Applies phonetic correction, dictionary lookup, and context analysis
# ============================================================================
ENABLE_TAGLISH_PREPROCESSING = os.getenv("ENABLE_TAGLISH_PREPROCESSING", "true").lower() == "true"
