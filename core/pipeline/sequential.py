"""
Sequential Pipeline - Procesamiento secuencial de chunks.

Esta estrategia procesa un chunk a la vez, en orden.
Adecuada para debugging y sistemas con recursos limitados.
"""

import logging
import threading
import time
from typing import Any

from core.module_base import BaseModule
from core.pipeline.base import MetricsTracker, PipelineStrategy

logger = logging.getLogger("srt2web.pipeline.sequential")


class SequentialPipeline(PipelineStrategy):
    """
    Pipeline de procesamiento secuencial.

    Procesa chunks uno a la vez en orden estricto.
    - Ventajas: Predictible, fácil debugging, bajo consumo de memoria
    - Desventajas: Menor throughput
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

        self._modules: list[BaseModule] = []
        self._input_source: Any | None = None
        self._output_sink: Any | None = None
        self._stop_event = threading.Event()
        self._running = False
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self.metrics = MetricsTracker()

    @property
    def name(self) -> str:
        return "sequential"

    def start(
        self,
        modules: list[BaseModule],
        input_source: Any,
        output_sink: Any,
    ) -> None:
        """Iniciar pipeline secuencial."""
        self._modules = modules
        self._input_source = input_source
        self._output_sink = output_sink
        self._stop_event.clear()
        self._running = True
        self.metrics.start_time = time.time()

        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="pipeline-sequential",
        )
        self._thread.start()

        self._log("info", "SequentialPipeline started")
        self._notify_state_change("running")

    def stop(self) -> None:
        """Detener pipeline secuencial."""
        self._running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self._log("info", "SequentialPipeline stopped")
        self._notify_state_change("idle")

    def is_running(self) -> bool:
        """Verificar si está en ejecución."""
        return self._running and not self._stop_event.is_set()

    def _run_loop(self) -> None:
        """Bucle principal de procesamiento secuencial."""
        logger.info("Sequential processing loop started")
        chunk_index = 0

        try:
            while not self._stop_event.is_set():
                if not self._input_source:
                    time.sleep(0.1)
                    continue

                # Obtener siguiente chunk
                data = self._input_source.get_next_chunk()
                if data is None:
                    time.sleep(0.01)
                    continue

                data.chunk_index = chunk_index
                data.timestamp = time.time()

                # Procesar secuencialmente
                start_time = time.perf_counter()
                for module in self._modules:
                    if not module.enabled or self._stop_event.is_set():
                        continue
                    try:
                        data = module.process(data)
                    except Exception as e:
                        self._log("error", f"Module {module.name} error: {e}")
                        break

                # Escribir salida
                if self._output_sink and data:
                    try:
                        self._output_sink.write(data)
                    except Exception as e:
                        self._log("error", f"Output sink error: {e}")

                elapsed = time.perf_counter() - start_time
                self.metrics.record_chunk(elapsed, success=True)

                # Notificar callback
                self._notify_chunk_complete(chunk_index, data)

                chunk_index += 1

        except Exception as e:
            self._log("error", f"Sequential loop error: {e}")
            self._notify_state_change("error")

    def get_metrics(self) -> MetricsTracker:
        """Obtener métricas actuales."""
        return self.metrics
