"""
Background scheduler for automated tasks:
- Daily statistics calculation at 2 AM
- Log cleanup (30 days) at 3 AM daily
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from utils.utils import get_logger
from db.db import SessionLocal
from routes.logs import cleanup_old_logs_job

logger = get_logger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()


def calculate_daily_statistics_job():
    """
    Background job to calculate statistics for yesterday.
    Runs daily at 2 AM.
    """
    try:
        # Import here to avoid circular imports
        from admin.services import SystemStatisticsService
        
        # Calculate statistics for yesterday
        yesterday = (datetime.now() - timedelta(days=1)).date()
        
        db = SessionLocal()
        try:
            logger.info("[Statistics Job] Calculating statistics for %s", yesterday)
            stat = SystemStatisticsService.calculate_statistics_for_date(db, yesterday)
            
            logger.info(
                "[Statistics Job] ✓ Statistics calculated - Date: %s, Users: %s, Active: %s, Sessions: %s, Avg Duration: %.2f min",
                stat.stat_date, stat.total_users, stat.active_users, 
                stat.total_sessions, stat.average_session_duration or 0
            )
        finally:
            db.close()
    
    except Exception as e:
        logger.error("[Statistics Job] Error calculating statistics: %s", str(e))


def start_scheduler():
    """
    Start the background scheduler with all scheduled jobs.
    Called during application startup.
    """
    logger.info("="*70)
    logger.info("⏰ Initializing Background Scheduler")
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
    
    # Start the scheduler
    scheduler.start()
    logger.info("✓ Background Scheduler Started Successfully")
    logger.info("="*70)


def stop_scheduler():
    """
    Stop the background scheduler.
    Called during application shutdown.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✓ Background Scheduler Stopped")
