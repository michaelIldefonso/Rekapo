import os
import json
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.db import get_db, User
from routes.auth import get_current_user
from admin.utils import get_current_admin
from utils.utils import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Initialize R2 client (S3-compatible) for logging operations
r2_client = None
BUCKET_NAME = os.getenv('R2_BUCKET_NAME', 'rekapo')

try:
    endpoint_url = os.getenv('R2_ENDPOINT_URL')
    access_key_id = os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = os.getenv('R2_SECRET_ACCESS_KEY')
    region = os.getenv('R2_REGION', 'auto')
    
    if not all([endpoint_url, access_key_id, secret_access_key]):
        logger.warning("⚠️ R2 logging disabled - missing credentials (R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, or R2_SECRET_ACCESS_KEY)")
    else:
        r2_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
            config=Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}
            )
        )
        logger.info("✓ R2 logging client initialized successfully")
        logger.info("  - Bucket: %s", BUCKET_NAME)
        logger.info("  - Endpoint: %s", endpoint_url)
except Exception as e:
    logger.error("❌ R2 client initialization failed: %s", str(e))
    r2_client = None


class LogEntry(BaseModel):
    level: str  # 'info', 'warn', 'error', 'network'
    message: str
    timestamp: str
    
    class Config:
        extra = "allow"  # Allow extra fields from mobile app


class LogBatch(BaseModel):
    logs: List[LogEntry]
    batch_timestamp: Optional[str] = None
    timestamp: Optional[str] = None  # Alternative field name from mobile app
    app_version: Optional[str] = None
    platform: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow extra fields from mobile app


@router.post("/logs/write")
@router.post("/logs/app")  # Alias for mobile app compatibility
async def write_logs_to_r2(
    log_batch: LogBatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Write logs to Cloudflare R2 bucket.
    File path: logs/2026/02/09/user_123_14-30-00.json
    Endpoints: /api/logs/write or /api/logs/app
    """
    logger.info("📥 Received log batch - User: %s, Logs: %d", 
               current_user.id, len(log_batch.logs))
    
    if not r2_client:
        logger.warning("R2 client not configured - logs not stored")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log storage service not configured"
        )
    
    try:
        # Generate hierarchical path
        now = datetime.now()
        file_path = (
            f"logs/{now.year}/{now.month:02d}/{now.day:02d}/"
            f"user_{current_user.id}_{now.strftime('%H-%M-%S')}.json"
        )
        
        # Prepare log data (handle both timestamp field names from different mobile versions)
        batch_time = log_batch.batch_timestamp or log_batch.timestamp or datetime.now().isoformat()
        
        log_data = {
            "user_id": current_user.id,
            "user_email": current_user.email,
            "batch_timestamp": batch_time,
            "app_version": log_batch.app_version,
            "platform": log_batch.platform,
            "logs": [
                {
                    "level": log.level,
                    "message": log.message,
                    "timestamp": log.timestamp
                }
                for log in log_batch.logs
            ]
        }
        
        # Upload to R2
        r2_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_path,
            Body=json.dumps(log_data, indent=2),
            ContentType='application/json'
        )
        
        logger.info("✓ Logs written to R2 - User: %s, File: %s, Count: %d", 
                   current_user.id, file_path, len(log_batch.logs))
        
        return {
            "status": "success",
            "logs_written": len(log_batch.logs),
            "file": file_path
        }
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error("R2 ClientError writing logs: %s - %s", error_code, error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to write logs to R2: {error_code}"
        )
    except Exception as e:
        logger.error("Error writing logs to R2: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to write logs"
        )


@router.get("/logs/files")
async def list_log_files(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List log files from R2 (admin only).
    Optionally filter by date.
    """
    if not r2_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log storage service not configured"
        )
    
    try:
        prefix = "logs/"
        if date:
            parts = date.split('-')
            if len(parts) == 3:
                prefix = f"logs/{parts[0]}/{parts[1]}/{parts[2]}/"
        
        response = r2_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix
        )
        
        files = []
        if 'Contents' in response:
            files = [
                {
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat()
                }
                for obj in response['Contents']
            ]
            files.sort(key=lambda x: x['last_modified'], reverse=True)
        
        logger.info("✓ Listed %d log files (Admin: %s, Date filter: %s)", 
                   len(files), current_admin.id, date or "none")
        
        return {"files": files, "count": len(files)}
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error("R2 ClientError listing files: %s", error_code)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list log files"
        )
    except Exception as e:
        logger.error("Error listing log files: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list log files"
        )


@router.get("/logs/view/{file_path:path}")
async def view_log_file(
    file_path: str,
    level: Optional[str] = Query(None, description="Filter by log level"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    View contents of log file from R2 (admin only).
    Optionally filter by log level.
    """
    if not r2_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log storage service not configured"
        )
    
    try:
        response = r2_client.get_object(
            Bucket=BUCKET_NAME,
            Key=file_path
        )
        
        log_data = json.loads(response['Body'].read())
        
        if level:
            log_data['logs'] = [
                log for log in log_data['logs'] 
                if log['level'] == level
            ]
        
        logger.info("✓ Viewed log file - Admin: %s, File: %s, Count: %d", 
                   current_admin.id, file_path, len(log_data['logs']))
        
        return {
            "file": file_path,
            "user_id": log_data.get('user_id'),
            "user_email": log_data.get('user_email'),
            "batch_timestamp": log_data.get('batch_timestamp'),
            "logs": log_data['logs'],
            "count": len(log_data['logs'])
        }
    
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Log file not found"
            )
        logger.error("Error viewing log file: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error viewing log file: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/logs/errors/recent")
async def get_recent_errors(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 168 = 1 week)"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all errors from last N hours (admin only).
    Default: 24 hours, max: 7 days.
    """
    if not r2_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log storage service not configured"
        )
    
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        all_errors = []
        
        # Search in logs for the last N days (covering the hours requested)
        days_to_check = (hours // 24) + 2  # Add buffer for timezone differences
        
        for day_offset in range(days_to_check):
            check_date = datetime.now() - timedelta(days=day_offset)
            date_prefix = f"logs/{check_date.year}/{check_date.month:02d}/{check_date.day:02d}/"
            
            response = r2_client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=date_prefix
            )
            
            if 'Contents' not in response:
                continue
            
            for obj in response['Contents']:
                # Skip files older than cutoff
                if obj['LastModified'].replace(tzinfo=None) < cutoff_time:
                    continue
                
                try:
                    file_response = r2_client.get_object(
                        Bucket=BUCKET_NAME,
                        Key=obj['Key']
                    )
                    log_data = json.loads(file_response['Body'].read())
                    
                    for log in log_data.get('logs', []):
                        if log['level'] == 'error':
                            log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                            if log_time.replace(tzinfo=None) >= cutoff_time:
                                all_errors.append({
                                    "user_id": log_data.get('user_id'),
                                    "user_email": log_data.get('user_email'),
                                    "timestamp": log['timestamp'],
                                    "message": log['message'],
                                    "file": obj['Key']
                                })
                except Exception as e:
                    logger.warning("Error processing log file %s: %s", obj['Key'], str(e))
                    continue
        
        all_errors.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info("✓ Found %d recent errors (Admin: %s, Hours: %d)", 
                   len(all_errors), current_admin.id, hours)
        
        return {
            "errors": all_errors, 
            "count": len(all_errors),
            "hours": hours,
            "cutoff_time": cutoff_time.isoformat()
        }
    
    except Exception as e:
        logger.error("Error retrieving recent errors: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/logs/stats")
async def get_log_stats(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 168 = 1 week)"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get log statistics for dashboard widgets (admin only).
    Returns total logs, error/warn/info counts, and top errors.
    """
    if not r2_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log storage service not configured"
        )
    
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        stats = {
            "total_logs": 0,
            "errors": 0,
            "warnings": 0,
            "info": 0,
            "top_errors": {},
            "top_error_users": {}
        }
        
        # Scan recent files
        days_to_check = (hours // 24) + 2
        for day_offset in range(days_to_check):
            check_date = datetime.now() - timedelta(days=day_offset)
            date_prefix = f"logs/{check_date.year}/{check_date.month:02d}/{check_date.day:02d}/"
            
            response = r2_client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=date_prefix
            )
            
            if 'Contents' not in response:
                continue
            
            for obj in response['Contents']:
                try:
                    file_response = r2_client.get_object(
                        Bucket=BUCKET_NAME,
                        Key=obj['Key']
                    )
                    log_data = json.loads(file_response['Body'].read())
                    
                    for log in log_data.get('logs', []):
                        log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                        if log_time.replace(tzinfo=None) >= cutoff_time:
                            stats["total_logs"] += 1
                            
                            if log['level'] == 'error':
                                stats["errors"] += 1
                                # Track error messages
                                error_msg = log['message'][:100]
                                stats["top_errors"][error_msg] = stats["top_errors"].get(error_msg, 0) + 1
                                # Track users with errors
                                user_email = log_data.get('user_email', 'unknown')
                                stats["top_error_users"][user_email] = stats["top_error_users"].get(user_email, 0) + 1
                            elif log['level'] == 'warn':
                                stats["warnings"] += 1
                            else:
                                stats["info"] += 1
                except Exception as e:
                    logger.warning("Error processing log file %s: %s", obj['Key'], str(e))
                    continue
        
        # Format top lists
        top_errors = sorted(stats["top_errors"].items(), key=lambda x: x[1], reverse=True)[:5]
        top_error_users = sorted(stats["top_error_users"].items(), key=lambda x: x[1], reverse=True)[:5]
        
        logger.info("✓ Retrieved log stats (Admin: %s, Hours: %d, Total: %d)", 
                   current_admin.id, hours, stats["total_logs"])
        
        return {
            "period_hours": hours,
            "total_logs": stats["total_logs"],
            "errors": stats["errors"],
            "warnings": stats["warnings"],
            "info": stats["info"],
            "top_errors": [{"message": msg, "count": count} for msg, count in top_errors],
            "top_error_users": [{"email": email, "count": count} for email, count in top_error_users]
        }
    
    except Exception as e:
        logger.error("Error retrieving log stats: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/logs/user/{user_id}")
async def get_logs_by_user_id(
    user_id: int,
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 168 = 1 week)"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all logs for a specific user from last N hours (admin only).
    Searches by user ID.
    """
    if not r2_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log storage service not configured"
        )
    
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        user_logs = []
        
        # Scan recent days
        days_to_check = (hours // 24) + 2
        for day_offset in range(days_to_check):
            check_date = datetime.now() - timedelta(days=day_offset)
            date_prefix = f"logs/{check_date.year}/{check_date.month:02d}/{check_date.day:02d}/"
            
            response = r2_client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=date_prefix
            )
            
            if 'Contents' not in response:
                continue
            
            for obj in response['Contents']:
                # Check if filename contains user_id (format: user_{id}_timestamp.json)
                if f"user_{user_id}_" in obj['Key']:
                    try:
                        file_response = r2_client.get_object(
                            Bucket=BUCKET_NAME,
                            Key=obj['Key']
                        )
                        log_data = json.loads(file_response['Body'].read())
                        
                        for log in log_data.get('logs', []):
                            log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                            if log_time.replace(tzinfo=None) >= cutoff_time:
                                # Filter by level if specified
                                if level is None or log['level'] == level:
                                    user_logs.append({
                                        "timestamp": log['timestamp'],
                                        "level": log['level'],
                                        "message": log['message'],
                                        "file": obj['Key']
                                    })
                    except Exception as e:
                        logger.warning("Error processing log file %s: %s", obj['Key'], str(e))
                        continue
        
        user_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info("✓ Found %d logs for user %d (Admin: %s, Hours: %d)", 
                   len(user_logs), user_id, current_admin.id, hours)
        
        return {
            "user_id": user_id,
            "logs": user_logs,
            "count": len(user_logs),
            "hours": hours
        }
    
    except Exception as e:
        logger.error("Error retrieving user logs: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/logs/user/email/{email}")
async def get_logs_by_email(
    email: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 168 = 1 week)"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Search logs by user email from last N hours (admin only).
    Scans all log files and matches by email address.
    """
    if not r2_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log storage service not configured"
        )
    
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        matching_logs = []
        
        # Scan recent days
        days_to_check = (hours // 24) + 2
        for day_offset in range(days_to_check):
            check_date = datetime.now() - timedelta(days=day_offset)
            date_prefix = f"logs/{check_date.year}/{check_date.month:02d}/{check_date.day:02d}/"
            
            response = r2_client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=date_prefix
            )
            
            if 'Contents' not in response:
                continue
            
            for obj in response['Contents']:
                try:
                    file_response = r2_client.get_object(
                        Bucket=BUCKET_NAME,
                        Key=obj['Key']
                    )
                    log_data = json.loads(file_response['Body'].read())
                    
                    # Check if email matches
                    if log_data.get('user_email', '').lower() == email.lower():
                        for log in log_data.get('logs', []):
                            log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                            if log_time.replace(tzinfo=None) >= cutoff_time:
                                if level is None or log['level'] == level:
                                    matching_logs.append({
                                        "user_id": log_data.get('user_id'),
                                        "user_email": log_data.get('user_email'),
                                        "timestamp": log['timestamp'],
                                        "level": log['level'],
                                        "message": log['message'],
                                        "file": obj['Key']
                                    })
                except Exception as e:
                    logger.warning("Error processing log file %s: %s", obj['Key'], str(e))
                    continue
        
        matching_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info("✓ Found %d logs for email %s (Admin: %s, Hours: %d)", 
                   len(matching_logs), email, current_admin.id, hours)
        
        return {
            "email": email,
            "logs": matching_logs,
            "count": len(matching_logs),
            "hours": hours
        }
    
    except Exception as e:
        logger.error("Error searching logs by email: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/logs/cleanup")
async def cleanup_old_logs(
    days: int = Query(30, ge=1, le=365, description="Delete logs older than N days"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete logs older than specified days from R2 (admin only).
    Default: 30 days, max: 365 days.
    """
    if not r2_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log storage service not configured"
        )
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        response = r2_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix="logs/"
        )
        
        deleted_count = 0
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    r2_client.delete_object(
                        Bucket=BUCKET_NAME,
                        Key=obj['Key']
                    )
                    deleted_count += 1
        
        logger.info("✓ Cleaned up %d old log files (Admin: %s, Days: %d, Cutoff: %s)", 
                   deleted_count, current_admin.id, days, cutoff_date.date())
        
        return {
            "deleted": deleted_count,
            "days": days,
            "cutoff_date": cutoff_date.isoformat()
        }
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error("R2 ClientError during cleanup: %s", error_code)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup logs"
        )
    except Exception as e:
        logger.error("Error cleaning up logs: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup logs"
        )


def cleanup_old_logs_job():
    """
    Background job to cleanup logs older than 7 days.
    Called by the scheduler in main.py.
    """
    if not r2_client:
        logger.warning("[Cleanup Job] R2 client not configured - skipping log cleanup")
        return
    
    try:
        cutoff_date = datetime.now() - timedelta(days=7)
        
        response = r2_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix="logs/"
        )
        
        deleted_count = 0
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    r2_client.delete_object(
                        Bucket=BUCKET_NAME,
                        Key=obj['Key']
                    )
                    deleted_count += 1
        
        logger.info("[Cleanup Job] ✓ Deleted %d old log files (cutoff: %s)", 
                   deleted_count, cutoff_date.date())
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error("[Cleanup Job] R2 ClientError: %s", error_code)
    except Exception as e:
        logger.error("[Cleanup Job] Error cleaning up logs: %s", str(e))
