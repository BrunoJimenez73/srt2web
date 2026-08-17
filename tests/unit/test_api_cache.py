"""
Tests for API caching layer.
"""

from core.cache import LRUCache, api_cache


class TestLRUCache:
    def test_get_set(self) -> None:
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_missing_key(self) -> None:
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_eviction(self) -> None:
        cache = LRUCache(maxsize=2, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # Should evict "a"
        assert cache.get("a") is None  # evicted
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_clear(self) -> None:
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        cache.set("a", 1)
        cache.clear()
        assert cache.get("a") is None

    def test_ttl_expiry(self) -> None:
        import time

        cache = LRUCache(maxsize=10, ttl_seconds=0)  # 0 TTL = instant expiry
        cache.set("a", 1)
        time.sleep(0.01)
        assert cache.get("a") is None  # expired


class TestAPICache:
    def test_get_set(self) -> None:
        api_cache.ensure("test", ttl_seconds=60)
        api_cache.set("test", {"data": 42})
        assert api_cache.get("test") == {"data": 42}

    def test_missing_cache(self) -> None:
        assert api_cache.get("nonexistent") is None

    def test_invalidate(self) -> None:
        api_cache.ensure("temp", ttl_seconds=60)
        api_cache.set("temp", "value")
        api_cache.invalidate("temp")
        assert api_cache.get("temp") is None

    def test_invalidate_all(self) -> None:
        api_cache.ensure("a", ttl_seconds=60)
        api_cache.ensure("b", ttl_seconds=60)
        api_cache.set("a", 1)
        api_cache.set("b", 2)
        api_cache.invalidate_all()
        assert api_cache.get("a") is None
        assert api_cache.get("b") is None


class TestCachedDecorator:
    def test_decorator_caches(self) -> None:
        """Verify cached decorator stores and returns cached value."""
        from core.cache import cached

        call_count = 0

        @cached("cached_test", ttl_seconds=60)
        async def my_func() -> dict:
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        import asyncio

        r1 = asyncio.run(my_func())
        r2 = asyncio.run(my_func())
        assert r1 == {"count": 1}  # First call
        assert r2 == {"count": 1}  # Cached - count should not increment

    def test_invalidate_clears(self) -> None:
        """Verify invalidate_cache clears the cached value."""
        from core.cache import cached, invalidate_cache

        call_count = 0

        @cached("invalidate_test", ttl_seconds=60)
        async def my_func() -> dict:
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        import asyncio

        r1 = asyncio.run(my_func())
        invalidate_cache("invalidate_test")
        r2 = asyncio.run(my_func())
        assert r1 == {"count": 1}
        assert r2 == {"count": 2}  # Should increment after invalidation

    def test_stampede_protection(self) -> None:
        """Verify concurrent requests only execute the function once."""
        import asyncio

        from core.cache import cached

        call_count = 0

        @cached("stampede_test", ttl_seconds=60)
        async def slow_func() -> dict:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # Simulate slow computation
            return {"count": call_count}

        async def run_concurrent() -> list[dict]:
            r1, r2, r3 = await asyncio.gather(slow_func(), slow_func(), slow_func())
            return [r1, r2, r3]

        results = asyncio.run(run_concurrent())
        assert call_count == 1  # Only one actual execution
        for r in results:
            assert r == {"count": 1}  # All get the same result

    def test_stampede_after_expiry(self) -> None:
        """Verify single-flight also works after cache expiry."""
        import asyncio

        from core.cache import cached

        call_count = 0

        @cached("stampede_expiry_test", ttl_seconds=0)
        async def slow_func() -> dict:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return {"count": call_count}

        # First call populates cache (immediately expires with ttl=0)
        r1 = asyncio.run(slow_func())
        assert call_count == 1

        # Concurrent calls after expiry
        async def run_concurrent() -> list[dict]:
            r2, r3 = await asyncio.gather(slow_func(), slow_func())
            return [r2, r3]

        r2, r3 = asyncio.run(run_concurrent())
        assert call_count == 2  # Only one new execution
        assert r2 == {"count": 2}
        assert r3 == {"count": 2}
