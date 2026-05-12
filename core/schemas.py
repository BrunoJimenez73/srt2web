from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class PipelineMode(str, Enum):
    SEQUENTIAL = "sequential"
    THREAD_PARALLEL = "thread_parallel"
    ASYNCIO = "asyncio"


class PipelineState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


class ModuleState(str, Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PROCESSING = "processing"
    STARTING = "starting"
    STOPPING = "stopping"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"
    DEGRADED = "degraded"


class ModuleStatus(BaseModel):
    """
    Strict model for module health and performance metrics.
    """

    name: str
    state: ModuleState
    enabled: bool
    error_message: Optional[str] = None
    last_process_time_ms: float = 0.0
    processed_chunks: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    circuit_state: Optional[str] = None
    memory_mb: Optional[float] = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "enabled": self.enabled,
            "error_message": self.error_message,
            "last_process_time_ms": self.last_process_time_ms,
            "processed_chunks": self.processed_chunks,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": self.average_processing_time,
            "circuit_state": self.circuit_state,
            "memory_mb": self.memory_mb,
            "extra": self.extra,
        }


class SystemMetrics(BaseModel):
    """
    System resource usage.
    """

    cpu_percent: float
    memory_mb: float
    memory_percent: float
    gpu_util: float = 0.0
    gpu_memory_mb: float = 0.0
    gpu_memory_percent: float = 0.0
    chunks_per_second: float = 0.0
