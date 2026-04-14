"""
AsyncIO Pipeline - Procesamiento paralelo con asyncio.

Esta estrategia usa asyncio nativo para procesamiento paralelo.
Ideal para módulos que soportan async/await.
"""

import asyncio
import time
import logging
from typing import Optional, Callable, List, Any

from core.pipeline.base import PipelineStrategy, MetricsTracker
from core.module_base import BaseModule, PipelineData

logger = logging.getLogger("srt2web.pipeline.async_pipeline")


class AsyncPipeline(PipelineStrategy):
    """
    Pipeline de procesamiento con asyncio nativo.
    
    Usa async/await para procesamiento paralelo:
    - Ventajas: Muy eficiente para I/O, bajo overhead
    - Desventajas: Requiere módulos async-compatible
    """
    
    def __init__(
        self,
        max_concurrent_chunks: int = 3,
        buffer_size: int = 5,
        retry_attempts: int = 2,
        retry_delay: float = 1.0,
    ):
        super().__init__(
            max_concurrent_chunks=max_concurrent_chunks,
            buffer_size=buffer_size,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
        )
        
        self._modules: List[BaseModule] = []
        self._input_source: Optional[Any] = None
        self._output_sink: Optional[Any] = None
        
        self._running = False
        self._stop_event: Optional[asyncio.Event] = None
        self._task: Optional[asyncio.Task] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        
        self.metrics = MetricsTracker()
    
    @property
    def name(self) -> str:
        return "asyncio"
    
    def start(
        self,
        modules: List[BaseModule],
        input_source: Any,
        output_sink: Any,
    ) -> None:
        """Iniciar pipeline asyncio."""
        self._modules = modules
        self._input_source = input_source
        self._output_sink = output_sink
        self._running = True
        self.metrics.start_time = time.time()
        
        self._stop_event = asyncio.Event()
        self._semaphore = asyncio.Semaphore(self.max_concurrent_chunks)
        
        # Create and run async task
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run_async_loop())
        
        self._log("info", "AsyncPipeline started")
        self._notify_state_change("running")
    
    def stop(self) -> None:
        """Detener pipeline asyncio."""
        self._running = False
        
        if self._stop_event:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._stop_event.set())
        
        if self._task and not self._task.done():
            self._task.cancel()
        
        self._log("info", "AsyncPipeline stopped")
        self._notify_state_change("idle")
    
    def is_running(self) -> bool:
        """Verificar si está en ejecución."""
        return self._running and self._task and not self._task.done()
    
    async def _run_async_loop(self) -> None:
        """Bucle principal async."""
        logger.info("AsyncIO processing loop started")
        chunk_index = 0
        
        try:
            while not self._stop_event.is_set():
                if not self._input_source:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get next chunk (sync version for compatibility)
                data = self._input_source.get_next_chunk()
                if data is None:
                    await asyncio.sleep(0.01)
                    continue
                
                data.chunk_index = chunk_index
                data.timestamp = time.time()
                
                # Process with semaphore control
                async with self._semaphore:
                    start_time = time.perf_counter()
                    
                    # Process through modules
                    for module in self._modules:
                        if not module.enabled or self._stop_event.is_set():
                            continue
                        try:
                            data = module.process(data)
                        except Exception as e:
                            self._log("error", f"Module {module.name} error: {e}")
                            break
                    
                    elapsed = time.perf_counter() - start_time
                    self.metrics.record_chunk(elapsed, success=True)
                
                # Write output
                if self._output_sink and data:
                    try:
                        self._output_sink.write(data)
                    except Exception as e:
                        self._log("error", f"Output sink error: {e}")
                
                # Notify callback
                self._notify_chunk_complete(chunk_index, data)
                
                chunk_index += 1
                
        except asyncio.CancelledError:
            logger.info("AsyncIO loop cancelled")
        except Exception as e:
            self._log("error", f"AsyncIO loop error: {e}")
            self._notify_state_change("error")
    
    def get_metrics(self) -> MetricsTracker:
        """Obtener métricas actuales."""
        return self.metrics
