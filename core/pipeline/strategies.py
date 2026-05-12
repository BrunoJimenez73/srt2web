"""
Pipeline Strategies - Implementa el patrón Strategy para diferentes modos de ejecución.

Cada estrategia implementa un algoritmo de procesamiento diferente:
- SequentialStrategy: Procesa chunks uno a la vez
- ThreadParallelStrategy: Procesa chunks en paralelo usando threads
- AsyncIOStrategy: Procesa chunks en paralelo usando asyncio
"""

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from core.module_base import BaseModule, PipelineData

logger = logging.getLogger("srt2web.pipeline.strategy")


@dataclass
class StrategyConfig:
    """Configuración común para todas las estrategias."""

    max_concurrent_chunks: int = 2
    chunk_timeout_sec: float = 60.0
    enable_metrics: bool = True


class PipelineStrategy(ABC):
    """Clase base abstracta para estrategias de pipeline."""

    def __init__(self, config: Optional[StrategyConfig] = None):
        self._config = config or StrategyConfig()
        self._modules: list[BaseModule] = []
        self._is_running = False

    @abstractmethod
    def process_chunk(self, data: PipelineData) -> PipelineData:
        """
        Procesa un chunk a través de los módulos.

        Args:
            data: Datos del chunk a procesar

        Returns:
            PipelineData procesada
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """Inicia la estrategia."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Detiene la estrategia."""
        pass

    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """Retorna métricas de la estrategia."""
        pass

    def set_modules(self, modules: list[BaseModule]) -> None:
        """Configura los módulos a usar."""
        self._modules = modules

    @property
    def is_running(self) -> bool:
        return self._is_running


class SequentialStrategy(PipelineStrategy):
    """
    Estrategia secuencial - Procesa chunks uno a la vez.

    Adecuada para:
    - Dependencias estrictas entre módulos
    - Debugging y desarrollo
    - Sistemas con recursos limitados
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._chunks_processed = 0
        self._total_time = 0.0

    def process_chunk(self, data: PipelineData) -> PipelineData:
        """Procesa un chunk secuencialmente."""
        start_time = time.time()

        for module in self._modules:
            if not module.enabled:
                continue

            data = module.process(data)

        self._chunks_processed += 1
        self._total_time += time.time() - start_time
        return data

    def start(self) -> None:
        self._is_running = True
        logger.info("SequentialStrategy started")

    def stop(self) -> None:
        self._is_running = False
        logger.info("SequentialStrategy stopped")

    def get_metrics(self) -> dict[str, Any]:
        return {
            "strategy": "sequential",
            "chunks_processed": self._chunks_processed,
            "total_time_sec": round(self._total_time, 3),
            "avg_time_sec": round(self._total_time / max(self._chunks_processed, 1), 3),
        }


class ThreadParallelStrategy(PipelineStrategy):
    """
    Estrategia paralela con threads - Procesa múltiples chunks concurrently.

    Adecuada para:
    - Módulos CPU-bound
    - Bloqueo I/O (disco, red)
    - Sistemas multi-core
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._semaphore = threading.Semaphore(self._config.max_concurrent_chunks)
        self._chunks_processed = 0
        self._chunks_failed = 0
        self._total_time = 0.0
        self._active_chunks = 0
        self._lock = threading.Lock()

    def process_chunk(self, data: PipelineData) -> PipelineData:
        """Procesa un chunk con semáforo para limitar concurrencia."""
        with self._semaphore:
            with self._lock:
                self._active_chunks += 1

            try:
                start_time = time.time()
                for module in self._modules:
                    if not module.enabled:
                        continue
                    data = module.process(data)

                with self._lock:
                    self._chunks_processed += 1
                    self._total_time += time.time() - start_time

                return data
            except Exception as e:
                with self._lock:
                    self._chunks_failed += 1
                logger.error(f"ThreadParallelStrategy: chunk {data.chunk_index} failed: {e}")
                raise
            finally:
                with self._lock:
                    self._active_chunks -= 1

    def start(self) -> None:
        self._is_running = True
        logger.info(f"ThreadParallelStrategy started (max_concurrent={self._config.max_concurrent_chunks})")

    def stop(self) -> None:
        self._is_running = False
        logger.info("ThreadParallelStrategy stopped")

    def get_metrics(self) -> dict[str, Any]:
        return {
            "strategy": "thread_parallel",
            "chunks_processed": self._chunks_processed,
            "chunks_failed": self._chunks_failed,
            "active_chunks": self._active_chunks,
            "total_time_sec": round(self._total_time, 3),
            "avg_time_sec": round(self._total_time / max(self._chunks_processed, 1), 3),
        }


class AsyncIOStrategy(PipelineStrategy):
    """
    Estrategia asyncio nativa - Procesa chunks concurrentemente con async/await.

    Adecuada para:
    - Alta并发 (muchos chunks)
    - I/O no bloqueante
    - Integración con servidores async (FastAPI)
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._chunks_processed = 0
        self._chunks_failed = 0
        self._total_time = 0.0
        self._active_chunks = 0

    async def process_chunk_async(self, data: PipelineData) -> PipelineData:
        """Procesa un chunk de forma asíncrona."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._config.max_concurrent_chunks)

        async with self._semaphore:
            self._active_chunks += 1
            try:
                start_time = time.time()
                for module in self._modules:
                    if not module.enabled:
                        continue
                    # Wrap sync process in run_in_executor for true async
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, module.process, data)

                self._chunks_processed += 1
                self._total_time += time.time() - start_time
                return data
            except Exception as e:
                self._chunks_failed += 1
                logger.error(f"AsyncIOStrategy: chunk {data.chunk_index} failed: {e}")
                raise
            finally:
                self._active_chunks -= 1

    def process_chunk(self, data: PipelineData) -> PipelineData:
        """Interfaz síncrona - crea un nuevo event loop si es necesario."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in async context, need to schedule
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.process_chunk_async(data))
                    return future.result()
            else:
                return asyncio.run(self.process_chunk_async(data))
        except RuntimeError:
            return asyncio.run(self.process_chunk_async(data))

    def start(self) -> None:
        self._is_running = True
        logger.info(f"AsyncIOStrategy started (max_concurrent={self._config.max_concurrent_chunks})")

    def stop(self) -> None:
        self._is_running = False
        logger.info("AsyncIOStrategy stopped")

    def get_metrics(self) -> dict[str, Any]:
        return {
            "strategy": "asyncio",
            "chunks_processed": self._chunks_processed,
            "chunks_failed": self._chunks_failed,
            "active_chunks": self._active_chunks,
            "total_time_sec": round(self._total_time, 3),
            "avg_time_sec": round(self._total_time / max(self._chunks_processed, 1), 3),
        }


def create_strategy(mode: str, config: Optional[StrategyConfig] = None) -> PipelineStrategy:
    """
    Factory function para crear estrategias.

    Args:
        mode: Modo de estrategia ("sequential", "thread_parallel", "asyncio")
        config: Configuración opcional

    Returns:
        Instancia de PipelineStrategy correspondiente

    Raises:
        ValueError: Si el modo no es válido
    """
    strategies = {
        "sequential": SequentialStrategy,
        "thread_parallel": ThreadParallelStrategy,
        "asyncio": AsyncIOStrategy,
    }

    strategy_class = strategies.get(mode)
    if not strategy_class:
        raise ValueError(f"Unknown strategy mode: {mode}. Available: {list(strategies.keys())}")

    return strategy_class(config)  # type: ignore[abstract]
