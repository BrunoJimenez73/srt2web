"""
Pipeline Base - Interfaz abstracta para estrategias de pipeline.

Define la interfaz común que todas las implementaciones de pipeline
(sequential, parallel, asyncio) deben seguir.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, List, Dict, Any
import time
import threading
import logging

from core.module_base import BaseModule, PipelineData

logger = logging.getLogger("srt2web.pipeline.base")


class PipelineStrategy(ABC):
    """
    Interfaz abstracta para estrategias de pipeline.
    
    Cada estrategia define cómo se procesan los chunks:
    - Sequential: un chunk a la vez
    - Parallel: múltiples workers en threads
    - Async: paralelismo con asyncio
    """
    
    def __init__(
        self,
        max_concurrent_chunks: int = 3,
        buffer_size: int = 5,
        retry_attempts: int = 2,
        retry_delay: float = 1.0,
    ):
        self.max_concurrent_chunks = max_concurrent_chunks
        self.buffer_size = buffer_size
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Callbacks
        self._on_log: Optional[Callable[[str, str], None]] = None
        self._on_state_change: Optional[Callable[[str], None]] = None
        self._on_chunk_complete: Optional[Callable[[int, PipelineData], None]] = None
    
    @abstractmethod
    def start(
        self,
        modules: List[BaseModule],
        input_source: Any,
        output_sink: Any,
    ) -> None:
        """Iniciar el pipeline."""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Detener el pipeline."""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Verificar si el pipeline está en ejecución."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre de la estrategia."""
        pass
    
    def set_log_callback(self, callback: Callable[[str, str], None]) -> None:
        """Configurar callback para logs."""
        self._on_log = callback
    
    def set_state_change_callback(self, callback: Callable[[str], None]) -> None:
        """Configurar callback para cambios de estado."""
        self._on_state_change = callback
    
    def set_chunk_complete_callback(self, callback: Callable[[int, PipelineData], None]) -> None:
        """Configurar callback para chunks completados."""
        self._on_chunk_complete = callback
    
    def _log(self, level: str, message: str) -> None:
        """Enviar log a callback."""
        if self._on_log:
            self._on_log(level, message)
        else:
            getattr(logger, level.lower())(message)
    
    def _notify_state_change(self, state: str) -> None:
        """Notificar cambio de estado."""
        if self._on_state_change:
            self._on_state_change(state)
    
    def _notify_chunk_complete(self, chunk_index: int, data: PipelineData) -> None:
        """Notificar chunk completado."""
        if self._on_chunk_complete:
            self._on_chunk_complete(chunk_index, data)


class MetricsTracker:
    """Tracker de métricas simple para todas las estrategias."""
    
    def __init__(self):
        self.chunks_processed: int = 0
        self.chunks_failed: int = 0
        self.total_processing_time: float = 0.0
        self.start_time: Optional[float] = None
    
    @property
    def avg_processing_time(self) -> float:
        if self.chunks_processed == 0:
            return 0.0
        return self.total_processing_time / self.chunks_processed
    
    @property
    def uptime(self) -> float:
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time
    
    def record_chunk(self, processing_time: float, success: bool = True) -> None:
        """Registrar un chunk procesado."""
        if success:
            self.chunks_processed += 1
            self.total_processing_time += processing_time
        else:
            self.chunks_failed += 1


def create_pipeline_metrics() -> MetricsTracker:
    """Factory para crear tracker de métricas."""
    return MetricsTracker()
