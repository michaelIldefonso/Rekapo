"""
Utility for generating Cloudflare R2 signed URLs.
Provides time-limited access to private files without exposing permanent public URLs.

Usage:
    from utils.r2_signed_urls import generate_signed_url
    
    # In your API endpoint:
    audio_url = generate_signed_url(session.r2_audio_key, expiration_seconds=3600)
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from config.config import (
    R2_ENDPOINT,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_ENABLED
)
from utils.utils import get_logger

logger = get_logger(__name__)


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
        endpoint_url=R2_ENDPOINT,
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
    
    # Generate signed URL valid for 1 hour
    signed_url = generate_signed_url(
        session.r2_audio_key,
        expiration_seconds=3600
    )
    
    return {
        "audio_url": signed_url,
        "expires_in_seconds": 3600,
        "session_id": session_id
    }
"""
