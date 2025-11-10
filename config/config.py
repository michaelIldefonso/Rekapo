import os
from pathlib import Path

# Get the project root directory (parent of config directory)
PROJECT_ROOT = Path(__file__).parent.parent

# Upload directories (relative to project root)
UPLOADS_DIR = PROJECT_ROOT / "uploads"
PROFILE_PHOTOS_DIR = UPLOADS_DIR / "profile_photos"

# Relative paths for storage in database
PROFILE_PHOTOS_RELATIVE_PATH = "uploads/profile_photos"
