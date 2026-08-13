"""Background scheduler for recurring jobs.

Jobs run as synchronous functions: APScheduler dispatches them on a worker
thread, so blocking work (SMTP, local TTS, HTTP) never blocks the event loop.
Enabled via ARIA_SCHEDULER_ENABLED (default true); the test suite disables it
so TestClient lifespan starts no background workers.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def scheduler_instance() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def run_reminders_job() -> None:
    from app.db.session import SessionLocal
    from app.services.notifications import check_reminders_for_all

    db = SessionLocal()
    try:
        result = check_reminders_for_all(db)
        logger.info("scheduled reminders result=%s", result)
    except Exception:
        logger.exception("scheduled reminders job failed")
    finally:
        db.close()


def run_audio_queue_job() -> None:
    from app.db.session import SessionLocal
    from app.services.audio import process_audio_queue

    db = SessionLocal()
    try:
        processed = process_audio_queue(db)
        if processed:
            logger.info("scheduled audio generated %s artifacts", processed)
    except Exception:
        logger.exception("scheduled audio queue job failed")
    finally:
        db.close()


def start_scheduler() -> None:
    settings = get_settings()
    if not settings.aria_scheduler_enabled:
        logger.info("Background scheduler disabled (ARIA_SCHEDULER_ENABLED=false)")
        return
    scheduler = scheduler_instance()
    if scheduler.running:
        return
    scheduler.add_job(
        run_reminders_job,
        "interval",
        minutes=settings.aria_reminder_check_interval_minutes,
        id="reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        run_audio_queue_job,
        "interval",
        seconds=settings.aria_audio_queue_interval_seconds,
        id="audio_queue",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Background scheduler started: reminders every %s min, audio queue every %s s",
        settings.aria_reminder_check_interval_minutes,
        settings.aria_audio_queue_interval_seconds,
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
