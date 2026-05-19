"""
PipelineMetrics — Métricas agregadas del pipeline.
Extracted from core/unified_pipeline.py for clean separation.
"""

import time
from dataclasses import dataclass, field


@dataclass
class PipelineMetrics:
    """Métricas agregadas del pipeline."""

    chunks_processed: int = 0
    chunks_failed: int = 0
    total_processing_time: float = 0.0
    start_time: float | None = None

    # Per-module timing tracking (ms)
    module_total_times: dict[str, float] = field(default_factory=dict)
    module_chunk_counts: dict[str, int] = field(default_factory=dict)

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

    @property
    def module_avg_times(self) -> dict[str, float]:
        """Average processing time per module in milliseconds."""
        return {
            name: round(self.module_total_times[name] / self.module_chunk_counts.get(name, 1), 2)
            for name in self.module_total_times
            if self.module_chunk_counts.get(name, 0) > 0
        }

    def record_module_timing(self, module_name: str, time_ms: float) -> None:
        """Record a single module's processing time for a chunk."""
        self.module_total_times.setdefault(module_name, 0.0)
        self.module_total_times[module_name] += time_ms
        self.module_chunk_counts.setdefault(module_name, 0)
        self.module_chunk_counts[module_name] += 1

    def to_dict(self) -> dict[str, object]:
        """Serializar métricas a diccionario."""
        return {
            "chunks_processed": self.chunks_processed,
            "chunks_failed": self.chunks_failed,
            "avg_processing_time": self.avg_processing_time,
            "total_processing_time": self.total_processing_time,
            "uptime": self.uptime,
            "module_total_times": dict(self.module_total_times),
            "module_chunk_counts": dict(self.module_chunk_counts),
            "module_avg_times": self.module_avg_times,
        }


__all__ = ["PipelineMetrics"]
