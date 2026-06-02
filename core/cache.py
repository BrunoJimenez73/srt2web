# File: core/cache.py
import copy
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar


class LRUCache:
    """LRU cache con TTL (Time To Live), thread-safe y preventivo contra mutaciones."""

    def __init__(self, maxsize: int = 500, ttl_seconds: int = 60):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[Any, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        with self._lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    self.cache.move_to_end(key)
                    return copy.deepcopy(value)
                else:
                    del self.cache[key]
            return None

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.maxsize:
                self.cache.popitem(last=False)
            self.cache[key] = (copy.deepcopy(value), time.time())

    def clear(self) -> None:
        with self._lock:
            self.cache.clear()

    def invalidate(self, key: Any) -> None:
        with self._lock:
            self.cache.pop(key, None)


class APICache:
    """
    Named caches for API endpoints.

    Provides per-endpoint caching with configurable TTLs
    and bulk invalidation by endpoint name.
    """

    def __init__(self) -> None:
        self._caches: dict[str, LRUCache] = {}
        self._lock = threading.Lock()

    def _get_or_create(self, name: str, ttl_seconds: int, maxsize: int = 1) -> LRUCache:
        with self._lock:
            if name not in self._caches:
                self._caches[name] = LRUCache(maxsize=maxsize, ttl_seconds=ttl_seconds)
            return self._caches[name]

    def get(self, name: str, key: str = "default") -> Any | None:
        with self._lock:
            cache = self._caches.get(name)
        if cache is None:
            return None
        return cache.get(key)

    def set(self, name: str, value: Any, key: str = "default") -> None:
        with self._lock:
            cache = self._caches.get(name)
        if cache is not None:
            cache.set(key, value)

    def ensure(self, name: str, ttl_seconds: int, maxsize: int = 1) -> None:
        self._get_or_create(name, ttl_seconds, maxsize)

    def invalidate(self, name: str) -> None:
        with self._lock:
            cache = self._caches.get(name)
        if cache is not None:
            cache.clear()

    def invalidate_all(self) -> None:
        with self._lock:
            for cache in self._caches.values():
                cache.clear()


api_cache = APICache()


# ── Cached decorator for FastAPI endpoints ───────────────────────────────

F = TypeVar("F", bound=Callable[..., Any])


def cached(name: str, ttl_seconds: int = 2, maxsize: int = 1) -> Callable[[F], F]:
    """
    Decorador que cachea la respuesta de un endpoint.

    Args:
        name: Nombre del cache (ej: "status", "config")
        ttl_seconds: Tiempo de vida del cache en segundos
        maxsize: Máximo de entradas cacheadas

    Uso:
        @router.get("/status")
        @cached("status", ttl_seconds=1)
        async def get_status():
            ...
    """
    api_cache.ensure(name, ttl_seconds, maxsize)

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cached_value = api_cache.get(name)
            if cached_value is not None:
                return cached_value
            result = await func(*args, **kwargs)
            api_cache.set(name, result)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def invalidate_cache(name: str) -> None:
    """Invalidate a named cache (call from write endpoints)."""
    api_cache.invalidate(name)
