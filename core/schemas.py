from enum import Enum
from pathlib import Path
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field


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


class PipelineData(BaseModel):
    """
    Strict data model for chunks moving through the pipeline.
    Replaces generic dicts to ensure all modules have required data.
    """

    # Core identification and timing
    chunk_index: int = 0
    timestamp: float = Field(default_factory=lambda: __import__("time").time)
    duration: float = 0.0
    cumulative_duration: float = 0.0

    # File paths (standardized to Path)
    video_chunk_path: Optional[Path] = None
    audio_chunk_path: Optional[Path] = None
    audio_samples: Optional[np.ndarray] = None
    audio_sample_rate: int = 16000
    tts_audio_path: Optional[Path] = None
    mixed_audio_path: Optional[Path] = None
    subtitles_path: Optional[Path] = None
    output_hls_path: Optional[Path] = None

    # Text processing results
    transcript: Optional[str] = None
    transcript_segments: list[dict[str, Any]] = Field(default_factory=list)
    detected_language: Optional[str] = None
    translation: Optional[str] = None
    translated_segments: list[dict[str, Any]] = Field(default_factory=list)
    subtitles: Optional[list[dict[str, Any]]] = None

    # Metadata and error tracking
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True  # For numpy arrays


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
