"""
Reminder Scheduler

Uses APScheduler to periodically check and process due reminders.
Starts on application startup and runs continuously.
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.settings import settings
from app.db import async_session_maker
from app.services.reminder_service import process_due_reminders

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


async def _process_reminders_job():
    """Job that processes due reminders."""
    try:
        async with async_session_maker() as db:
            processed = await process_due_reminders(db)
            if processed > 0:
                logger.info(f"Reminder scheduler tick: processed {processed} reminders")
    except Exception as e:
        logger.error(f"Error in reminder scheduler job: {e}")


def start_reminder_scheduler():
    """Start the reminder scheduler."""
    global _scheduler
    
    if not settings.REMINDER_SCHEDULER_ENABLED:
        logger.info("Reminder scheduler is disabled via settings")
        return
    
    if _scheduler is not None and _scheduler.running:
        logger.warning("Reminder scheduler already running")
        return
    
    _scheduler = AsyncIOScheduler()
    
    # Add job to process reminders every N seconds
    _scheduler.add_job(
        _process_reminders_job,
        trigger=IntervalTrigger(seconds=settings.REMINDER_CHECK_INTERVAL_SECONDS),
        id="process_due_reminders",
        name="Process due reminders",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping executions
        coalesce=True  # If multiple runs missed, only run once
    )
    
    _scheduler.start()
    logger.info(
        f"Reminder scheduler started - checking every {settings.REMINDER_CHECK_INTERVAL_SECONDS} seconds"
    )


def stop_reminder_scheduler():
    """Stop the reminder scheduler gracefully."""
    global _scheduler
    
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Reminder scheduler stopped")
    
    _scheduler = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the current scheduler instance."""
    return _scheduler


@asynccontextmanager
async def scheduler_lifespan():
    """Context manager for scheduler lifecycle."""
    start_reminder_scheduler()
    try:
        yield
    finally:
        stop_reminder_scheduler()
