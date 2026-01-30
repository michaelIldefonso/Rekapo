"""
Cloudflare R2 Storage Service

Provides a unified interface for file storage operations with support for both
Cloudflare R2 (S3-compatible) and local filesystem storage.
"""

import os
import boto3
from pathlib import Path
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError
from botocore.config import Config
import logging

logger = logging.getLogger(__name__)


class R2Client:
    """
    Client for interacting with Cloudflare R2 storage.
    Automatically falls back to local storage when R2 is disabled.
    """
    
    def __init__(self):
        """Initialize R2 client based on environment configuration."""
        self.r2_enabled = os.getenv("R2_ENABLED", "false").lower() == "true"
        
        if self.r2_enabled:
            self.endpoint_url = os.getenv("R2_ENDPOINT_URL")
            self.access_key_id = os.getenv("R2_ACCESS_KEY_ID")
            self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
            self.bucket_name = os.getenv("R2_BUCKET_NAME")
            self.region = os.getenv("R2_REGION", "auto")
            self.public_url = os.getenv("R2_PUBLIC_URL", "")
            
            # Validate required configuration
            if not all([self.endpoint_url, self.access_key_id, 
                       self.secret_access_key, self.bucket_name]):
                raise ValueError(
                    "R2 is enabled but missing required configuration. "
                    "Please set R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, "
                    "R2_SECRET_ACCESS_KEY, and R2_BUCKET_NAME"
                )
            
            # Initialize S3 client for R2
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region,
                config=Config(
                    signature_version='s3v4',
                    s3={'addressing_style': 'path'}
                )
            )
            
            logger.info(f"R2 storage initialized with bucket: {self.bucket_name}")
        else:
            self.s3_client = None
            logger.info("R2 storage disabled, using local filesystem")
    
    def upload_file(
        self, 
        file_content: bytes, 
        key: str, 
        content_type: Optional[str] = None,
        local_fallback_path: Optional[Path] = None
    ) -> str:
        """
        Upload a file to R2 or local storage.
        
        Args:
            file_content: The file content as bytes
            key: The object key (path) in R2 bucket
            content_type: MIME type of the file
            local_fallback_path: Path to save locally if R2 is disabled
        
        Returns:
            The URL or path to access the uploaded file
        
        Raises:
            Exception: If upload fails
        """
        if self.r2_enabled:
            try:
                extra_args = {}
                if content_type:
                    extra_args['ContentType'] = content_type
                
                # Upload to R2
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_content,
                    **extra_args
                )
                
                # Return public URL if configured, otherwise return the key
                if self.public_url:
                    return f"{self.public_url}/{key}"
                else:
                    return f"r2://{self.bucket_name}/{key}"
                
            except ClientError as e:
                logger.error(f"Failed to upload {key} to R2: {e}")
                raise Exception(f"R2 upload failed: {str(e)}")
        else:
            # Local storage fallback
            if not local_fallback_path:
                raise ValueError("local_fallback_path required when R2 is disabled")
            
            local_fallback_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_fallback_path, "wb") as f:
                f.write(file_content)
            
            # Return relative path for local storage
            return str(local_fallback_path)
    
    def download_file(self, key: str, local_path: Optional[Path] = None) -> bytes:
        """
        Download a file from R2 or local storage.
        
        Args:
            key: The object key in R2 bucket or local path
            local_path: Local path if R2 is disabled
        
        Returns:
            The file content as bytes
        
        Raises:
            Exception: If download fails
        """
        if self.r2_enabled:
            try:
                # Handle r2:// URI format
                if key.startswith("r2://"):
                    key = key.replace(f"r2://{self.bucket_name}/", "")
                
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                return response['Body'].read()
                
            except ClientError as e:
                logger.error(f"Failed to download {key} from R2: {e}")
                raise Exception(f"R2 download failed: {str(e)}")
        else:
            # Local storage fallback
            path = local_path or Path(key)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            with open(path, "rb") as f:
                return f.read()
    
    def delete_file(self, key: str, local_path: Optional[Path] = None) -> bool:
        """
        Delete a file from R2 or local storage.
        
        Args:
            key: The object key in R2 bucket or local path
            local_path: Local path if R2 is disabled
        
        Returns:
            True if deletion was successful, False otherwise
        """
        if self.r2_enabled:
            try:
                # Handle r2:// URI format
                if key.startswith("r2://"):
                    key = key.replace(f"r2://{self.bucket_name}/", "")
                
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                logger.info(f"Deleted {key} from R2")
                return True
                
            except ClientError as e:
                logger.error(f"Failed to delete {key} from R2: {e}")
                return False
        else:
            # Local storage fallback
            try:
                path = local_path or Path(key)
                if path.exists() and path.is_file():
                    path.unlink()
                    logger.info(f"Deleted local file: {path}")
                    return True
                return False
            except Exception as e:
                logger.error(f"Failed to delete local file {path}: {e}")
                return False
    
    def copy_file(self, source_key: str, dest_key: str) -> str:
        """
        Copy a file within R2 storage (more efficient than download+upload).
        
        Args:
            source_key: The source object key
            dest_key: The destination object key
        
        Returns:
            The URL or path to the copied file
        
        Raises:
            Exception: If copy fails
        """
        if self.r2_enabled:
            try:
                # Handle r2:// URI format
                if source_key.startswith("r2://"):
                    source_key = source_key.replace(f"r2://{self.bucket_name}/", "")
                if dest_key.startswith("r2://"):
                    dest_key = dest_key.replace(f"r2://{self.bucket_name}/", "")
                
                # Use S3 copy_object for efficient server-side copy
                copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
                self.s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=self.bucket_name,
                    Key=dest_key
                )
                
                logger.info(f"Copied {source_key} to {dest_key} in R2")
                
                # Return public URL if configured, otherwise return the key
                if self.public_url:
                    return f"{self.public_url}/{dest_key}"
                else:
                    return f"r2://{self.bucket_name}/{dest_key}"
                
            except ClientError as e:
                logger.error(f"Failed to copy {source_key} to {dest_key} in R2: {e}")
                raise Exception(f"R2 copy failed: {str(e)}")
        else:
            raise ValueError("copy_file only available when R2 is enabled")
    
    def file_exists(self, key: str, local_path: Optional[Path] = None) -> bool:
        """
        Check if a file exists in R2 or local storage.
        
        Args:
            key: The object key in R2 bucket or local path
            local_path: Local path if R2 is disabled
        
        Returns:
            True if file exists, False otherwise
        """
        if self.r2_enabled:
            try:
                # Handle r2:// URI format
                if key.startswith("r2://"):
                    key = key.replace(f"r2://{self.bucket_name}/", "")
                
                self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                return True
            except ClientError:
                return False
        else:
            # Local storage fallback
            path = local_path or Path(key)
            return path.exists() and path.is_file()
    
    def get_presigned_url(
        self, 
        key: str, 
        expiration: int = 3600,
        local_path: Optional[Path] = None
    ) -> str:
        """
        Generate a presigned URL for temporary access to a file.
        
        Args:
            key: The object key in R2 bucket
            expiration: URL expiration time in seconds (default: 1 hour)
            local_path: Local path if R2 is disabled (returns file path)
        
        Returns:
            Presigned URL or local file path
        """
        if self.r2_enabled:
            try:
                # Handle r2:// URI format
                if key.startswith("r2://"):
                    key = key.replace(f"r2://{self.bucket_name}/", "")
                
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': key
                    },
                    ExpiresIn=expiration
                )
                return url
                
            except ClientError as e:
                logger.error(f"Failed to generate presigned URL for {key}: {e}")
                raise Exception(f"Failed to generate presigned URL: {str(e)}")
        else:
            # Return local file path for local storage
            return str(local_path or Path(key))


# Global R2 client instance
r2_client = R2Client()
