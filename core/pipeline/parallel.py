"""
Parallel Pipeline - Procesamiento paralelo con threads.

Esta estrategia usa múltiples workers en threads para procesar
múltiples chunks simultáneamente. Es el modo default para alto throughput.
"""

import logging
import queue
import threading
import time
from typing import Any, Optional

from core.module_base import BaseModule
from core.pipeline.base import MetricsTracker, PipelineStrategy

logger = logging.getLogger("srt2web.pipeline.parallel")


class ParallelPipeline(PipelineStrategy):
    """
    Pipeline de procesamiento paralelo con threads.

    Usa múltiples workers para procesar chunks en paralelo:
    - Input thread: produce chunks desde la fuente
    - Worker threads: procesan chunks a través de los módulos
    - Output thread: escribe resultados al sink

    - Ventajas: Alto throughput, balanceo de carga
    - Desventajas: Mayor uso de memoria, menos predictible
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
        self._input_source: Optional[Any] = None
        self._output_sink: Optional[Any] = None

        # Control
        self._stop_event = threading.Event()
        self._semaphore = threading.Semaphore(max_concurrent_chunks)
        self._running = False

        # Queues
        self._chunk_queue: queue.Queue[Any] = queue.Queue(maxsize=buffer_size)
        self._output_queue: queue.Queue[Any] = queue.Queue(maxsize=buffer_size)
        self._results: dict[int, Any] = {}

        # Threads
        self._input_thread: Optional[threading.Thread] = None
        self._worker_threads: list[threading.Thread] = []
        self._output_thread: Optional[threading.Thread] = None

        # Lock
        self._lock = threading.Lock()

        self.metrics = MetricsTracker()

    @property
    def name(self) -> str:
        return "thread_parallel"

    def start(
        self,
        modules: list[BaseModule],
        input_source: Any,
        output_sink: Any,
    ) -> None:
        """Iniciar pipeline paralelo."""
        self._modules = modules
        self._input_source = input_source
        self._output_sink = output_sink
        self._stop_event.clear()
        self._running = True
        self.metrics.start_time = time.time()

        # Input thread
        self._input_thread = threading.Thread(
            target=self._input_thread_loop,
            daemon=True,
            name="pipeline-input",
        )
        self._input_thread.start()

        # Worker threads
        for i in range(self.max_concurrent_chunks):
            worker = threading.Thread(
                target=self._worker_thread_loop,
                daemon=True,
                name=f"pipeline-worker-{i}",
            )
            worker.start()
            self._worker_threads.append(worker)

        # Output thread
        self._output_thread = threading.Thread(
            target=self._output_thread_loop,
            daemon=True,
            name="pipeline-output",
        )
        self._output_thread.start()

        self._log("info", f"ParallelPipeline started with {self.max_concurrent_chunks} workers")
        self._notify_state_change("running")

    def stop(self) -> None:
        """Detener pipeline paralelo."""
        self._running = False
        self._stop_event.set()

        # Drain queues
        while not self._chunk_queue.empty():
            try:
                self._chunk_queue.get_nowait()
            except queue.Empty:
                break

        # Join threads
        if self._input_thread and self._input_thread.is_alive():
            self._input_thread.join(timeout=2.0)

        for worker in self._worker_threads:
            if worker.is_alive():
                worker.join(timeout=2.0)

        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=2.0)

        self._log("info", "ParallelPipeline stopped")
        self._notify_state_change("idle")

    def is_running(self) -> bool:
        """Verificar si está en ejecución."""
        return self._running and not self._stop_event.is_set()

    def _input_thread_loop(self) -> None:
        """Thread de lectura de entrada."""
        logger.info("Input thread started")
        chunk_index = 0

        try:
            while not self._stop_event.is_set():
                if not self._input_source:
                    time.sleep(0.1)
                    continue

                # Esperar espacio en queue
                try:
                    self._chunk_queue.put(None, timeout=0.1)
                except queue.Full:
                    continue

                data = self._input_source.get_next_chunk()
                if data is None:
                    try:
                        self._chunk_queue.get_nowait()
                    except queue.Empty:
                        pass
                    time.sleep(0.01)
                    continue

                data.chunk_index = chunk_index
                data.timestamp = time.time()

                try:
                    self._chunk_queue.put((chunk_index, data), timeout=0.5)
                    chunk_index += 1
                except queue.Full:
                    self._log("warning", "Chunk queue full, dropping chunk")

        except Exception as e:
            self._log("error", f"Input thread error: {e}")

    def _worker_thread_loop(self) -> None:
        """Thread de procesamiento de workers."""
        worker_name = threading.current_thread().name
        logger.info(f"{worker_name} started")

        while not self._stop_event.is_set():
            try:
                item = self._chunk_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:
                self._chunk_queue.task_done()
                continue

            chunk_index, data = item

            # Acquire semaphore for concurrency control
            self._semaphore.acquire()

            try:
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

                # Put to output queue
                try:
                    self._output_queue.put((chunk_index, data), timeout=0.5)
                except queue.Full:
                    self._log("warning", "Output queue full")

            finally:
                self._semaphore.release()
                self._chunk_queue.task_done()

    def _output_thread_loop(self) -> None:
        """Thread de escritura de salida."""
        logger.info("Output thread started")

        while not self._stop_event.is_set():
            try:
                item = self._output_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            chunk_index, data = item

            try:
                if self._output_sink:
                    self._output_sink.write(data)
                self._notify_chunk_complete(chunk_index, data)
            except Exception as e:
                self._log("error", f"Output error: {e}")

            self._output_queue.task_done()

    def get_metrics(self) -> MetricsTracker:
        """Obtener métricas actuales."""
        return self.metrics
