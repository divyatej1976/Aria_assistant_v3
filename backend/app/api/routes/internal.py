"""Internal endpoints: a job worker, and the timer tick. Only callers holding ARIA_CRON_SECRET."""

import hmac
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.dependencies import get_db
from app.db.models import AudioArtifact, Job, UploadChunk
from app.services import jobs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/internal", tags=["internal"])
Db = Annotated[Session, Depends(get_db)]


def _authorize(authorization: str | None) -> None:
    secret = get_settings().aria_cron_secret
    given = (authorization or "").removeprefix("Bearer ").encode()
    if not secret or not hmac.compare_digest(given, secret.encode()):
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/work")
def work(db: Db, authorization: str | None = Header(default=None)) -> dict:
    """Run jobs until none are left or this request's time budget is spent."""
    _authorize(authorization)
    import app.services.job_handlers  # noqa: F401  (registers the handlers)

    started, ran = time.monotonic(), 0
    budget = get_settings().aria_job_budget_seconds or 240
    while time.monotonic() - started < budget / 2 and jobs.run_one(db):
        ran += 1
    return {"ran": ran}


@router.post("/tick")
def tick(db: Db, authorization: str | None = Header(default=None)) -> dict:
    """The timer: send due reminders, restart stalled or waiting jobs, tidy up, keep warm."""
    _authorize(authorization)
    import app.services.job_handlers  # noqa: F401
    from app.services.notifications import check_reminders_for_all

    try:
        reminders = check_reminders_for_all(db)
    except Exception:
        db.rollback()
        logger.exception("tick: reminders failed")
        reminders = {}
    # Episodes left waiting without a job (from before jobs existed) get one.
    waiting = db.scalars(select(AudioArtifact).where(AudioArtifact.status.in_(["PENDING", "PROCESSING"]),
                                                     ~AudioArtifact.id.in_(select(Job.target_id).where(
                                                         Job.status.in_(["queued", "running"]))))).all()
    for artifact in waiting:
        jobs.enqueue(db, kind="audio", owner_id=artifact.owner_id, target_id=artifact.id, start=False)
    db.execute(delete(UploadChunk).where(UploadChunk.created_at < datetime.now(UTC) - timedelta(days=1)))
    db.commit()
    pending = jobs.runnable_count(db)
    if pending:
        jobs.kick(db.get_bind(), workers=min(pending, 4))
    return {"reminders": reminders, "jobs_started": min(pending, 4)}
