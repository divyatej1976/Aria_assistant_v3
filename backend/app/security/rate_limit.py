"""In-process sliding-window rate limiting for authentication endpoints.

The limiter is single-instance state; multi-instance deployments should move
this to a shared store (see Phase 12.7) and set ARIA_RATE_LIMIT_ENABLED=false
until then. It is only active in production so local development and the test
suite are unaffected.
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


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
        return True


def rate_limited(limit: int, window_seconds: int) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        if not _active():
            return
        client = request.client.host if request.client is not None else "unknown"
        key = f"{client}:{request.url.path}"
        if not allow_request(key, limit=limit, window_seconds=window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

    return dependency
