"""
Pipeline Factory - Crea instancias de estrategias de pipeline.

Factory que selecciona la estrategia apropiada según la configuración.
Mantiene backwards compatibility con la API existente.
"""

import logging

from core.pipeline.async_pipeline import AsyncPipeline
from core.pipeline.base import PipelineStrategy, create_pipeline_metrics
from core.pipeline.parallel import ParallelPipeline
from core.pipeline.sequential import SequentialPipeline

logger = logging.getLogger("srt2web.pipeline.factory")


from core.schemas import PipelineMode


def create_pipeline(
    mode: str = "thread_parallel",
    max_concurrent_chunks: int = 3,
    buffer_size: int = 5,
    retry_attempts: int = 2,
    retry_delay: float = 1.0,
) -> PipelineStrategy:
    """
    Factory para crear instancias de pipeline.

    Args:
        mode: Modo de operación (sequential, thread_parallel, asyncio)
        max_concurrent_chunks: Máximo chunks simultáneos
        buffer_size: Tamaño del buffer
        retry_attempts: Reintentos por módulo
        retry_delay: Delay entre reintentos

    Returns:
        Instancia de PipelineStrategy

    Example:
        >>> pipeline = create_pipeline("thread_parallel", max_concurrent_chunks=4)
        >>> pipeline.start(modules, input_source, output_sink)
    """
    mode_enum = PipelineMode(mode.lower())

    if mode_enum == PipelineMode.SEQUENTIAL:
        logger.info(f"Creating SequentialPipeline (concurrent={max_concurrent_chunks})")
        return SequentialPipeline(
            max_concurrent_chunks=max_concurrent_chunks,
            buffer_size=buffer_size,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
        )

    elif mode_enum == PipelineMode.THREAD_PARALLEL:
        logger.info(f"Creating ParallelPipeline (concurrent={max_concurrent_chunks})")
        return ParallelPipeline(
            max_concurrent_chunks=max_concurrent_chunks,
            buffer_size=buffer_size,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
        )

    elif mode_enum == PipelineMode.ASYNCIO:
        logger.info(f"Creating AsyncPipeline (concurrent={max_concurrent_chunks})")
        return AsyncPipeline(
            max_concurrent_chunks=max_concurrent_chunks,
            buffer_size=buffer_size,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
        )

    # Default to thread_parallel
    logger.warning(f"Unknown mode '{mode}', defaulting to thread_parallel")
    return create_pipeline(
        PipelineMode.THREAD_PARALLEL.value,
        max_concurrent_chunks,
        buffer_size,
        retry_attempts,
        retry_delay,
    )


def get_available_modes() -> dict[str, str]:
    """Obtener modos disponibles con descripción."""
    return {
        "sequential": "Procesamiento secuencial (un chunk a la vez)",
        "thread_parallel": "Paralelismo con threads (default, alto throughput)",
        "asyncio": "Paralelismo con asyncio nativo (bajo overhead)",
    }


__all__ = [
    "PipelineStrategy",
    "PipelineMode",
    "SequentialPipeline",
    "ParallelPipeline",
    "AsyncPipeline",
    "create_pipeline",
    "get_available_modes",
    "create_pipeline_metrics",
]
