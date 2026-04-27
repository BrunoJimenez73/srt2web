"""
Base module interface for the SRT2Web pipeline.

All processing modules must inherit from BaseModule and implement
the required methods. This ensures modules are interchangeable.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Callable
import logging
import time
import threading
import gc

import numpy as np


class ModuleState(str, Enum):
    """Possible states of a processing module."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    DISABLED = "disabled"
    DEGRADED = "degraded"


class CircuitState(str, Enum):
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

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0, half_open_max_calls: int = 3) -> None:
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
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.timeout:
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

            if self._state == CircuitState.HALF_OPEN:
                self._open_circuit()
            elif self._failure_count >= self.failure_threshold:
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

    def __init__(self, max_retries: int = 3, base_delay: float = 0.5, max_delay: float = 10.0, exponential_base: float = 2.0) -> None:
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
        func: Callable,
        *args,
        is_recoverable=None,
        **kwargs,
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


class MemoryManager:
    """
    Memory management for pipeline stability.

    Monitors memory usage and triggers garbage collection
    when thresholds are exceeded.
    """

    def __init__(self, max_memory_mb: float = 3072.0, gc_threshold_mb: float = 2048.0, check_interval: int = 10) -> None:
        self.max_memory_mb = max_memory_mb
        self.gc_threshold_mb = gc_threshold_mb
        self.check_interval = check_interval
        self._chunk_counter = 0
        self._last_gc_time = 0
        self._min_gc_interval = 30
        self.logger = logging.getLogger("srt2web.memory")

    def check(self) -> dict:
        """
        Check memory usage and trigger GC if needed.

        Returns:
            dict with memory info
        """
        self._chunk_counter += 1

        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()

            info = {
                "memory_mb": round(memory_mb, 1),
                "memory_percent": round(memory_percent, 1),
                "gc_triggered": False,
                "above_threshold": memory_mb > self.gc_threshold_mb,
            }

            if memory_mb > self.gc_threshold_mb:
                time_since_gc = time.time() - self._last_gc_time

                if time_since_gc > self._min_gc_interval:
                    self.logger.info(
                        f"Memory high ({memory_mb:.0f}MB). Running garbage collection..."
                    )
                    gc.collect()
                    self._last_gc_time = time.time()
                    info["gc_triggered"] = True

                    new_memory = process.memory_info().rss / 1024 / 1024
                    self.logger.info(
                        f"GC complete. Memory: {new_memory:.0f}MB (freed {memory_mb - new_memory:.0f}MB)"
                    )
                    info["memory_after_gc"] = round(new_memory, 1)

            if memory_mb > self.max_memory_mb:
                self.logger.warning(
                    f"Memory critical ({memory_mb:.0f}MB > {self.max_memory_mb:.0f}MB). "
                    "Consider increasing limit or reducing processing."
                )
                info["critical"] = True

            return info

        except ImportError:
            return {"memory_mb": 0, "memory_percent": 0, "psutil_not_available": True}

    def should_check(self) -> bool:
        """Check if it's time to run memory check."""
        return self._chunk_counter % self.check_interval == 0


@dataclass
class ModuleStatus:
    """Status information for a module."""

    name: str
    state: ModuleState
    enabled: bool
    error_message: Optional[str] = None
    processed_chunks: int = 0
    last_process_time_ms: float = 0.0
    extra: dict = field(default_factory=dict)
    circuit_state: Optional[str] = None
    memory_mb: Optional[float] = None

    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "state": self.state.value,
            "enabled": self.enabled,
            "error_message": self.error_message,
            "processed_chunks": self.processed_chunks,
            "last_process_time_ms": round(self.last_process_time_ms, 2),
            "extra": self.extra,
        }
        if self.circuit_state:
            result["circuit_state"] = self.circuit_state
        if self.memory_mb is not None:
            result["memory_mb"] = self.memory_mb
        return result


@dataclass
class PipelineData:
    """
    Data container that flows through the processing pipeline.
    Each module reads what it needs and adds its output fields.
    """

    chunk_index: int = 0
    timestamp: float = 0.0
    duration: float = 0.0
    cumulative_duration: float = (
        0.0  # Accumulated duration from previous chunks (for sync)
    )
    video_chunk_path: Optional[str] = None
    audio_chunk_path: Optional[str] = None
    audio_samples: Optional[np.ndarray] = None
    audio_sample_rate: int = 16000
    transcript: Optional[str] = None
    transcript_segments: list = field(default_factory=list)
    detected_language: Optional[str] = None
    translated_text: Optional[str] = None
    translated_segments: list = field(default_factory=list)
    subtitles_path: Optional[str] = None
    dubbed_audio_path: Optional[str] = None
    mixed_audio_path: Optional[str] = None
    output_hls_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict (excluding numpy arrays)."""
        d = {}
        for k, v in self.__dict__.items():
            if isinstance(v, np.ndarray):
                d[k] = f"<ndarray shape={v.shape} dtype={v.dtype}>"
            else:
                d[k] = v
        return d


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

    for pattern in recoverable_patterns:
        if pattern in error_str:
            return True

    return False


class BaseModule(ABC):
    """
    Abstract base class for all pipeline processing modules.

    Lifecycle:
        1. __init__(name, config) — constructor
        2. configure(config)     — apply configuration
        3. start()               — initialize resources
        4. process(data)         — called for each chunk (main loop)
        5. stop()                — release resources
    """

    _memory_manager = MemoryManager()

    def __init__(self, name: str, config: Optional[dict] = None, circuit_breaker: Optional[CircuitBreaker] = None, retry_strategy: Optional[RetryStrategy] = None) -> None:
        self.name = name
        self.enabled = True
        self._state = ModuleState.IDLE
        self._error_message: Optional[str] = None
        self._processed_chunks = 0
        self._last_process_time_ms = 0.0
        self.logger = logging.getLogger(f"srt2web.module.{name}")

        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=5,
            timeout=60.0,
        )
        self._retry_strategy = retry_strategy or RetryStrategy(
            max_retries=3,
            base_delay=0.5,
        )

        if config:
            self.configure(config)

    @property
    def state(self) -> ModuleState:
        return self._state

    @property
    def circuit_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self._circuit_breaker.state

    def configure(self, config: dict) -> None:
        """
        Apply configuration dictionary to this module.
        Override in subclasses to handle module-specific config.
        """
        self.enabled = config.get("enabled", True)
        if not self.enabled:
            self._state = ModuleState.DISABLED

        cb_config = config.get("circuit_breaker", {})
        if cb_config:
            self._circuit_breaker.failure_threshold = cb_config.get(
                "failure_threshold", self._circuit_breaker.failure_threshold
            )
            self._circuit_breaker.timeout = cb_config.get(
                "timeout", self._circuit_breaker.timeout
            )

        retry_config = config.get("retry", {})
        if retry_config:
            self._retry_strategy.max_retries = retry_config.get(
                "max_retries", self._retry_strategy.max_retries
            )
            self._retry_strategy.base_delay = retry_config.get(
                "base_delay", self._retry_strategy.base_delay
            )

    @abstractmethod
    def start(self) -> None:
        """
        Initialize module resources (models, processes, etc.).
        Called once before processing begins.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Release module resources.
        Called once when the pipeline stops.
        """
        pass

    @abstractmethod
    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Process a single chunk of data.
        Override this in subclasses with the actual processing logic.
        """
        pass

    def _degraded_process(self, data: PipelineData) -> PipelineData:
        """
        Graceful degradation when module fails.

        Override in subclasses to provide degraded but functional behavior.
        Default: return data unchanged (skip this module's processing).
        """
        self.logger.warning(
            f"Module {self.name} in degraded mode, skipping processing for chunk {data.chunk_index}"
        )
        self._state = ModuleState.DEGRADED
        return data

    def process(self, data: PipelineData) -> PipelineData:
        """
        Wrapper around _do_process that handles:
        - Circuit breaker
        - Retry logic
        - Error recovery
        - Memory management
        - Timing and counting

        Do not override this — override _do_process instead.
        """
        if not self.enabled or self._state == ModuleState.DISABLED:
            return data

        if self._state == ModuleState.ERROR and self.circuit_state == CircuitState.OPEN:
            self.logger.debug(f"Circuit open for {self.name}, using degraded mode")
            return self._degraded_process(data)

        if not self._circuit_breaker.can_execute():
            self.logger.debug(f"Circuit not ready for {self.name}, using degraded mode")
            return self._degraded_process(data)

        start_time = time.perf_counter()
        last_error = None

        def do_work():
            return self._do_process(data)

        for attempt in range(self._retry_strategy.max_retries + 1):
            try:
                result = do_work()

                elapsed = (time.perf_counter() - start_time) * 1000
                self._last_process_time_ms = elapsed
                self._processed_chunks += 1
                self._circuit_breaker.record_success()

                if self._state == ModuleState.DEGRADED:
                    self._state = ModuleState.RUNNING

                self.logger.debug(
                    f"Processed chunk {data.chunk_index} in {elapsed:.1f}ms"
                )

                self._check_memory()

                return result

            except Exception as e:
                last_error = e
                self._circuit_breaker.record_failure()

                if attempt < self._retry_strategy.max_retries:
                    delay = self._retry_strategy.get_delay(attempt)
                    self.logger.warning(
                        f"Retry {attempt + 1}/{self._retry_strategy.max_retries + 1} "
                        f"for {self.name} after {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"All retries exhausted for {self.name} "
                        f"(chunk {data.chunk_index}): {e}"
                    )

        elapsed = (time.perf_counter() - start_time) * 1000
        self._last_process_time_ms = elapsed
        self._state = ModuleState.ERROR
        self._error_message = str(last_error)

        return self._degraded_process(data)

    def _check_memory(self) -> None:
        """Check memory usage if it's time to do so."""
        if self._memory_manager.should_check():
            mem_info = self._memory_manager.check()
            if mem_info.get("gc_triggered"):
                self.logger.info(
                    f"Memory after GC: {mem_info.get('memory_after_gc', 'N/A')}MB"
                )

    def get_status(self) -> ModuleStatus:
        """Get current status of this module (sin llamar a psutil por módulo)."""
        return ModuleStatus(
            name=self.name,
            state=self._state if self.enabled else ModuleState.DISABLED,
            enabled=self.enabled,
            error_message=self._error_message,
            processed_chunks=self._processed_chunks,
            last_process_time_ms=self._last_process_time_ms,
            circuit_state=self.circuit_state.value,
            memory_mb=None,  # El pipeline lo llena desde HardwareMonitor centralizado
        )

    def reset_error(self) -> None:
        """Clear error state and reset circuit breaker."""
        if self._state == ModuleState.ERROR:
            self._state = ModuleState.RUNNING
            self._error_message = None
        self._circuit_breaker.force_reset()
