"""
Pipeline Base - Clase base concreta para estrategias de pipeline legacy.

Define una clase base no-abstracta para compatibilidad con estrategias
antiguas (sequential, parallel, async). La nueva PipelineStrategy ABC
vive en strategies.py para el pipeline unificado.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

from core.module_base import BaseModule, PipelineData

logger = logging.getLogger("srt2web.pipeline.base")


class PipelineStrategy:
    """
    Clase base concreta para estrategias de pipeline legacy.

    NOTA: Ya no es ABC. La nueva interfaz abstracta está en
    core.pipeline.strategies.PipelineStrategy.

    Las subclases heredadas (SequentialPipeline, ParallelPipeline,
    AsyncPipeline, AsyncPipelineV2) continúan funcionando sin cambios.
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
        self._on_log: Callable[[str, str], None] | None = None
        self._on_state_change: Callable[[str], None] | None = None
        self._on_chunk_complete: Callable[[int, PipelineData], None] | None = None

    def start(
        self,
        modules: list[BaseModule],
        input_source: Any,
        output_sink: Any,
    ) -> None:
        """Iniciar el pipeline."""
        pass

    def stop(self) -> None:
        """Detener el pipeline."""
        pass

    def is_running(self) -> bool:
        """Verificar si el pipeline está en ejecución."""
        return False

    @property
    def name(self) -> str:
        """Nombre de la estrategia."""
        return "legacy"

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

    def __init__(self) -> None:
        self.chunks_processed: int = 0
        self.chunks_failed: int = 0
        self.total_processing_time: float = 0.0
        self.start_time: float | None = None

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
