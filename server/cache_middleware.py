"""
Cache middleware for API endpoints.

Provides a decorator to cache FastAPI endpoint responses
and a function to invalidate caches when data changes.
"""

import functools
import hashlib
import json
from typing import Any, Awaitable, Callable

from fastapi import Request, Response

from core.cache import api_cache

CACHE_CONFIG: dict[str, dict[str, int]] = {
    "status": {"ttl": 1},
    "config": {"ttl": 5},
    "health": {"ttl": 10},
}

AsyncFunc = Callable[..., Awaitable[Any]]


def _make_key(request: Request) -> str:
    path = request.url.path
    query = request.url.query
    raw = f"{path}?{query}" if query else path
    return hashlib.md5(raw.encode()).hexdigest()


def cached(endpoint_name: str) -> Callable[[AsyncFunc], AsyncFunc]:
    cfg = CACHE_CONFIG.get(endpoint_name, {"ttl": 5})
    api_cache.ensure(endpoint_name, cfg["ttl"])

    def decorator(func: AsyncFunc) -> AsyncFunc:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            key = _make_key(request) if request else "default"
            cached = api_cache.get(endpoint_name, key)
            if cached is not None:
                return Response(
                    content=json.dumps(cached),
                    media_type="application/json",
                    headers={"Cache-Control": f"public, max-age={cfg['ttl']}"},
                )

            result = await func(*args, **kwargs)
            api_cache.set(endpoint_name, result, key)
            return result

        return wrapper

    return decorator


def invalidate_cache(endpoint_name: str) -> None:
    api_cache.invalidate(endpoint_name)