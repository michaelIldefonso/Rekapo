"""
Application logging endpoints for mobile apps.
Write logs from mobile app - viewing/management is in admin/admin_logs.py
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.db import get_db, User, AppLog
from routes.auth import get_current_user
from utils.utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


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
async def write_logs_to_database(
    log_batch: LogBatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Write logs to database.
    Endpoints: /api/logs/write or /api/logs/app
    """
    logger.info("📥 Received log batch - User: %s, Logs: %d", 
               current_user.id, len(log_batch.logs))
    
    try:
        # Get batch timestamp (handle both field names from different mobile versions)
        batch_time_str = log_batch.batch_timestamp or log_batch.timestamp
        batch_time = None
        if batch_time_str:
            try:
                batch_time = datetime.fromisoformat(batch_time_str.replace('Z', '+00:00'))
            except:
                batch_time = datetime.now()
        else:
            batch_time = datetime.now()
        
        # Insert logs into database
        log_entries = []
        for log in log_batch.logs:
            try:
                log_timestamp = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
            except:
                log_timestamp = datetime.now()
            
            log_entry = AppLog(
                user_id=current_user.id,
                level=log.level,
                message=log.message,
                timestamp=log_timestamp,
                batch_timestamp=batch_time,
                app_version=log_batch.app_version,
                platform=log_batch.platform
            )
            log_entries.append(log_entry)
        
        db.add_all(log_entries)
        db.commit()
        
        logger.info("✓ Logs written to database - User: %s, Count: %d", 
                   current_user.id, len(log_batch.logs))
        
        return {
            "status": "success",
            "logs_written": len(log_batch.logs)
        }
    
    except Exception as e:
        db.rollback()
        logger.error("Error writing logs to database: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to write logs"
        )
