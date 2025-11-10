import logging
import os
from typing import Optional
from fastapi import UploadFile, HTTPException
import uuid
from pathlib import Path


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


# File upload utilities
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB


async def save_profile_photo(file: UploadFile, user_id: int) -> str:
	"""
	Save uploaded profile photo to disk.
	
	Args:
		file: The uploaded file
		user_id: The user's ID for organizing files
	
	Returns:
		The relative path to the saved file
	
	Raises:
		HTTPException: If file validation fails
	"""
	from config.config import PROFILE_PHOTOS_DIR, PROFILE_PHOTOS_RELATIVE_PATH
	
	# Validate file extension
	file_ext = Path(file.filename).suffix.lower()
	if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
		raise HTTPException(
			status_code=400,
			detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
		)
	
	# Validate file size
	contents = await file.read()
	if len(contents) > MAX_PROFILE_PHOTO_SIZE:
		raise HTTPException(
			status_code=400,
			detail=f"File too large. Maximum size: {MAX_PROFILE_PHOTO_SIZE / (1024*1024):.1f}MB"
		)
	
	# Create upload directory if it doesn't exist
	PROFILE_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
	
	# Generate unique filename
	unique_filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}{file_ext}"
	file_path = PROFILE_PHOTOS_DIR / unique_filename
	
	# Save file
	with open(file_path, "wb") as f:
		f.write(contents)
	
	# Return relative path (for database storage)
	return f"{PROFILE_PHOTOS_RELATIVE_PATH}/{unique_filename}"


def delete_profile_photo(file_path: str) -> bool:
	"""
	Delete a profile photo file if it exists.
	
	Args:
		file_path: The path to the file to delete
	
	Returns:
		True if file was deleted, False if it didn't exist
	"""
	try:
		path = Path(file_path)
		if path.exists() and path.is_file():
			path.unlink()
			return True
		return False
	except Exception as e:
		logger = get_logger(__name__)
		logger.error(f"Error deleting profile photo {file_path}: {e}")
		return False


