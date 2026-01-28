import os
from pathlib import Path

# Get the project root directory (parent of config directory)
PROJECT_ROOT = Path(__file__).parent.parent

# Upload directories (relative to project root)
UPLOADS_DIR = PROJECT_ROOT / "uploads"
PROFILE_PHOTOS_DIR = UPLOADS_DIR / "profile_photos"

# Relative paths for storage in database
PROFILE_PHOTOS_RELATIVE_PATH = "uploads/profile_photos"

# Cloudflare R2 Storage Configuration
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

# Whisper Model Configuration
WHISPER_MODEL_PATH = os.getenv("WHISPER_MODEL_PATH", "ai_models/whisper/models/checkpoint-3200")
