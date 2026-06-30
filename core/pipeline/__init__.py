"""
Core Pipeline Module - Estrategias de pipeline.

ADVERTENCIA (F101): Las clases legacy SequentialPipeline, ParallelPipeline,
AsyncPipeline y PipelineStrategy existen para compatibilidad hacia atrás.
Emite DeprecationWarning al instanciarse.

La implementación activa está en:
  - core/pipeline/strategies.py  (PipelineStrategy ABC + 3 subclases concretas)
  - core/unified_pipeline.py     (UnifiedPipeline — orquestador principal)
  - core/pipeline/factory.py     (legacy, usar core/pipeline/strategies.create_strategy)
"""

from core.pipeline.async_pipeline import AsyncPipeline
from core.pipeline.base import (
    MetricsTracker,
    PipelineStrategy,
    create_pipeline_metrics,
)
from core.pipeline.factory import (
    PipelineMode,
    create_pipeline,
    get_available_modes,
)
from core.pipeline.parallel import ParallelPipeline
from core.pipeline.sequential import SequentialPipeline

# Backwards compatibility - import from unified_pipeline
from core.unified_pipeline import UnifiedPipeline as Pipeline

__all__ = [
    "AsyncPipeline",
    "MetricsTracker",
    "ParallelPipeline",
    # Alias
    "Pipeline",
    # Legacy factory
    "PipelineMode",
    # Legacy base (deprecated — emite DeprecationWarning)
    "PipelineStrategy",
    # Legacy strategies (deprecated)
    "SequentialPipeline",
    "UnifiedPipeline",
    "create_pipeline",
    "create_pipeline_metrics",
    "get_available_modes",
]
