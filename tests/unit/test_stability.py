"""
Tests for Circuit Breaker implementation.
"""

import pytest
import time
from unittest.mock import MagicMock, patch


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class."""

    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in closed state."""
        from core.module_base import CircuitBreaker

        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.can_execute() is True

    def test_records_success(self):
        """Test that success resets failure count."""
        from core.module_base import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2

        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == "closed"

    def test_opens_after_threshold(self):
        """Test that circuit opens after reaching failure threshold."""
        from core.module_base import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"

        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False

    def test_half_open_after_timeout(self):
        """Test that circuit transitions to half-open after timeout."""
        from core.module_base import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, timeout=0.1)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.15)
        assert cb.state == "half_open"
        assert cb.can_execute() is True

    def test_closes_after_half_open_successes(self):
        """Test that circuit closes after successful calls in half-open state."""
        from core.module_base import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, timeout=0.1, half_open_max_calls=2)

        cb.record_failure()
        cb.record_failure()

        time.sleep(0.15)
        assert cb.state == "half_open"

        cb.record_success()
        cb.record_success()
        assert cb.state == "closed"

    def test_force_reset(self):
        """Test force reset functionality."""
        from core.module_base import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        cb.force_reset()
        assert cb.state == "closed"
        assert cb._failure_count == 0
        assert cb.can_execute() is True

    def test_half_open_max_calls(self):
        """Test that circuit opens after threshold and recovers."""
        from core.module_base import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, timeout=0.1, half_open_max_calls=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.15)
        assert cb.state == "half_open"
        assert cb.can_execute() is True

        cb.record_failure()
        assert cb.state == "open"

    def test_concurrent_access(self):
        """Test thread safety of circuit breaker."""
        import threading
        from core.module_base import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=100)

        def record_failures():
            for _ in range(50):
                cb.record_failure()

        threads = [threading.Thread(target=record_failures) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cb._failure_count == 200


class TestRetryStrategy:
    """Test suite for RetryStrategy class."""

    def test_successful_execution_no_retry(self):
        """Test that successful execution doesn't retry."""
        from core.module_base import RetryStrategy

        retry = RetryStrategy(max_retries=3)
        func = MagicMock(return_value="success")

        result = retry.execute(func)

        assert result == "success"
        assert func.call_count == 1

    def test_retries_on_failure(self):
        """Test that retries happen on failure."""
        from core.module_base import RetryStrategy

        retry = RetryStrategy(max_retries=3, base_delay=0.01)
        func = MagicMock(
            side_effect=[Exception("fail 1"), Exception("fail 2"), "success"]
        )

        result = retry.execute(func)

        assert result == "success"
        assert func.call_count == 3

    def test_exhausts_retries(self):
        """Test that all retries are exhausted."""
        from core.module_base import RetryStrategy

        retry = RetryStrategy(max_retries=2, base_delay=0.01)
        func = MagicMock(side_effect=Exception("always fails"))

        with pytest.raises(Exception) as exc_info:
            retry.execute(func)

        assert str(exc_info.value) == "always fails"
        assert func.call_count == 3

    def test_is_recoverable_check(self):
        """Test that is_recoverable callback is respected."""
        from core.module_base import RetryStrategy

        retry = RetryStrategy(max_retries=3, base_delay=0.01)
        func = MagicMock(side_effect=Exception("timeout"))
        is_recoverable = MagicMock(return_value=False)

        with pytest.raises(Exception):
            retry.execute(func, is_recoverable=is_recoverable)

        assert func.call_count == 1
        is_recoverable.assert_called_once()

    def test_delay_increases_exponentially(self):
        """Test that delays increase exponentially."""
        from core.module_base import RetryStrategy

        retry = RetryStrategy(max_retries=3, base_delay=0.1, exponential_base=2.0)

        assert retry.get_delay(0) == 0.1
        assert retry.get_delay(1) == 0.2
        assert retry.get_delay(2) == 0.4
        assert retry.get_delay(3) == 0.8

    def test_max_delay_respected(self):
        """Test that max_delay is respected."""
        from core.module_base import RetryStrategy

        retry = RetryStrategy(max_retries=5, base_delay=1.0, max_delay=5.0)

        assert retry.get_delay(0) == 1.0
        assert retry.get_delay(2) == 4.0
        assert retry.get_delay(3) == 5.0
        assert retry.get_delay(4) == 5.0


class TestIsRecoverableError:
    """Test suite for is_recoverable_error function."""

    def test_timeout_is_recoverable(self):
        """Test that timeout errors are recoverable."""
        from core.module_base import is_recoverable_error

        assert is_recoverable_error(Exception("timeout occurred")) is True
        assert is_recoverable_error(Exception("Connection timed out")) is True

    def test_ffmpeg_is_recoverable(self):
        """Test that FFmpeg errors are recoverable."""
        from core.module_base import is_recoverable_error

        assert is_recoverable_error(Exception("ffmpeg error")) is True
        assert is_recoverable_error(Exception("FFmpeg process died")) is True

    def test_stream_is_recoverable(self):
        """Test that stream errors are recoverable."""
        from core.module_base import is_recoverable_error

        assert is_recoverable_error(Exception("stream closed")) is True
        assert is_recoverable_error(Exception("connection lost")) is True

    def test_memory_is_recoverable(self):
        """Test that memory errors are recoverable."""
        from core.module_base import is_recoverable_error

        assert is_recoverable_error(Exception("out of memory")) is True

    def test_generic_error_not_recoverable(self):
        """Test that generic errors are not recoverable."""
        from core.module_base import is_recoverable_error

        assert is_recoverable_error(Exception("something went wrong")) is False
        assert is_recoverable_error(Exception("configuration invalid")) is False


class TestMemoryManager:
    """Test suite for MemoryManager class."""

    def test_initialization(self):
        """Test MemoryManager initialization."""
        from core.module_base import MemoryManager

        mm = MemoryManager(max_memory_mb=4096, gc_threshold_mb=2048)

        assert mm.max_memory_mb == 4096
        assert mm.gc_threshold_mb == 2048
        assert mm.check_interval == 10

    def test_should_check_interval(self):
        """Test that check only runs at interval."""
        from core.module_base import MemoryManager

        mm = MemoryManager(check_interval=5)

        assert mm.should_check() is True

        mm._chunk_counter = 3
        assert mm.should_check() is False

        mm._chunk_counter = 5
        assert mm.should_check() is True

    def test_check_without_psutil(self):
        """Test check when psutil is not available."""
        from core.module_base import MemoryManager

        mm = MemoryManager()

        with patch.dict("sys.modules", {"psutil": None}):
            info = mm.check()

        assert info.get("psutil_not_available") is True

    def test_check_returns_memory_info(self):
        """Test that check returns memory information."""
        from core.module_base import MemoryManager

        mm = MemoryManager()

        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 1024
        mock_process.memory_percent.return_value = 25.0

        with patch("psutil.Process", return_value=mock_process):
            info = mm.check()

        assert "memory_mb" in info
        assert "memory_percent" in info
        assert info["memory_mb"] == 1024.0

    def test_gc_triggered_above_threshold(self):
        """Test that GC is triggered when memory exceeds threshold."""
        from core.module_base import MemoryManager

        mm = MemoryManager(gc_threshold_mb=100, check_interval=1)
        mm._last_gc_time = 0

        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 250 * 1024 * 1024
        mock_process.memory_percent.return_value = 50.0

        with patch("psutil.Process", return_value=mock_process):
            info = mm.check()

        assert info["gc_triggered"] is True
        assert info["above_threshold"] is True

    def test_gc_not_triggered_within_interval(self):
        """Test that GC is not triggered if within minimum interval."""
        from core.module_base import MemoryManager

        mm = MemoryManager(gc_threshold_mb=100, check_interval=1)
        mm._last_gc_time = time.time()

        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 250 * 1024 * 1024
        mock_process.memory_percent.return_value = 50.0

        with patch("psutil.Process", return_value=mock_process):
            info = mm.check()

        assert info["gc_triggered"] is False
