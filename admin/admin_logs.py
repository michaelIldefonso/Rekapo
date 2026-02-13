"""
Admin endpoints for viewing and managing application logs.
All endpoints require admin authentication.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from db.db import get_db, User, AppLog
from admin.utils import get_current_admin
from utils.utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/admin/logs/summary")
async def get_log_summary(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get summary of logs from database (admin only).
    Optionally filter by date.
    """
    try:
        query = db.query(
            func.date(AppLog.timestamp).label('date'),
            func.count(AppLog.id).label('total'),
            func.sum(func.case((AppLog.level == 'error', 1), else_=0)).label('errors'),
            func.sum(func.case((AppLog.level == 'warn', 1), else_=0)).label('warnings'),
            func.sum(func.case((AppLog.level == 'info', 1), else_=0)).label('info')
        )
        
        if date:
            try:
                filter_date = datetime.strptime(date, '%Y-%m-%d').date()
                query = query.filter(func.date(AppLog.timestamp) == filter_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        
        results = query.group_by(func.date(AppLog.timestamp)).order_by(func.date(AppLog.timestamp).desc()).limit(30).all()
        
        summary = [
            {
                "date": str(row.date),
                "total": row.total,
                "errors": row.errors,
                "warnings": row.warnings,
                "info": row.info
            }
            for row in results
        ]
        
        logger.info("✓ Retrieved log summary (Admin: %s, Date filter: %s)", 
                   current_admin.id, date or "none")
        
        return {"summary": summary, "count": len(summary)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting log summary: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get log summary"
        )


@router.get("/admin/logs/recent")
async def get_recent_logs(
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to retrieve"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get recent logs from database (admin only).
    Optionally filter by log level.
    """
    try:
        query = db.query(AppLog, User.email).join(User, AppLog.user_id == User.id)
        
        if level:
            query = query.filter(AppLog.level == level)
        
        logs = query.order_by(AppLog.timestamp.desc()).limit(limit).all()
        
        result = [
            {
                "id": log.AppLog.id,
                "user_id": log.AppLog.user_id,
                "user_email": log.email,
                "level": log.AppLog.level,
                "message": log.AppLog.message,
                "timestamp": log.AppLog.timestamp.isoformat(),
                "app_version": log.AppLog.app_version,
                "platform": log.AppLog.platform
            }
            for log in logs
        ]
        
        logger.info("✓ Retrieved %d recent logs (Admin: %s, Level: %s)", 
                   len(result), current_admin.id, level or "all")
        
        return {"logs": result, "count": len(result)}
    
    except Exception as e:
        logger.error("Error getting recent logs: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recent logs"
        )


@router.get("/admin/logs/errors/recent")
async def get_recent_errors(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 168 = 1 week)"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all errors from last N hours (admin only).
    Default: 24 hours, max: 7 days.
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        errors = db.query(AppLog, User.email).join(User, AppLog.user_id == User.id).filter(
            and_(
                AppLog.level == 'error',
                AppLog.timestamp >= cutoff_time
            )
        ).order_by(AppLog.timestamp.desc()).all()
        
        result = [
            {
                "user_id": error.AppLog.user_id,
                "user_email": error.email,
                "timestamp": error.AppLog.timestamp.isoformat(),
                "message": error.AppLog.message,
                "app_version": error.AppLog.app_version,
                "platform": error.AppLog.platform
            }
            for error in errors
        ]
        
        logger.info("✓ Found %d recent errors (Admin: %s, Hours: %d)", 
                   len(result), current_admin.id, hours)
        
        return {
            "errors": result, 
            "count": len(result),
            "hours": hours,
            "cutoff_time": cutoff_time.isoformat()
        }
    
    except Exception as e:
        logger.error("Error retrieving recent errors: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent errors"
        )


@router.get("/admin/logs/stats")
async def get_log_stats(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 168 = 1 week)"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get log statistics for dashboard widgets (admin only).
    Returns total logs, error/warn/info counts, and top errors.
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Get total counts by level
        counts = db.query(
            func.count(AppLog.id).label('total'),
            func.sum(func.case((AppLog.level == 'error', 1), else_=0)).label('errors'),
            func.sum(func.case((AppLog.level == 'warn', 1), else_=0)).label('warnings'),
            func.sum(func.case((AppLog.level == 'info', 1), else_=0)).label('info')
        ).filter(AppLog.timestamp >= cutoff_time).first()
        
        # Get top error messages
        top_errors = db.query(
            func.substr(AppLog.message, 1, 100).label('message'),
            func.count(AppLog.id).label('count')
        ).filter(
            and_(
                AppLog.level == 'error',
                AppLog.timestamp >= cutoff_time
            )
        ).group_by(func.substr(AppLog.message, 1, 100)).order_by(func.count(AppLog.id).desc()).limit(5).all()
        
        # Get users with most errors
        top_error_users = db.query(
            User.email,
            func.count(AppLog.id).label('count')
        ).join(AppLog, User.id == AppLog.user_id).filter(
            and_(
                AppLog.level == 'error',
                AppLog.timestamp >= cutoff_time
            )
        ).group_by(User.email).order_by(func.count(AppLog.id).desc()).limit(5).all()
        
        logger.info("✓ Retrieved log stats (Admin: %s, Hours: %d, Total: %d)", 
                   current_admin.id, hours, counts.total)
        
        return {
            "period_hours": hours,
            "total_logs": counts.total or 0,
            "errors": counts.errors or 0,
            "warnings": counts.warnings or 0,
            "info": counts.info or 0,
            "top_errors": [{"message": e.message, "count": e.count} for e in top_errors],
            "top_error_users": [{"email": u.email, "count": u.count} for u in top_error_users]
        }
    
    except Exception as e:
        logger.error("Error retrieving log stats: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve log stats"
        )


@router.get("/admin/logs/user/{user_id}")
async def get_logs_by_user_id(
    user_id: int,
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 168 = 1 week)"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all logs for a specific user from last N hours (admin only).
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        query = db.query(AppLog).filter(
            and_(
                AppLog.user_id == user_id,
                AppLog.timestamp >= cutoff_time
            )
        )
        
        if level:
            query = query.filter(AppLog.level == level)
        
        logs = query.order_by(AppLog.timestamp.desc()).all()
        
        result = [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "app_version": log.app_version,
                "platform": log.platform
            }
            for log in logs
        ]
        
        logger.info("✓ Found %d logs for user %d (Admin: %s, Hours: %d)", 
                   len(result), user_id, current_admin.id, hours)
        
        return {
            "user_id": user_id,
            "logs": result,
            "count": len(result),
            "hours": hours
        }
    
    except Exception as e:
        logger.error("Error retrieving user logs: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user logs"
        )


@router.get("/admin/logs/user/email/{email}")
async def get_logs_by_email(
    email: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 168 = 1 week)"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Search logs by user email from last N hours (admin only).
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Find user by email
        user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
        if not user:
            return {
                "email": email,
                "logs": [],
                "count": 0,
                "hours": hours,
                "message": "User not found"
            }
        
        query = db.query(AppLog).filter(
            and_(
                AppLog.user_id == user.id,
                AppLog.timestamp >= cutoff_time
            )
        )
        
        if level:
            query = query.filter(AppLog.level == level)
        
        logs = query.order_by(AppLog.timestamp.desc()).all()
        
        result = [
            {
                "user_id": log.user_id,
                "user_email": email,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "app_version": log.app_version,
                "platform": log.platform
            }
            for log in logs
        ]
        
        logger.info("✓ Found %d logs for email %s (Admin: %s, Hours: %d)", 
                   len(result), email, current_admin.id, hours)
        
        return {
            "email": email,
            "logs": result,
            "count": len(result),
            "hours": hours
        }
    
    except Exception as e:
        logger.error("Error searching logs by email: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search logs by email"
        )


@router.delete("/admin/logs/cleanup")
async def cleanup_old_logs(
    days: int = Query(30, ge=1, le=365, description="Delete logs older than N days"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete logs older than specified days from database (admin only).
    Default: 30 days, max: 365 days.
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted_count = db.query(AppLog).filter(AppLog.timestamp < cutoff_date).delete()
        db.commit()
        
        logger.info("✓ Cleaned up %d old log entries (Admin: %s, Days: %d, Cutoff: %s)", 
                   deleted_count, current_admin.id, days, cutoff_date.date())
        
        return {
            "deleted": deleted_count,
            "days": days,
            "cutoff_date": cutoff_date.isoformat()
        }
    
    except Exception as e:
        db.rollback()
        logger.error("Error cleaning up logs: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup logs"
        )


def cleanup_old_logs_job():
    """
    Background job to cleanup logs older than 7 days.
    Called by the scheduler in main.py.
    Uses distributed lock to prevent duplicate execution across workers.
    """
    from db.db import SessionLocal
    from sqlalchemy import text
    import os
    
    db = SessionLocal()
    try:
        # Acquire distributed lock (prevents duplicate execution)
        if "postgresql" in str(db.bind.url):
            lock_id = hash("log_cleanup") % 2147483647
            result = db.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": lock_id}
            )
            if not result.scalar():
                logger.info("[Cleanup Job] Skipped - another worker is running this job")
                return
        
        cutoff_date = datetime.now() - timedelta(days=7)
        deleted_count = db.query(AppLog).filter(AppLog.timestamp < cutoff_date).delete()
        db.commit()
        
        logger.info("[Cleanup Job] ✓ Deleted %d old log entries (cutoff: %s, worker: %d)", 
                   deleted_count, cutoff_date.date(), os.getpid())
    
    except Exception as e:
        db.rollback()
        logger.error("[Cleanup Job] Error cleaning up logs: %s", str(e))
    finally:
        db.close()
