"""Phase 12.7 in-process TTL cache utility."""

import time

from app.core.cache import TTLCache


def test_cache_returns_stored_value() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=60)
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert cache.get("missing") is None


def test_cache_expires_by_ttl() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=0.05)
    cache.set("a", 1)
    assert cache.get("a") == 1
    time.sleep(0.1)
    assert cache.get("a") is None


def test_cache_evicts_lru_beyond_maxsize() -> None:
    cache: TTLCache[str, int] = TTLCache(maxsize=2, ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_cache_clear() -> None:
    cache: TTLCache[str, int] = TTLCache()
    cache.set("a", 1)
    cache.clear()
    assert cache.get("a") is None
