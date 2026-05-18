"""
PipelineMetrics — Métricas agregadas del pipeline.
Extracted from core/unified_pipeline.py for clean separation.
"""

import time
from dataclasses import dataclass


@dataclass
class PipelineMetrics:
    """Métricas agregadas del pipeline."""

    chunks_processed: int = 0
    chunks_failed: int = 0
    total_processing_time: float = 0.0
    start_time: float | None = None

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

    def to_dict(self) -> dict[str, object]:
        """Serializar métricas a diccionario."""
        return {
            "chunks_processed": self.chunks_processed,
            "chunks_failed": self.chunks_failed,
            "avg_processing_time": self.avg_processing_time,
            "total_processing_time": self.total_processing_time,
            "uptime": self.uptime,
        }


__all__ = ["PipelineMetrics"]
