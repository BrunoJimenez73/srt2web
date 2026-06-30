"""
CircuitBreaker — Circuit breaker pattern with retry strategy.
Extracted from core/module_base.py for reuse across the codebase.
"""

import logging
import threading
import time
from collections.abc import Callable
from enum import StrEnum
from typing import Any

logger = logging.getLogger("srt2web.circuit_breaker")


class CircuitState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for module fault tolerance.

    States:
        CLOSED: Normal operation, requests pass through
        OPEN: Failures exceeded threshold, requests blocked
        HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN and time.time() - self._last_failure_time >= self.timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
            return self._state

    def can_execute(self) -> bool:
        """Check if request can be executed."""
        current_state = self.state
        if current_state == CircuitState.CLOSED:
            return True
        if current_state == CircuitState.HALF_OPEN:
            with self._lock:
                return self._half_open_calls < self.half_open_max_calls
        return False

    def record_success(self) -> None:
        """Record successful execution."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._half_open_calls += 1
                if self._success_count >= self.half_open_max_calls:
                    self._reset()
            else:
                self._failure_count = 0
                self._success_count = 0

    def record_failure(self) -> None:
        """Record failed execution."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.failure_threshold:
                self._open_circuit()

    def _open_circuit(self) -> None:
        """Open the circuit (start blocking requests)."""
        self._state = CircuitState.OPEN
        self._half_open_calls = 0

    def _reset(self) -> None:
        """Reset circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0

    def force_reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._reset()


class RetryStrategy:
    """Retry strategy with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)
        return delay

    def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        is_recoverable: Callable[[Exception], bool] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            is_recoverable: Optional function to check if exception is recoverable
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            Last exception if all retries exhausted
        """
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    if is_recoverable is not None and not is_recoverable(e):
                        raise

                    delay = self.get_delay(attempt)
                    time.sleep(delay)

        if last_exception is not None:
            raise last_exception


def is_recoverable_error(exception: Exception) -> bool:
    """
    Determine if an error is recoverable (retryable).

    Recoverable errors:
    - Timeout errors
    - Temporary file not available
    - Memory errors (sometimes)
    - FFmpeg temporary failures

    Non-recoverable errors:
    - Model loading failures
    - Configuration errors
    - Import errors
    """
    error_str = str(exception).lower()
    recoverable_patterns = [
        "timeout",
        "timed out",
        "temporary",
        "temp file",
        "ffmpeg",
        "stream",
        "connection",
        "resource",
        "memory",
        "process",
    ]

    return any(pattern in error_str for pattern in recoverable_patterns)


__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "RetryStrategy",
    "is_recoverable_error",
]
