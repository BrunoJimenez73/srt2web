"""
Tests for core.ffmpeg_pool — FFmpeg concurrency pool.

F165: Covers pool lifecycle, acquire/release, concurrency limits,
shutdown, singleton access, and stats.
"""

import threading
import time

import pytest

from core.ffmpeg_pool import FFmpegPool, get_pool, shutdown_pool


@pytest.mark.unit
class TestFFmpegPool:
    """Unit tests for FFmpegPool."""

    def test_acquire_and_release(self):
        pool = FFmpegPool(max_size=2)
        assert pool.acquire("ffmpeg", "job1")
        stats = pool.get_stats()
        assert stats["active_slots"] == 1
        assert stats["free_slots"] == 1
        pool.release("job1")
        stats = pool.get_stats()
        assert stats["active_slots"] == 0
        assert stats["free_slots"] == 2

    def test_acquire_respects_max_size(self):
        pool = FFmpegPool(max_size=2)
        assert pool.acquire("ffmpeg", "j1")
        assert pool.acquire("ffmpeg", "j2")
        assert not pool.acquire("ffmpeg", "j3", timeout=0.1)
        pool.release("j1")
        assert pool.acquire("ffmpeg", "j3", timeout=0.1)
        pool.release("j2")
        pool.release("j3")

    def test_release_unknown_job_is_noop(self):
        pool = FFmpegPool(max_size=2)
        pool.release("nonexistent")
        stats = pool.get_stats()
        assert stats["active_slots"] == 0

    def test_get_stats(self):
        pool = FFmpegPool(max_size=4)
        stats = pool.get_stats()
        assert stats["total_slots"] == 4
        assert stats["active_slots"] == 0
        assert stats["free_slots"] == 4
        assert stats["active_jobs"] == []

    def test_concurrent_acquire_release(self):
        pool = FFmpegPool(max_size=3)
        acquired = []

        def worker(i):
            if pool.acquire("ffmpeg", f"job{i}", timeout=5):
                acquired.append(i)
                time.sleep(0.05)
                pool.release(f"job{i}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(acquired) == 6
        stats = pool.get_stats()
        assert stats["active_slots"] == 0

    def test_shutdown_releases_active_jobs(self):
        pool = FFmpegPool(max_size=3)
        pool.acquire("ffmpeg", "j1")
        pool.acquire("ffmpeg", "j2")
        pool.shutdown()
        stats = pool.get_stats()
        assert stats["active_slots"] == 0

    def test_shutdown_allows_reacquire(self):
        pool = FFmpegPool(max_size=2)
        pool.acquire("ffmpeg", "j1")
        pool.shutdown()
        pool2 = FFmpegPool(max_size=2)
        assert pool2.acquire("ffmpeg", "new_job")
        pool2.release("new_job")


@pytest.mark.unit
class TestFFmpegPoolSingleton:
    """Tests for the global pool singleton."""

    def setup_method(self):
        shutdown_pool()

    def teardown_method(self):
        shutdown_pool()

    def test_get_pool_creates_singleton(self):
        pool1 = get_pool()
        pool2 = get_pool()
        assert pool1 is pool2

    def test_shutdown_pool_clears_singleton(self):
        pool1 = get_pool()
        shutdown_pool()
        pool2 = get_pool()
        assert pool1 is not pool2
