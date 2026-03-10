"""
Utility functions for Rekapo backend.
Provides logging setup, email masking, file upload handling, and safe data serialization.
Used across all modules for consistent logging and file operations.
"""
import logging
import os
from typing import Optional
from fastapi import UploadFile, HTTPException
import uuid
from pathlib import Path

# ============================================================================
# Logging Utilities
# Provides consistent logging configuration across all modules
# ============================================================================

def get_logger(name: str) -> logging.Logger:
	"""Create/get a module logger with sensible defaults.

	- Level from LOG_LEVEL env (default INFO)
	- StreamHandler to stdout with simple format
	- Idempotent: doesn't duplicate handlers if called multiple times
	"""
	logger = logging.getLogger(name)
	if not logger.handlers:
		level_str = os.getenv("LOG_LEVEL", "INFO").upper()
		level = getattr(logging, level_str, logging.INFO)
		logger.setLevel(level)

		handler = logging.StreamHandler()
		handler.setLevel(level)
		formatter = logging.Formatter(
			fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
			datefmt="%Y-%m-%d %H:%M:%S",
		)
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		# Avoid propagating to root if uvicorn config differs
		logger.propagate = False
	return logger


# ============================================================================
# Privacy Utilities
# Mask sensitive data like emails for secure logging
# ============================================================================

def mask_email(email: Optional[str]) -> str:
	"""Mask an email address for logging: j***@domain.com.
	Returns "unknown" if not provided.
	"""
	if not email or "@" not in email:
		return "unknown"
	local, domain = email.split("@", 1)
	if len(local) <= 1:
		masked_local = "*"
	elif len(local) == 2:
		masked_local = local[0] + "*"
	else:
		masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
	return f"{masked_local}@{domain}"


def safe_bool(value: Optional[bool]) -> Optional[bool]:
	"""Pass-through for Optional[bool] to be explicit in logs."""
	return value if value is None else bool(value)


def safe_user_log_dict(user) -> dict:
	"""Build a sanitized dict of user fields safe for logs."""
	return {
		"id": getattr(user, "id", None),
		"google_id": getattr(user, "google_id", None),
		"email": mask_email(getattr(user, "email", None)),
		"name": getattr(user, "name", None),
		"profile_picture_path": getattr(user, "profile_picture_path", None),
		"data_usage_consent": getattr(user, "data_usage_consent", None),
		"is_admin": safe_bool(getattr(user, "is_admin", None)),
		"is_disabled": safe_bool(getattr(user, "is_disabled", None)),
		"created_at": getattr(user, "created_at", None),
	}


# ============================================================================
# File Upload Utilities
# Handles profile photo uploads with validation and storage (R2/local)
# ============================================================================

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB


async def save_profile_photo(file: UploadFile, user_id: int) -> str:
	"""
	Save uploaded profile photo to R2 or local disk.
	
	Args:
		file: The uploaded file
		user_id: The user's ID for organizing files
	
	Returns:
		The URL or relative path to the saved file
	
	Raises:
		HTTPException: If file validation fails
	"""
	logger = get_logger(__name__)
	from config.config import (
		PROFILE_PHOTOS_DIR, PROFILE_PHOTOS_RELATIVE_PATH,
		R2_ENABLED, R2_PROFILE_PHOTOS_PREFIX
	)
	from storage.storage import r2_client
	
	logger.info(f"📸 Starting profile photo upload for user {user_id}")
	logger.info(f"🔧 R2 Storage: {'ENABLED' if R2_ENABLED else 'DISABLED'}")
	
	# Validate file extension
	file_ext = Path(file.filename).suffix.lower()
	logger.info(f"📄 File: {file.filename}, Extension: {file_ext}")
	
	if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
		logger.error(f"❌ Invalid file type: {file_ext}")
		raise HTTPException(
			status_code=400,
			detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
		)
	
	# Validate file size
	contents = await file.read()
	file_size_mb = len(contents) / (1024 * 1024)
	logger.info(f"📏 File size: {file_size_mb:.2f}MB")
	
	if len(contents) > MAX_PROFILE_PHOTO_SIZE:
		logger.error(f"❌ File too large: {file_size_mb:.2f}MB > {MAX_PROFILE_PHOTO_SIZE / (1024*1024):.1f}MB")
		raise HTTPException(
			status_code=400,
			detail=f"File too large. Maximum size: {MAX_PROFILE_PHOTO_SIZE / (1024*1024):.1f}MB"
		)
	
	# Generate unique filename
	unique_filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}{file_ext}"
	logger.info(f"🔑 Generated filename: {unique_filename}")
	
	# Determine content type
	content_type_map = {
		'.jpg': 'image/jpeg',
		'.jpeg': 'image/jpeg',
		'.png': 'image/png',
		'.gif': 'image/gif',
		'.webp': 'image/webp'
	}
	content_type = content_type_map.get(file_ext, 'application/octet-stream')
	logger.info(f"📦 Content type: {content_type}")
	
	if R2_ENABLED:
		# Upload to R2
		r2_key = f"{R2_PROFILE_PHOTOS_PREFIX}/{unique_filename}"
		logger.info(f"☁️  Uploading to R2: {r2_key}")
		
		try:
			file_url = r2_client.upload_file(
				file_content=contents,
				key=r2_key,
				content_type=content_type
			)
			logger.info(f"✅ Successfully uploaded to R2: {file_url}")
			return file_url
		except Exception as e:
			logger.error(f"❌ R2 upload failed: {str(e)}")
			raise
	else:
		# Save to local storage
		logger.info(f"💾 Saving to local storage: {PROFILE_PHOTOS_DIR / unique_filename}")
		PROFILE_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
		file_path = PROFILE_PHOTOS_DIR / unique_filename
		
		with open(file_path, "wb") as f:
			f.write(contents)
		
		logger.info(f"✅ Successfully saved locally")
		# Return relative path (for database storage)
		return f"{PROFILE_PHOTOS_RELATIVE_PATH}/{unique_filename}"


def delete_profile_photo(file_path: str) -> bool:
	"""
	Delete a profile photo file from R2 or local storage.
	
	Args:
		file_path: The path/URL to the file to delete
	
	Returns:
		True if file was deleted, False if it didn't exist
	"""
	from config.config import R2_ENABLED, R2_PROFILE_PHOTOS_PREFIX
	from storage.storage import r2_client
	
	try:
		if R2_ENABLED and (file_path.startswith("r2://") or file_path.startswith("http")):
			# Extract key from R2 URL or URI
			if file_path.startswith("http"):
				# Extract key from public URL (assumes format: https://domain/prefix/filename)
				parts = file_path.split("/")
				key = f"{R2_PROFILE_PHOTOS_PREFIX}/{parts[-1]}"
			else:
				# Handle r2:// URI
				key = file_path
			
			return r2_client.delete_file(key)
		else:
			# Local storage
			path = Path(file_path)
			if path.exists() and path.is_file():
				path.unlink()
				return True
			return False
	except Exception as e:
		logger = get_logger(__name__)
		logger.error(f"Error deleting profile photo {file_path}: {e}")
		return False


