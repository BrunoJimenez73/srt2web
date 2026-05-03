"""
Tests for Pipeline Error Handler.

Verifies error classification, recovery decisions, retry logic,
and state management.
"""

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from core.pipeline_error_handler import (
    ErrorCategory,
    ErrorPolicy,
    ErrorRecord,
    ErrorSeverity,
    PipelineErrorHandler,
)


class TestErrorClassification:
    """Test error classification logic."""

    def setup_method(self):
        self.handler = PipelineErrorHandler()

    def test_classify_module_error(self):
        """Module errors should be categorized as module_processing."""
        error = RuntimeError("Module transcriber failed")
        category, severity = self.handler.classify_error(error, module_name="transcriber")
        assert category == ErrorCategory.MODULE_PROCESSING
        assert severity == ErrorSeverity.ERROR

    def test_classify_input_error(self):
        """Input source errors should be categorized correctly."""
        error = ConnectionError("SRT connection lost")
        category, severity = self.handler.classify_error(error)
        assert category == ErrorCategory.INPUT_SOURCE
        assert severity == ErrorSeverity.ERROR

    def test_classify_output_error(self):
        """Output sink errors should be categorized correctly."""
        error = OSError("HLS muxer write failed")
        category, severity = self.handler.classify_error(error)
        assert category == ErrorCategory.OUTPUT_SINK
        assert severity == ErrorSeverity.ERROR

    def test_classify_queue_full(self):
        """Queue full should be warning level."""
        error = Exception("Queue full")
        category, severity = self.handler.classify_error(error)
        assert category == ErrorCategory.QUEUE_FULL
        assert severity == ErrorSeverity.WARNING

    def test_classify_timeout(self):
        """Timeout errors should be detected."""
        error = TimeoutError("Operation timed out")
        category, severity = self.handler.classify_error(error)
        assert category == ErrorCategory.TIMEOUT
        assert severity == ErrorSeverity.ERROR

    def test_classify_resource_exhausted(self):
        """Resource exhaustion should be critical."""
        error = MemoryError("Out of memory")
        category, severity = self.handler.classify_error(error)
        assert category == ErrorCategory.RESOURCE_EXHAUSTED
        assert severity == ErrorSeverity.CRITICAL


class TestRecoverableErrors:
    """Test recoverable error detection."""

    def setup_method(self):
        self.handler = PipelineErrorHandler()

    @pytest.mark.parametrize(
        "error_msg",
        [
            "Connection timeout",
            "Temporary failure",
            "Queue full",
            "Stream interrupted",
            "FFmpeg process failed",
            "Resource temporarily unavailable",
        ],
    )
    def test_recoverable_errors(self, error_msg):
        """Recoverable errors should return True."""
        error = Exception(error_msg)
        assert self.handler.is_recoverable(error) is True

    @pytest.mark.parametrize(
        "error_msg",
        [
            "Module loading failed",
            "Invalid configuration",
            "Import error",
            "Model not found",
        ],
    )
    def test_non_recoverable_errors(self, error_msg):
        """Non-recoverable errors should return False."""
        error = Exception(error_msg)
        assert self.handler.is_recoverable(error) is False


class TestErrorRecording:
    """Test error recording and history."""

    def setup_method(self):
        self.handler = PipelineErrorHandler()

    def test_record_error(self):
        """Recording an error should create an ErrorRecord."""
        error = RuntimeError("Test error")
        record = self.handler.record_error(error, module_name="test_module", chunk_index=5)

        assert record.module_name == "test_module"
        assert record.chunk_index == 5
        assert record.message == "Test error"
        assert record.recovery_action is not None

    def test_error_count(self):
        """Error count should increment."""
        self.handler.record_error(RuntimeError("Error 1"))
        self.handler.record_error(RuntimeError("Error 2"))
        assert self.handler.error_count == 2

    def test_consecutive_errors(self):
        """Consecutive errors should track properly."""
        self.handler.record_error(RuntimeError("Error 1"))
        self.handler.record_error(RuntimeError("Error 2"))
        assert self.handler.consecutive_error_count >= 1

    def test_record_success_resets_consecutive(self):
        """Recording success should reset consecutive counter."""
        self.handler.record_error(RuntimeError("Error"))
        count_before = self.handler.consecutive_error_count
        self.handler.record_success()
        assert self.handler.consecutive_error_count == 0

    def test_get_recent_errors(self):
        """Should return last N errors."""
        for i in range(15):
            self.handler.record_error(RuntimeError(f"Error {i}"))

        recent = self.handler.get_recent_errors(count=5)
        assert len(recent) == 5
        assert "Error 14" in recent[-1]["message"]

    def test_clear_history(self):
        """Clearing history should reset all counters."""
        self.handler.record_error(RuntimeError("Error"))
        self.handler.clear_history()
        assert self.handler.error_count == 0
        assert self.handler.consecutive_error_count == 0


class TestRetryLogic:
    """Test retry decision logic."""

    def setup_method(self):
        self.handler = PipelineErrorHandler(ErrorPolicy(max_retries=3, retry_delay=0.5))

    def test_should_retry_recoverable(self):
        """Should retry recoverable errors within limits."""
        error = TimeoutError("Connection timeout")
        assert self.handler.should_retry(error, attempt=0) is True
        assert self.handler.should_retry(error, attempt=2) is True

    def test_should_not_retry_non_recoverable(self):
        """Should not retry non-recoverable errors."""
        error = ImportError("Module not found")
        assert self.handler.should_retry(error, attempt=0) is False

    def test_should_not_retry_exceeds_max(self):
        """Should not retry after max attempts."""
        error = TimeoutError("Connection timeout")
        assert self.handler.should_retry(error, attempt=3) is False

    def test_get_retry_delay_exponential(self):
        """Retry delay should increase exponentially."""
        delay_0 = self.handler.get_retry_delay(0)
        delay_1 = self.handler.get_retry_delay(1)
        delay_2 = self.handler.get_retry_delay(2)

        assert delay_0 == 0.5
        assert delay_1 == 1.0
        assert delay_2 == 2.0


class TestDegradationAndStop:
    """Test degradation and stop decisions."""

    def setup_method(self):
        self.handler = PipelineErrorHandler(
            ErrorPolicy(
                max_consecutive_errors=5,
                max_errors_per_minute=10,
            )
        )

    def test_should_degrade_after_consecutive_errors(self):
        """Should degrade after max consecutive errors."""
        for _ in range(6):
            self.handler.record_error(RuntimeError("Error"))

        assert self.handler.should_degrade() is True

    def test_should_stop_after_too_many_errors(self):
        """Should stop if too many errors per minute."""
        for _ in range(25):
            self.handler.record_error(RuntimeError("Error"))

        assert self.handler.should_stop() is True

    def test_should_not_degrade_with_few_errors(self):
        """Should not degrade with few errors."""
        self.handler.record_error(RuntimeError("Error"))
        assert self.handler.should_degrade() is False
        assert self.handler.should_stop() is False


class TestErrorPolicy:
    """Test ErrorPolicy configuration."""

    def test_default_policy(self):
        """Default policy should have reasonable values."""
        policy = ErrorPolicy()
        assert policy.max_retries == 2
        assert policy.retry_delay == 1.0
        assert policy.max_errors_per_minute == 10
        assert policy.max_consecutive_errors == 5

    def test_custom_policy(self):
        """Custom policy should override defaults."""
        policy = ErrorPolicy(
            max_retries=5,
            retry_delay=2.0,
            max_errors_per_minute=20,
        )
        assert policy.max_retries == 5
        assert policy.retry_delay == 2.0
        assert policy.max_errors_per_minute == 20


class TestErrorRecord:
    """Test ErrorRecord dataclass."""

    def test_to_dict(self):
        """ErrorRecord should serialize to dict."""
        record = ErrorRecord(
            timestamp=1234567890.0,
            category=ErrorCategory.MODULE_PROCESSING,
            severity=ErrorSeverity.ERROR,
            message="Test error",
            module_name="test",
            chunk_index=1,
            recovery_action="retry",
        )

        d = record.to_dict()
        assert d["category"] == "module_processing"
        assert d["severity"] == "error"
        assert d["message"] == "Test error"
        assert d["module_name"] == "test"
        assert d["chunk_index"] == 1
        assert d["recovery_action"] == "retry"


class TestErrorCallback:
    """Test error callback mechanism."""

    def test_error_callback_invoked(self):
        """Error callback should be invoked on error."""
        errors_received = []

        def callback(record):
            errors_received.append(record)

        handler = PipelineErrorHandler()
        handler.set_error_callback(callback)
        handler.record_error(RuntimeError("Test"))

        assert len(errors_received) == 1
        assert errors_received[0].message == "Test"
