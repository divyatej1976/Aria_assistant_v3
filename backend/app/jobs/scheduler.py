"""Background scheduler for recurring jobs.

Jobs run as synchronous functions: APScheduler dispatches them on a worker
thread, so blocking work (SMTP, local TTS, HTTP) never blocks the event loop.
Enabled via ARIA_SCHEDULER_ENABLED (default true); the test suite disables it
so TestClient lifespan starts no background workers.

Each job is guarded by a PostgreSQL advisory lock, so when the backend runs as
multiple replicas only one replica executes a given job at a time. On SQLite
(development) the lock is a no-op and every instance runs the job.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

REMINDERS_LOCK_KEY = 7001
AUDIO_QUEUE_LOCK_KEY = 7002


def _try_advisory_lock(connection, key: int) -> bool:
    from sqlalchemy import text

    if connection.dialect.name != "postgresql":
        # Non-Postgres (e.g., SQLite): single instance, always "acquired".
        return True
    value = connection.execute(
        text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
    ).scalar()
    return bool(value)


def _release_advisory_lock(connection, key: int) -> None:
    from sqlalchemy import text

    try:
        connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
    except Exception:
        pass


def _run_locked(engine, *, key: int, work) -> bool:
    """Run `work` under an advisory lock; returns False when another replica holds it."""
    connection = engine.connect()
    try:
        if not _try_advisory_lock(connection, key):
            return False
        work()
        return True
    finally:
        _release_advisory_lock(connection, key)
        connection.close()


def scheduler_instance() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def run_reminders_job() -> None:
    from app.db.session import SessionLocal, engine
    from app.services.notifications import check_reminders_for_all

    def work() -> None:
        db = SessionLocal()
        try:
            result = check_reminders_for_all(db)
            logger.info("scheduled reminders result=%s", result)
        except Exception:
            logger.exception("scheduled reminders job failed")
        finally:
            db.close()

    if not _run_locked(engine, key=REMINDERS_LOCK_KEY, work=work):
        logger.info("reminders job skipped: another replica holds the lock")
        return


def run_audio_queue_job() -> None:
    from app.db.session import SessionLocal, engine
    from app.services.audio import process_audio_queue

    def work() -> None:
        db = SessionLocal()
        try:
            processed = process_audio_queue(db)
            if processed:
                logger.info("scheduled audio generated %s artifacts", processed)
        except Exception:
            logger.exception("scheduled audio queue job failed")
        finally:
            db.close()

    if not _run_locked(engine, key=AUDIO_QUEUE_LOCK_KEY, work=work):
        logger.info("audio queue job skipped: another replica holds the lock")
        return


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
