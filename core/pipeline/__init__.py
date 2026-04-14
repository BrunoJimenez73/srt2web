"""
Core Pipeline Module - Estrategias de pipeline refactorizadas.

Este módulo contiene las estrategias de procesamiento de pipeline:
- base.py: Interfaz abstracta y métricas
- sequential.py: Procesamiento secuencial
- parallel.py: Procesamiento paralelo con threads
- async_pipeline.py: Procesamiento con asyncio
- factory.py: Factory para crear instancias
"""

from core.pipeline.base import (
    PipelineStrategy,
    MetricsTracker,
    create_pipeline_metrics,
)
from core.pipeline.factory import (
    PipelineMode,
    create_pipeline,
    get_available_modes,
)
from core.pipeline.sequential import SequentialPipeline
from core.pipeline.parallel import ParallelPipeline
from core.pipeline.async_pipeline import AsyncPipeline

# Backwards compatibility - import from unified_pipeline
# Los tests y código legacy pueden usar estos nombres
from core.unified_pipeline import UnifiedPipeline as Pipeline

__all__ = [
    # Base
    "PipelineStrategy",
    "MetricsTracker",
    "create_pipeline_metrics",
    # Factory
    "PipelineMode",
    "create_pipeline",
    "get_available_modes",
    # Strategies
    "SequentialPipeline",
    "ParallelPipeline",
    "AsyncPipeline",
    # Legacy (backwards compatible)
    "Pipeline",  # Alias para UnifiedPipeline
    "UnifiedPipeline",
]
