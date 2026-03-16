"""
Base module interface for the SRT2Web pipeline.

All processing modules must inherit from BaseModule and implement
the required methods. This ensures modules are interchangeable.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
import logging
import time

import numpy as np


class ModuleState(str, Enum):
    """Possible states of a processing module."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    DISABLED = "disabled"


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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "enabled": self.enabled,
            "error_message": self.error_message,
            "processed_chunks": self.processed_chunks,
            "last_process_time_ms": round(self.last_process_time_ms, 2),
            "extra": self.extra,
        }


@dataclass
class PipelineData:
    """
    Data container that flows through the processing pipeline.
    Each module reads what it needs and adds its output fields.
    """
    # Chunk identification
    chunk_index: int = 0
    timestamp: float = 0.0
    duration: float = 0.0

    # Video / container paths
    video_chunk_path: Optional[str] = None
    
    # Audio data
    audio_chunk_path: Optional[str] = None
    audio_samples: Optional[np.ndarray] = None
    audio_sample_rate: int = 16000

    # Transcription
    transcript: Optional[str] = None
    transcript_segments: list = field(default_factory=list)
    detected_language: Optional[str] = None

    # Translation
    translated_text: Optional[str] = None
    translated_segments: list = field(default_factory=list)

    # Subtitles
    subtitles_path: Optional[str] = None

    # TTS / Dubbed audio
    dubbed_audio_path: Optional[str] = None

    # Mixed audio
    mixed_audio_path: Optional[str] = None

    # Final output
    output_hls_path: Optional[str] = None

    # Arbitrary metadata
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

    def __init__(self, name: str, config: Optional[dict] = None):
        self.name = name
        self.enabled = True
        self._state = ModuleState.IDLE
        self._error_message: Optional[str] = None
        self._processed_chunks = 0
        self._last_process_time_ms = 0.0
        self.logger = logging.getLogger(f"srt2web.module.{name}")
        
        if config:
            self.configure(config)

    @property
    def state(self) -> ModuleState:
        return self._state

    def configure(self, config: dict) -> None:
        """
        Apply configuration dictionary to this module.
        Override in subclasses to handle module-specific config.
        """
        self.enabled = config.get("enabled", True)
        if not self.enabled:
            self._state = ModuleState.DISABLED

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

    def process(self, data: PipelineData) -> PipelineData:
        """
        Wrapper around _process that handles timing, counting, and errors.
        Do not override this — override _process instead.
        """
        if not self.enabled or self._state == ModuleState.DISABLED:
            return data

        start_time = time.perf_counter()
        try:
            result = self._do_process(data)
            elapsed = (time.perf_counter() - start_time) * 1000
            self._last_process_time_ms = elapsed
            self._processed_chunks += 1
            self.logger.debug(
                f"Processed chunk {data.chunk_index} in {elapsed:.1f}ms"
            )
            return result
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            self._last_process_time_ms = elapsed
            self._state = ModuleState.ERROR
            self._error_message = str(e)
            self.logger.error(f"Error processing chunk {data.chunk_index}: {e}")
            # Return data unchanged so pipeline can continue
            return data

    def get_status(self) -> ModuleStatus:
        """Get current status of this module."""
        return ModuleStatus(
            name=self.name,
            state=self._state if self.enabled else ModuleState.DISABLED,
            enabled=self.enabled,
            error_message=self._error_message,
            processed_chunks=self._processed_chunks,
            last_process_time_ms=self._last_process_time_ms,
        )

    def reset_error(self) -> None:
        """Clear error state and return to RUNNING."""
        if self._state == ModuleState.ERROR:
            self._state = ModuleState.RUNNING
            self._error_message = None
