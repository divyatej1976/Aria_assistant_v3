"""Rate limiting for authentication endpoints.

Two backends, selected by ARIA_RATE_LIMIT_BACKEND:

- `memory` (default): per-process sliding window. Single-instance only;
  multi-instance deployments must switch to `db` (or an external store).
- `db`: shared fixed-window counters in the `rate_limit_buckets` table.
  Safe across replicas; costs one atomic upsert per limited request.

Active only in production so local development and the test suite are
unaffected.
"""

import datetime
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Protocol

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Memory-backend bounds: eviction sweep starts at 10k keys, hard cap at 11k.
_MAX_MEMORY_KEYS = 10_000
_HARD_CAP_KEYS = 11_000
_EVICT_BATCH = 1_000

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()
# Throttle for the db-backend fail-open warning: a down database must not
# spam one log line per request.
_last_db_warn: float = 0.0
_DB_WARN_INTERVAL_SECONDS = 60.0


class _SessionFactory(Protocol):
    def __call__(self):  # noqa: ANN202 - sessionmaker signature
        ...


def _active() -> bool:
    settings = get_settings()
    return settings.aria_env == "production" and settings.aria_rate_limit_enabled


def allow_request(key: str, *, limit: int, window_seconds: int) -> bool:
    now = time.monotonic()
    with _lock:
        recent = _hits[key]
        while recent and now - recent[0] > window_seconds:
            recent.popleft()
        if len(recent) >= limit:
            return False
        recent.append(now)
        # Evict dead keys so long-lived processes don't grow without bound.
        if len(_hits) > _MAX_MEMORY_KEYS:
            expired = [
                existing
                for existing, times in _hits.items()
                if not times or now - times[-1] > window_seconds
            ]
            for existing in expired[:_EVICT_BATCH]:
                del _hits[existing]
            # A flood of distinct *fresh* keys leaves nothing expired;
            # hard-cap by dropping oldest-inserted keys as a backstop.
            # Bounded iterations: each call adds at most one key, so the
            # excess over the cap is always small.
            for _ in range(min(len(_hits) - _HARD_CAP_KEYS, _EVICT_BATCH)):
                if len(_hits) <= _HARD_CAP_KEYS:
                    break
                _hits.pop(next(iter(_hits)))
        return True


def _naive_utc() -> datetime.datetime:
    """Naive UTC timestamp matching the bucket column's storage semantics."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def allow_request_db(
    key: str,
    *,
    limit: int,
    window_seconds: int,
    session_factory: _SessionFactory | None = None,
) -> bool:
    """Shared fixed-window check; increments are atomic upserts.

    Concurrency-safe across replicas (no read-modify-write): the increment and
    the window reset each happen inside a single SQL statement. `session_factory`
    is injectable for tests; production uses SessionLocal. Fails open on
    infrastructure errors (availability over strictness).
    """
    try:
        if session_factory is None:
            from app.db.session import SessionLocal

            session_factory = SessionLocal
        db = session_factory()
        try:
            from datetime import timedelta

            from sqlalchemy import update

            from app.db.models import RateLimitBucket

            now = _naive_utc()
            cutoff = now - timedelta(seconds=window_seconds)

            # 1) Live window: atomic increment, returns the new count.
            live = db.execute(
                update(RateLimitBucket)
                .where(RateLimitBucket.key == key, RateLimitBucket.window_started_at >= cutoff)
                .values(count=RateLimitBucket.count + 1)
                .returning(RateLimitBucket.count)
            ).scalar_one_or_none()
            db.commit()
            if live is not None:
                return live <= limit

            # 2) Missing or expired window: atomic reset; the WHERE clause
            #    keeps a concurrent replica's fresh window from being stolen.
            #    If we lose that race, treat the request as allowed (bounded
            #    single-call leniency, same as fail-open).
            dialect = db.get_bind().dialect.name
            if dialect == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as dialect_insert
            else:
                from sqlalchemy.dialects.sqlite import insert as dialect_insert
            stmt = dialect_insert(RateLimitBucket).values(
                key=key, window_started_at=now, count=1
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[RateLimitBucket.key],
                set_={"window_started_at": now, "count": 1},
                where=RateLimitBucket.window_started_at < cutoff,
            ).returning(RateLimitBucket.count)
            reset = db.execute(stmt).scalar_one_or_none()
            db.commit()
            return True if reset is None else reset <= limit
        finally:
            db.close()
    except Exception:
        # Fail open (availability over strictness), but loudly: a silent
        # limiter outage is how abuse goes unnoticed. Warning is throttled
        # so a down database doesn't spam one line per request.
        global _last_db_warn
        now_warn = time.monotonic()
        if now_warn - _last_db_warn >= _DB_WARN_INTERVAL_SECONDS:
            _last_db_warn = now_warn
            logger.warning("rate-limit db backend unavailable; failing open", exc_info=True)
        return True


def allow_request_any(
    key: str, *, limit: int, window_seconds: int, session_factory: _SessionFactory | None = None
) -> bool:
    settings = get_settings()
    if getattr(settings, "aria_rate_limit_backend", "memory") == "db":
        return allow_request_db(
            key, limit=limit, window_seconds=window_seconds, session_factory=session_factory
        )
    return allow_request(key, limit=limit, window_seconds=window_seconds)


def rate_limited(limit: int, window_seconds: int) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        if not _active():
            return
        client = request.client.host if request.client is not None else "unknown"
        key = f"{client}:{request.url.path}"
        if not allow_request_any(key, limit=limit, window_seconds=window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

    return dependency
