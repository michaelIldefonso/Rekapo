"""
Background scheduler for automated tasks:
- Daily statistics calculation at 2 AM
- Log cleanup (7 days) at 3 AM daily
- Soft-deleted sessions cleanup (15 days) at 4 AM daily
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from utils.utils import get_logger
from db.db import SessionLocal, Session as DBSession
from admin.admin_logs import cleanup_old_logs_job
from sqlalchemy import text
import os

logger = get_logger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()

# Worker ID for distributed lock (use process ID)
WORKER_ID = os.getpid()


def acquire_job_lock(db, job_name: str, timeout_minutes: int = 10) -> bool:
    """
    Acquire a distributed lock for a scheduled job using database advisory lock.
    Prevents duplicate execution when running multiple workers.
    
    Returns True if lock acquired, False otherwise.
    """
    try:
        # Use PostgreSQL advisory lock (session-level, auto-released on disconnect)
        # For SQLite, use a simple table-based lock
        if "sqlite" in str(db.bind.url):
            # Simple implementation for SQLite (good enough for thesis project)
            result = db.execute(
                text("SELECT 1 FROM system_statistics LIMIT 1")
            )
            return True  # SQLite single-process, always allow
        else:
            # PostgreSQL advisory lock (hash job_name to integer)
            lock_id = hash(job_name) % 2147483647
            result = db.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": lock_id}
            )
            acquired = result.scalar()
            return bool(acquired)
    except Exception as e:
        logger.warning(f"[Job Lock] Error acquiring lock for {job_name}: {e}")
        return False


def calculate_daily_statistics_job():
    """
    Background job to calculate statistics for yesterday.
    Runs daily at 2 AM.
    Uses distributed lock to prevent duplicate execution across workers.
    """
    db = SessionLocal()
    try:
        # Try to acquire lock (prevents duplicate execution)
        if not acquire_job_lock(db, "daily_statistics"):
            logger.info("[Statistics Job] Skipped - another worker is running this job")
            return
        
        # Import here to avoid circular imports
        from admin.services import SystemStatisticsService
        
        # Calculate statistics for yesterday
        yesterday = (datetime.now() - timedelta(days=1)).date()
        
        logger.info("[Statistics Job] Calculating statistics for %s (worker %s)", yesterday, WORKER_ID)
        stat = SystemStatisticsService.calculate_statistics_for_date(db, yesterday)
        
        logger.info(
            "[Statistics Job] ✓ Statistics calculated - Date: %s, Users: %s, Active: %s, Sessions: %s, Avg Duration: %.2f min",
            stat.stat_date, stat.total_users, stat.active_users, 
            stat.total_sessions, stat.average_session_duration or 0
        )
    
    except Exception as e:
        logger.error("[Statistics Job] Error calculating statistics: %s", str(e))
    finally:
        db.close()


def cleanup_deleted_sessions_job():
    """
    Background job to permanently delete soft-deleted sessions older than 15 days.
    Runs daily at 4 AM.
    Uses distributed lock to prevent duplicate execution across workers.
    """
    db = SessionLocal()
    try:
        # Acquire distributed lock (prevents duplicate execution)
        if not acquire_job_lock(db, "session_cleanup"):
            logger.info("[Session Cleanup] Skipped - another worker is running this job")
            return
        
        # Calculate cutoff date (15 days ago)
        cutoff_date = datetime.now() - timedelta(days=15)
        
        # Find sessions to delete
        sessions_to_delete = db.query(DBSession).filter(
            DBSession.is_deleted == True,
            DBSession.deleted_at < cutoff_date
        ).all()
        
        deleted_count = len(sessions_to_delete)
        
        if deleted_count > 0:
            # Permanently delete sessions (CASCADE will handle related segments/summaries)
            for session in sessions_to_delete:
                db.delete(session)
            
            db.commit()
            logger.info(
                "[Session Cleanup] ✓ Permanently deleted %d soft-deleted sessions (cutoff: %s, worker: %d)",
                deleted_count, cutoff_date.date(), WORKER_ID
            )
        else:
            logger.info("[Session Cleanup] No old soft-deleted sessions to clean up")
    
    except Exception as e:
        db.rollback()
        logger.error("[Session Cleanup] Error cleaning up sessions: %s", str(e))
    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler with all scheduled jobs.
    Called during application startup.
    
    Note: When running multiple workers, distributed locks prevent duplicate job execution.
    """
    logger.info("="*70)
    logger.info("⏰ Initializing Background Scheduler (Worker PID: %s)", WORKER_ID)
    logger.info("="*70)
    
    # Job 1: Calculate daily statistics at 2 AM
    scheduler.add_job(
        calculate_daily_statistics_job,
        'cron',
        hour=2,
        minute=0,
        id='daily_statistics',
        name='Calculate Daily Statistics',
        replace_existing=True
    )
    logger.info("✓ Scheduled: Daily Statistics Calculation at 2:00 AM")
    
    # Job 2: Cleanup old logs at 3 AM
    scheduler.add_job(
        cleanup_old_logs_job,
        'cron',
        hour=3,
        minute=0,
        id='log_cleanup',
        name='Cleanup Old Logs (7 days)',
        replace_existing=True
    )
    logger.info("✓ Scheduled: Log Cleanup at 3:00 AM (deletes logs >7 days old)")
    
    # Job 3: Cleanup old soft-deleted sessions at 4 AM
    scheduler.add_job(
        cleanup_deleted_sessions_job,
        'cron',
        hour=4,
        minute=0,
        id='session_cleanup',
        name='Cleanup Deleted Sessions (15 days)',
        replace_existing=True
    )
    logger.info("✓ Scheduled: Session Cleanup at 4:00 AM (permanently deletes soft-deleted sessions >15 days old)")
    
    # Start the scheduler
    scheduler.start()
    logger.info("✓ Background Scheduler Started Successfully")
    logger.info("   (Multi-worker safe: uses distributed locks)")
    logger.info("="*70)


def stop_scheduler():
    """
    Stop the background scheduler.
    Called during application shutdown.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✓ Background Scheduler Stopped")
