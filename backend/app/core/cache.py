"""In-process TTL cache utility.

Provides a small thread-safe LRU cache with per-key TTL expiry. It is NOT yet
wired into request paths: the Phase 12.6 load baseline shows p95 latency under
200 ms at moderate concurrency, so per the "scaling decisions supported by
actual usage evidence" gate, Redis and even in-process caching remain deferred
until sustained production traffic justifies them. This module exists so a
hot, low-volatility read can opt in cheaply when that evidence arrives.
"""

import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TTLCache:
    def __init__(self, *, maxsize: int = 256, ttl_seconds: float = 60) -> None:
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._data: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: K) -> V | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: K, value: V) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + self._ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def ttl_cache(ttl_seconds: float, maxsize: int = 256) -> Callable:
    """Decorator caching a single-argument callable in a TTLCache."""

    def decorator(func: Callable[[K], V]) -> Callable[[K], V]:
        cache = TTLCache(maxsize=maxsize, ttl_seconds=ttl_seconds)

        def wrapper(key: K) -> V:
            cached = cache.get(key)
            if cached is not None:
                return cached
            value = func(key)
            cache.set(key, value)
            return value

        return wrapper

    return decorator
