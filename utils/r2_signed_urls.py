"""
Utility for generating Cloudflare R2 signed URLs.
Provides time-limited access to private files without exposing permanent public URLs.

Usage:
    from utils.r2_signed_urls import generate_signed_url
    
    # In your API endpoint:
    audio_url = generate_signed_url(session.r2_audio_key, expiration_seconds=R2_AUDIO_SIGNED_URL_EXPIRY_SECONDS)
"""

import boto3
import time
from functools import lru_cache
from threading import Lock
from urllib.parse import urlparse
from botocore.config import Config
from botocore.exceptions import ClientError
from config.config import (
    R2_ENDPOINT_URL,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_ENABLED,
    R2_PUBLIC_URL,
    R2_PROFILE_PHOTOS_PREFIX,
    R2_PROFILE_PHOTO_SIGNED_URL_EXPIRY_SECONDS,
    R2_PROFILE_PHOTO_SIGNED_URL_CACHE_SECONDS,
    R2_AUDIO_SIGNED_URL_EXPIRY_SECONDS,
)
from utils.utils import get_logger

logger = get_logger(__name__)
_SIGNED_URL_CACHE: dict[tuple[str, int], tuple[str, float]] = {}
_SIGNED_URL_CACHE_LOCK = Lock()


@lru_cache(maxsize=1)
def get_r2_client():
    """
    Create and return an S3-compatible client for Cloudflare R2.
    
    Returns:
        boto3 S3 client configured for R2
    """
    if not R2_ENABLED:
        raise RuntimeError("R2 is not enabled. Set R2_ENABLED=true in .env")
    
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
        region_name='auto'  # Cloudflare R2 uses 'auto' region
    )


def generate_signed_url(
    file_key: str,
    expiration_seconds: int = 3600,
    response_content_type: str = None
) -> str:
    """
    Generate a pre-signed URL for secure, time-limited access to R2 files.
    
    This replaces permanent public URLs with temporary signed URLs that:
    - Expire after the specified duration (default 1 hour)
    - Cannot be reused after expiration
    - Provide controlled access to private files
    
    Args:
        file_key: The object key (filename/path) in R2 bucket
        expiration_seconds: URL validity duration in seconds (default: 3600 = 1 hour)
        response_content_type: Optional Content-Type header for the response
    
    Returns:
        Pre-signed URL string that expires after expiration_seconds
        
    Raises:
        RuntimeError: If R2 is not enabled
        ClientError: If file doesn't exist or R2 credentials invalid
        
    Example:
        >>> # Generate URL for audio file, valid for 2 hours
        >>> url = generate_signed_url("audio/session_123.mp3", expiration_seconds=7200)
        >>> # URL automatically expires after 2 hours
    """
    if not R2_ENABLED:
        logger.error("Attempted to generate signed URL but R2 is disabled")
        raise RuntimeError("R2 storage is not enabled")
    
    try:
        s3_client = get_r2_client()
        
        params = {
            'Bucket': R2_BUCKET_NAME,
            'Key': file_key
        }
        
        # Add Content-Type if specified (useful for forcing download vs inline display)
        if response_content_type:
            params['ResponseContentType'] = response_content_type
        
        signed_url = s3_client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=expiration_seconds
        )
        
        logger.info(
            f"Generated signed URL for {file_key} (expires in {expiration_seconds}s)"
        )
        
        return signed_url
    
    except ClientError as e:
        logger.error(f"Error generating signed URL for {file_key}: {e}")
        raise


def generate_signed_url_cached(
    file_key: str,
    expiration_seconds: int = 3600,
    cache_seconds: int | None = None,
) -> str:
    """
    Generate a signed URL with in-memory TTL caching.

    This reduces repeated presign operations for frequently accessed files.
    """
    effective_cache_seconds = (
        R2_PROFILE_PHOTO_SIGNED_URL_CACHE_SECONDS
        if cache_seconds is None
        else max(0, cache_seconds)
    )

    if effective_cache_seconds == 0:
        return generate_signed_url(file_key, expiration_seconds=expiration_seconds)

    now = time.time()
    cache_key = (file_key, expiration_seconds)

    with _SIGNED_URL_CACHE_LOCK:
        cached = _SIGNED_URL_CACHE.get(cache_key)
        if cached:
            cached_url, expires_at = cached
            if now < expires_at:
                return cached_url

    signed_url = generate_signed_url(file_key, expiration_seconds=expiration_seconds)

    with _SIGNED_URL_CACHE_LOCK:
        _SIGNED_URL_CACHE[cache_key] = (signed_url, now + effective_cache_seconds)

    return signed_url


def resolve_profile_photo_url(file_path: str | None) -> str | None:
    """
    Resolve stored profile photo path into a client-usable URL.

    - External provider URLs (e.g., Google photos) are returned unchanged.
    - R2 object references are converted to short-lived signed URLs.
    - Local paths are returned as-is.
    """
    if not file_path:
        return file_path

    # Keep non-R2 external URLs unchanged (e.g., Google profile images).
    if file_path.startswith("http") and "r2.dev" not in file_path:
        if not R2_PUBLIC_URL or not file_path.startswith(R2_PUBLIC_URL):
            return file_path

    if not R2_ENABLED:
        return file_path

    r2_key = None

    if file_path.startswith("r2://"):
        parts = file_path.split("/", 3)
        if len(parts) >= 4:
            r2_key = parts[3]
    elif file_path.startswith("http"):
        parsed = urlparse(file_path)
        r2_key = parsed.path.lstrip("/")
    elif file_path.startswith(f"{R2_PROFILE_PHOTOS_PREFIX}/"):
        r2_key = file_path

    if not r2_key:
        return file_path

    try:
        return generate_signed_url_cached(
            r2_key,
            expiration_seconds=R2_PROFILE_PHOTO_SIGNED_URL_EXPIRY_SECONDS,
            cache_seconds=min(
                R2_PROFILE_PHOTO_SIGNED_URL_CACHE_SECONDS,
                max(1, R2_PROFILE_PHOTO_SIGNED_URL_EXPIRY_SECONDS - 30),
            ),
        )
    except Exception as e:
        logger.warning("Failed to sign profile photo URL for %s: %s", r2_key, e)
        return file_path


def generate_upload_signed_url(
    file_key: str,
    expiration_seconds: int = 600,
    content_type: str = "audio/mpeg"
) -> str:
    """
    Generate a pre-signed URL for uploading files directly to R2.
    Allows clients to upload files without going through backend.
    
    Args:
        file_key: The object key where file will be stored
        expiration_seconds: URL validity (default: 600 = 10 minutes)
        content_type: Expected file MIME type
    
    Returns:
        Pre-signed URL for PUT request
        
    Example:
        >>> # Generate upload URL for mobile app
        >>> upload_url = generate_upload_signed_url(
        ...     f"audio/{session_id}_{timestamp}.mp3",
        ...     expiration_seconds=600
        ... )
        >>> # Mobile app can PUT file directly to this URL
    """
    if not R2_ENABLED:
        raise RuntimeError("R2 storage is not enabled")
    
    try:
        s3_client = get_r2_client()
        
        signed_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': R2_BUCKET_NAME,
                'Key': file_key,
                'ContentType': content_type
            },
            ExpiresIn=expiration_seconds
        )
        
        logger.info(
            f"Generated upload signed URL for {file_key} (expires in {expiration_seconds}s)"
        )
        
        return signed_url
    
    except ClientError as e:
        logger.error(f"Error generating upload signed URL for {file_key}: {e}")
        raise


def verify_file_exists(file_key: str) -> bool:
    """
    Check if a file exists in R2 bucket.
    
    Args:
        file_key: The object key to check
        
    Returns:
        True if file exists, False otherwise
    """
    if not R2_ENABLED:
        return False
    
    try:
        s3_client = get_r2_client()
        s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=file_key)
        return True
    except ClientError:
        return False


# Example usage in FastAPI route:
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from db.db import get_db, Session as DBSession
from utils.r2_signed_urls import generate_signed_url, verify_file_exists

router = APIRouter()

@router.get("/api/sessions/{session_id}/audio")
async def get_session_audio_url(
    session_id: int,
    db: Session = Depends(get_db)
):
    '''
    Get a time-limited signed URL for session audio file.
    URL expires after 1 hour for security.
    '''
    session = db.query(DBSession).filter(DBSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.r2_audio_key:
        raise HTTPException(status_code=404, detail="Audio file not available")
    
    # Verify file exists before generating URL
    if not verify_file_exists(session.r2_audio_key):
        raise HTTPException(status_code=404, detail="Audio file not found in storage")
    
    # Generate signed URL
    signed_url = generate_signed_url(
        session.r2_audio_key,
        expiration_seconds=R2_AUDIO_SIGNED_URL_EXPIRY_SECONDS
    )
    
    return {
        "audio_url": signed_url,
        "expires_in_seconds": R2_AUDIO_SIGNED_URL_EXPIRY_SECONDS,
        "session_id": session_id
    }
"""
