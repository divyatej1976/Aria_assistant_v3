"""Condense long uploads in the background so "summarize this" covers the whole file.

The work runs as a "digest" job (app.services.jobs): any worker can take it, and it saves its
place section by section, so a long book resumes where it stopped instead of starting over.
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Job, Resource
from app.services.condense import FITS_CHARS, condense

logger = logging.getLogger(__name__)


def needs_digest(resource: Resource | None) -> bool:
    return (resource is not None and resource.processing_status == "READY" and not resource.digest
            and len(resource.source_text or "") > FITS_CHARS)


def schedule_digest(db: Session, *, owner_id: UUID, resource_id: UUID) -> None:
    """Queue a digest for a long, ready file; short files need none."""
    from app.services import jobs

    resource = db.get(Resource, resource_id)
    if resource is not None and resource.owner_id == owner_id and needs_digest(resource):
        jobs.enqueue(db, kind="digest", owner_id=owner_id, target_id=resource_id)


async def wait_for_digest(db: Session, resource_ids, *, timeout: float = 40.0) -> None:
    """Let a "summarize this" asked right after upload wait for the whole-file digest."""
    from app.db.session import release_connection

    ids = list(resource_ids)
    for _ in range(int(timeout)):
        busy = db.scalar(select(Job.id).where(Job.kind == "digest", Job.target_id.in_(ids),
                                              Job.status.in_(["queued", "running"])).limit(1))
        db.rollback()  # end the read so the next poll sees the worker's commits
        if busy is None:
            return
        release_connection(db)
        await asyncio.sleep(1)


def build_digest(db: Session, job, progress) -> None:
    """The "digest" job: condense the whole file, resuming from saved sections."""
    from app.ai.registry import get_llm_provider_for_owner

    resource = db.get(Resource, job.target_id)
    if resource is None or resource.owner_id != job.owner_id or not needs_digest(resource):
        return
    provider = get_llm_provider_for_owner(db, owner_id=job.owner_id)
    if provider is None:
        return
    title, text = resource.title, resource.source_text or ""
    db.rollback()  # no transaction held open while the AI works
    digest = asyncio.run(condense(provider, title=title, text=text, progress=progress))
    resource = db.get(Resource, job.target_id, populate_existing=True)
    if resource is not None:
        resource.digest = digest
        db.commit()
    logger.info("digest ready resource_id=%s chars=%d->%d", job.target_id, len(text), len(digest))
