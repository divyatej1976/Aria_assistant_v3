"""Background jobs: any number run at once, each on its own worker, and long ones resume.

A worker claims one queued job with a row lock (FOR UPDATE SKIP LOCKED), so two workers
never take the same job, and holds a lease while it runs. A worker that dies, or one that
runs out of time and hands over (`Continue`), leaves the job claimable again; its saved
`progress` lets the next worker pick up where it stopped.
"""

import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Job

logger = logging.getLogger(__name__)

# Longer than one serverless request (300 s), so a live worker is never claimed twice.
LEASE_SECONDS = 360
MAX_ATTEMPTS = 4  # crashes only; a job that hands over with Continue does not use one up


class Continue(Exception):
    """The worker saved progress and ran out of time; run the job again soon."""


class Progress:
    """A job's saved state. `save()` commits it at once, outside the worker's transaction."""

    def __init__(self, bind, job_id: UUID, data: dict, deadline: float | None) -> None:
        self._bind, self._job_id, self.data, self.deadline = bind, job_id, dict(data or {}), deadline

    def save(self, **changes) -> None:
        self.data.update(changes)
        with Session(self._bind) as db:
            db.execute(update(Job).where(Job.id == self._job_id).values(
                progress=dict(self.data), lease_until=datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS)))
            db.commit()

    def check_time(self) -> None:
        """Hand over before the host stops the request; call between steps, after saving."""
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise Continue()


# kind -> handler(db, job, progress). Registered by the services that own the work.
HANDLERS: dict[str, Callable[[Session, Job, Progress], None]] = {}


def handler(kind: str):
    def register(fn):
        HANDLERS[kind] = fn
        return fn
    return register


def _runnable(now: datetime):
    return or_(Job.status == "queued", and_(Job.status == "running", Job.lease_until < now))


def enqueue(db: Session, *, kind: str, owner_id: UUID, target_id: UUID, start: bool = True) -> Job:
    """Queue work once: an unfinished job for the same target is reused."""
    job = db.scalar(select(Job).where(Job.kind == kind, Job.target_id == target_id,
                                      Job.status.in_(["queued", "running"])))
    if job is None:
        job = Job(kind=kind, owner_id=owner_id, target_id=target_id, status="queued", progress={})
        db.add(job)
    db.commit()
    db.refresh(job)
    if start:
        kick(db.get_bind())
    return job


def claim(db: Session) -> Job | None:
    """Take the oldest runnable job, skipping rows another worker has locked."""
    for _ in range(5):  # another worker may win a row between our read and update; try the next
        now = datetime.now(UTC)
        job_id = db.scalar(select(Job.id).where(_runnable(now)).order_by(Job.created_at)
                           .limit(1).with_for_update(skip_locked=True))
        if job_id is None:
            db.rollback()
            return None
        claimed = db.execute(update(Job).where(Job.id == job_id, _runnable(now)).values(
            status="running", attempts=Job.attempts + 1, lease_until=now + timedelta(seconds=LEASE_SECONDS),
        ).execution_options(synchronize_session=False))
        db.commit()
        if claimed.rowcount == 1:
            return db.get(Job, job_id, populate_existing=True)
    return None


def run_one(db: Session) -> bool:
    """Claim and run one job. False when there was nothing to do."""
    import app.services.job_handlers  # noqa: F401  (registers the handlers)

    job = claim(db)
    if job is None:
        return False
    budget = get_settings().aria_job_budget_seconds
    progress = Progress(db.get_bind(), job.id, job.progress, time.monotonic() + budget if budget else None)
    job_id, attempts = job.id, job.attempts
    try:
        HANDLERS[job.kind](db, job, progress)
    except Continue:
        db.rollback()
        # Handing over is not a failure: give the attempt back and let the next worker resume.
        db.execute(update(Job).where(Job.id == job_id).values(
            status="queued", lease_until=None, attempts=Job.attempts - 1))
        db.commit()
        kick(db.get_bind())
        return True
    except Exception as exc:
        db.rollback()
        logger.warning("job failed kind=%s attempt=%s", job.kind, attempts, exc_info=True)
        failed = attempts >= MAX_ATTEMPTS
        db.execute(update(Job).where(Job.id == job_id).values(
            status="failed" if failed else "queued", lease_until=None, error=str(exc)[:500]))
        db.commit()
        return True
    db.execute(update(Job).where(Job.id == job_id).values(status="done", lease_until=None))
    db.commit()
    return True


def runnable_count(db: Session) -> int:
    return len(db.scalars(select(Job.id).where(_runnable(datetime.now(UTC))).limit(50)).all())


def kick(bind, workers: int = 1) -> None:
    """Start workers now: threads here, or one request each to the host (which scales them out)."""
    settings = get_settings()
    if settings.aria_job_runner == "http" and settings.aria_cron_secret:
        url = settings.aria_public_url.rstrip("/") + "/api/v1/internal/work"
        # Sent inline, not from a thread: a serverless host may freeze threads once the response is out.
        for _ in range(workers):
            _start_remote(url, settings.aria_cron_secret)
        return
    factory = sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)
    for _ in range(workers):
        threading.Thread(target=_drain, args=(factory,), daemon=True, name="aria-job").start()


def _start_remote(url: str, secret: str) -> None:
    import httpx

    try:
        # The worker keeps running after we stop listening; only the start matters here.
        httpx.post(url, headers={"Authorization": f"Bearer {secret}"},
                   timeout=httpx.Timeout(1.5, connect=5))
    except httpx.TimeoutException:
        pass
    except Exception:
        logger.warning("could not start a remote job worker", exc_info=True)


def _drain(factory) -> None:
    with factory() as db:
        try:
            while run_one(db):
                pass
        except Exception:
            logger.exception("job worker stopped")
