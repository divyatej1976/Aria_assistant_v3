"""Condense long uploads in the background so "summarize this" covers the whole file."""

import asyncio
import logging
from uuid import UUID

from app.db.models import Resource
from app.services.condense import FITS_CHARS, condense

logger = logging.getLogger(__name__)

# Running digests by resource; also keeps a strong reference so tasks are not collected.
_running: dict[UUID, asyncio.Task] = {}


def schedule_digest(*, owner_id: UUID, resource_id: UUID) -> None:
    """Start condensing after the upload response; a no-op outside an event loop.

    shortcut: the task lives in this process; a restart mid-digest leaves no digest and
    chat falls back to the beginning of the file. Move to the job queue when it matters.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(build_digest(owner_id=owner_id, resource_id=resource_id))
    _running[resource_id] = task
    task.add_done_callback(lambda _: _running.pop(resource_id, None))


async def wait_for_digest(resource_ids, *, timeout: float = 40.0) -> None:
    """Let a "summarize this" asked right after upload wait for the whole-file digest."""
    tasks = [_running[rid] for rid in resource_ids if rid in _running]
    if tasks:
        await asyncio.wait([asyncio.shield(task) for task in tasks], timeout=timeout)


async def build_digest(*, owner_id: UUID, resource_id: UUID) -> str | None:
    from app.ai.registry import get_llm_provider_for_owner
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        resource = db.get(Resource, resource_id)
        if (resource is None or resource.owner_id != owner_id or resource.processing_status != "READY"
                or resource.digest or len(resource.source_text or "") <= FITS_CHARS):
            return None
        provider = get_llm_provider_for_owner(db, owner_id=owner_id)
        if provider is None:
            return None
        title, text = resource.title, resource.source_text or ""
        try:
            digest = await condense(provider, title=title, text=text)
        except Exception:
            logger.warning("digest failed resource_id=%s", resource_id, exc_info=True)
            return None
        resource = db.get(Resource, resource_id)
        if resource is not None:
            resource.digest = digest
            db.commit()
        logger.info("digest ready resource_id=%s chars=%d->%d", resource_id, len(text), len(digest))
        return digest
