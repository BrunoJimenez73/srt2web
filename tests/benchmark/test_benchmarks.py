"""
Performance benchmarks using pytest-benchmark.

Run with:
    pip install pytest-benchmark
    python -m pytest tests/benchmark/test_benchmarks.py -v --benchmark-only
    python -m pytest tests/benchmark/test_benchmarks.py -v --benchmark-compare
"""

import json
import threading

import pytest

try:
    import pytest_benchmark  # noqa: F401

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False

pytestmark = pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not installed")


@pytest.mark.benchmark
class TestFFmpegPoolBenchmarks:
    """Benchmarks for FFmpegPool concurrency primitives."""

    def test_acquire_release_throughput(self, benchmark):
        from core.ffmpeg_pool import FFmpegPool

        pool = FFmpegPool(max_size=16)

        def cycle():
            pool.acquire("ffmpeg", "bench-job")
            pool.release("bench-job")

        benchmark(cycle)

    def test_concurrent_acquire_release(self, benchmark):
        from core.ffmpeg_pool import FFmpegPool

        pool = FFmpegPool(max_size=8)
        barrier = threading.Barrier(8)

        def worker():
            barrier.wait()
            pool.acquire("ffmpeg", f"job-{threading.current_thread().ident}")
            pool.release(f"job-{threading.current_thread().ident}")

        def run_all():
            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        benchmark(run_all)


@pytest.mark.benchmark
class TestSubtitleSyncBenchmarks:
    """Benchmarks for subtitle drift monitor blending."""

    def test_check_sync_blending(self, benchmark):
        from core.subtitle_sync_monitor import SubtitleSyncMonitor

        monitor = SubtitleSyncMonitor(
            correction_threshold_ms=500,
            enable_drift_detection=True,
            drift_history_size=100,
        )
        for i in range(50):
            monitor.check_sync(audio_wall_clock_ms=1000 * i, first_cue_media_ms=1000 * i + 10)

        def blend():
            monitor.check_sync(audio_wall_clock_ms=51000, first_cue_media_ms=51005)

        benchmark(blend)


@pytest.mark.benchmark
class TestConfigSerializationBenchmarks:
    """Benchmarks for config serialization path."""

    def test_config_to_dict(self, benchmark):
        from core.config_manager import ConfigManager

        cm = ConfigManager()
        cm.load_config()
        benchmark(cm.to_dict)

    def test_config_json_roundtrip(self, benchmark):
        from core.config_manager import ConfigManager

        cm = ConfigManager()
        cm.load_config()

        def roundtrip():
            d = cm.to_dict()
            json.dumps(d)

        benchmark(roundtrip)
