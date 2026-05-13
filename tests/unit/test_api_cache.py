import json
from unittest.mock import Mock

import pytest
from fastapi import Request, Response

from core.cache import APICache, LRUCache, api_cache
from server.cache_middleware import cached, invalidate_cache


@pytest.fixture(autouse=True)
def clear_api_cache():
    api_cache.invalidate_all()
    yield


class TestLRUCache:
    def test_get_set(self) -> None:
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        cache.set("a", 1)
        assert cache.get("a") == 1

    def test_expiry(self) -> None:
        cache = LRUCache(maxsize=10, ttl_seconds=0)
        cache.set("a", 1)
        assert cache.get("a") is None

    def test_maxsize_eviction(self) -> None:
        cache = LRUCache(maxsize=2, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("c") is not None

    def test_lru_move_to_end(self) -> None:
        cache = LRUCache(maxsize=2, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")
        cache.set("c", 3)
        assert cache.get("a") is not None
        assert cache.get("b") is None

    def test_invalidate(self) -> None:
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        cache.set("a", 1)
        cache.invalidate("a")
        assert cache.get("a") is None

    def test_clear(self) -> None:
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None


class TestAPICache:
    def test_ensure_and_get(self) -> None:
        ac = APICache()
        ac.ensure("test", ttl_seconds=60)
        assert ac.get("test") is None

    def test_set_and_get(self) -> None:
        ac = APICache()
        ac.ensure("test", ttl_seconds=60)
        ac.set("test", {"data": 42})
        assert ac.get("test") == {"data": 42}

    def test_invalidate(self) -> None:
        ac = APICache()
        ac.ensure("test", ttl_seconds=60)
        ac.set("test", 1)
        ac.invalidate("test")
        assert ac.get("test") is None

    def test_invalidate_all(self) -> None:
        ac = APICache()
        ac.ensure("a", ttl_seconds=60)
        ac.ensure("b", ttl_seconds=60)
        ac.set("a", 1)
        ac.set("b", 2)
        ac.invalidate_all()
        assert ac.get("a") is None
        assert ac.get("b") is None

    def test_multiple_keys(self) -> None:
        ac = APICache()
        ac.ensure("test", ttl_seconds=60, maxsize=10)
        ac.set("test", 1, key="k1")
        ac.set("test", 2, key="k2")
        assert ac.get("test", key="k1") == 1
        assert ac.get("test", key="k2") == 2


class TestCacheMiddleware:
    @pytest.mark.asyncio
    async def test_cached_endpoint_returns_cached_value(self) -> None:
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/status"
        mock_request.url.query = ""

        call_count = 0

        @cached("status")
        async def my_endpoint(request) -> Any:
            nonlocal call_count
            call_count += 1
            return {"status": "ok"}

        result1 = await my_endpoint(mock_request)
        result2 = await my_endpoint(mock_request)

        assert call_count == 1
        if isinstance(result1, Response):
            data = json.loads(result1.body)
            assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_invalidation_clears_cache(self) -> None:
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/config"
        mock_request.url.query = ""

        call_count = 0

        @cached("config")
        async def my_endpoint(request) -> Any:
            nonlocal call_count
            call_count += 1
            return {"version": 1}

        await my_endpoint(mock_request)
        invalidate_cache("config")
        await my_endpoint(mock_request)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_health_endpoint_cached(self) -> None:
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/health"
        mock_request.url.query = ""

        call_count = 0

        @cached("health")
        async def health_endpoint() -> Any:
            nonlocal call_count
            call_count += 1
            return {"status": "ok"}

        await health_endpoint()
        await health_endpoint()
        assert call_count == 1
