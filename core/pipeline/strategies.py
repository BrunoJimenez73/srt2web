"""
Pipeline Strategies - Implementa el patrón Strategy para diferentes modos de ejecución.

Cada estrategia implementa un algoritmo de procesamiento diferente:
- SequentialStrategy: Procesa chunks uno a la vez
- ThreadParallelStrategy: Procesa chunks en paralelo usando threads
- AsyncIOStrategy: Procesa chunks en paralelo usando asyncio

Refactorizado (F66): Se extrajo la lógica común a PipelineStrategy como clase base concreta,
eliminando ~60% de duplicación entre las 3 estrategias.

Refactorizado (F132): Se movieron los 5 métodos de loop desde unified_pipeline.py
a las estrategias correspondientes, reduciendo unified_pipeline.py de ~1100 a <600 líneas.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from core.module_base import BaseModule, PipelineData

if TYPE_CHECKING:
    pass

logger = logging.getLogger("srt2web.pipeline.strategy")


@dataclass
class StrategyConfig:
    """Configuración común para todas las estrategias."""

    max_concurrent_chunks: int = 2
    chunk_timeout_sec: float = 60.0
    enable_metrics: bool = True


@dataclass
class ChunkProcessor:
    """Trackea el estado de procesamiento de un chunk."""

    chunk_index: int
    timestamp: float
    data: PipelineData | None = None
    stages_completed: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    task: threading.Thread | asyncio.Task[None] | None = None


@dataclass
class PipelineContext:
    """Bundles shared state between UnifiedPipeline and strategies.

    Passed to strategies so loop implementations can access pipeline
    internals without tight coupling.
    """

    stop_event: threading.Event | asyncio.Event
    semaphore: threading.Semaphore | asyncio.Semaphore
    chunk_queue: queue.Queue[ChunkProcessor]
    output_queue: queue.Queue[ChunkProcessor]
    results: dict[int, ChunkProcessor]
    lock: threading.Lock
    modules: list[BaseModule]
    input_source: Any
    output_sink: Any
    on_log: Callable[[str, str], None] | None
    on_state_change: Callable[[str], None] | None
    on_chunk_complete: Callable[[int, PipelineData], None] | None
    set_state: Callable[[Any], None]
    metrics: Any  # PipelineMetrics (avoiding circular import)
    lost_chunk_timeout: float
    buffer_size: int
    hardware_monitor: Any = None  # HardwareMonitor for adaptive concurrency (F170)
    adaptive_config: dict[str, Any] | None = None  # F170 reactive pipeline settings
    chunk_duration: float = 10.0  # Current chunk_duration_sec for adaptation
    on_chunk_duration_change: Callable[[float], None] | None = None  # F170 adaptation callback


class PipelineStrategy(ABC):
    """
    Clase base abstracta para estrategias de pipeline.

    Proporciona implementación común para:
    - Contadores de chunks procesados/fallados/activos
    - Métodos start()/stop() con logging
    - Métricas base (chunks_processed, total_time, avg_time)
    - Iteración sobre módulos habilitados
    """

    def __init__(self, config: StrategyConfig | None = None):
        self._config = config or StrategyConfig()
        self._modules: list[BaseModule] = []
        self._is_running = False
        # Contadores comunes a todas las estrategias
        self._chunks_processed = 0
        self._chunks_failed = 0
        self._total_time = 0.0
        self._active_chunks = 0
        # Shared context set by pipeline before starting loops
        self._ctx: PipelineContext | None = None

    def set_modules(self, modules: list[BaseModule]) -> None:
        """Configura los módulos a usar."""
        self._modules = modules

    def set_context(self, ctx: PipelineContext) -> None:
        """Set the shared pipeline context for loop execution."""
        self._ctx = ctx

    @property
    def is_running(self) -> bool:
        return self._is_running

    # --- Métodos concretos compartidos por todas las estrategias ---

    def start(self) -> None:
        """Inicia la estrategia."""
        self._is_running = True
        logger.info("%s started (max_concurrent=%s)", self.__class__.__name__, self._config.max_concurrent_chunks)

    def stop(self) -> None:
        """Detiene la estrategia."""
        self._is_running = False
        logger.info("%s stopped", self.__class__.__name__)

    def _process_modules(self, data: PipelineData) -> PipelineData:
        """
        Itera sobre los módulos habilitados procesando el chunk.
        Es el corazón del pipeline, compartido por todas las estrategias.
        """
        for module in self._modules:
            if not module.enabled:
                continue
            data = module.process(data)
        return data

    def _process_modules_with_tracking(
        self,
        data: PipelineData,
        processor: ChunkProcessor | None = None,
    ) -> PipelineData:
        """Process modules with per-module timing and degraded-mode handling."""
        for module in self._modules:
            if not module.enabled or (self._ctx and self._ctx.stop_event.is_set()):
                continue
            try:
                module_start = time.perf_counter()
                data = module.process(data)
                if processor is not None:
                    processor.stages_completed[module.name] = (time.perf_counter() - module_start) * 1000
                if module.state.value == "degraded" and not getattr(module, "is_critical", True):
                    self._log("warning", f"Non-critical module {module.name} degraded, continuing pipeline")
            except Exception as e:
                self._log("error", f"Module {module.name} error: {e}")
                if processor is not None:
                    processor.error = str(e)
                if not getattr(module, "is_critical", True):
                    self._log("warning", f"Non-critical module {module.name} failed, continuing in degraded mode")
                    continue
                break
        return data

    def _log(self, level: str, message: str) -> None:
        """Emit log via context callback."""
        getattr(logger, level, logger.info)(message)
        if self._ctx and self._ctx.on_log:
            try:
                self._ctx.on_log(level, message)
            except Exception as e:
                logger.exception("Log callback failed: %s", e)

    def get_metrics(self) -> dict[str, Any]:
        """Retorna métricas base comunes."""
        return {
            "chunks_processed": self._chunks_processed,
            "chunks_failed": self._chunks_failed,
            "active_chunks": self._active_chunks,
            "total_time_sec": round(self._total_time, 3),
            "avg_time_sec": round(self._total_time / max(self._chunks_processed, 1), 3),
        }

    # --- Loop management (F132: moved from unified_pipeline.py) ---

    def start_threads(self, ctx: PipelineContext) -> None:
        """Start execution threads/tasks. Override in subclasses."""
        self._ctx = ctx
        self._modules = ctx.modules

    def stop_threads(self) -> Any:
        """Stop execution threads/tasks. Override in subclasses if needed."""
        return None

    # --- Métodos abstractos que cada estrategia debe implementar ---

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


class SequentialStrategy(PipelineStrategy):
    """
    Estrategia secuencial - Procesa chunks uno a la vez.

    Adecuada para:
    - Dependencias estrictas entre módulos
    - Debugging y desarrollo
    - Sistemas con recursos limitados
    """

    def __init__(self, config: StrategyConfig | None = None):
        super().__init__(config)
        self._thread: threading.Thread | None = None

    def process_chunk(self, data: PipelineData) -> PipelineData:
        """Procesa un chunk secuencialmente."""
        start_time = time.time()
        data = self._process_modules(data)
        self._chunks_processed += 1
        self._total_time += time.time() - start_time
        return data

    def start_threads(self, ctx: PipelineContext) -> None:
        """Start the sequential processing loop in a single thread."""
        super().start_threads(ctx)
        self._thread = threading.Thread(
            target=self._run_sequential_loop,
            daemon=True,
            name="pipeline-sequential",
        )
        self._thread.start()

    def stop_threads(self) -> None:
        """Join the sequential thread with timeout."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("Sequential pipeline thread did not stop within 5s timeout")
        self._thread = None

    def _run_sequential_loop(self) -> None:
        """Bucle de procesamiento secuencial."""
        ctx = self._ctx
        assert ctx is not None
        logger.info("Sequential processing loop started")
        chunk_index = 0

        try:
            while not ctx.stop_event.is_set():
                if not ctx.input_source:
                    time.sleep(0.1)
                    continue

                data = ctx.input_source.get_next_chunk()
                if data is None:
                    time.sleep(0.01)
                    continue

                data.chunk_index = chunk_index
                data.correlation_id = str(uuid.uuid4())
                data.timestamp = time.time()

                start_time = time.perf_counter()
                data = self._process_modules_with_tracking(data)

                if ctx.output_sink and data:
                    try:
                        ctx.output_sink.write(data)
                    except Exception as e:
                        self._log("error", f"Output sink error: {e}")

                elapsed = time.perf_counter() - start_time
                ctx.metrics.chunks_processed += 1
                ctx.metrics.total_processing_time += elapsed

                chunk_index += 1

        except Exception as e:
            self._log("error", f"Sequential loop error: {e}")
            from core.schemas import PipelineState

            ctx.set_state(PipelineState.ERROR)

    def get_metrics(self) -> dict[str, Any]:
        metrics = super().get_metrics()
        metrics["strategy"] = "sequential"
        return metrics


class ThreadParallelStrategy(PipelineStrategy):
    """
    Estrategia paralela con threads - Procesa múltiples chunks concurrently.

    Adecuada para:
    - Módulos CPU-bound
    - Bloqueo I/O (disco, red)
    - Sistemas multi-core

    F170 — Reactive pipeline:
    - Dynamic concurrency based on CPU/GPU load
    - Backpressure from queue occupancy
    """

    def __init__(self, config: StrategyConfig | None = None):
        super().__init__(config)
        self._semaphore = threading.Semaphore(self._config.max_concurrent_chunks)
        self._lock = threading.Lock()
        self._input_thread: threading.Thread | None = None
        self._worker_threads: list[threading.Thread] = []
        self._output_thread: threading.Thread | None = None
        # F170 — Dynamic concurrency
        self._concurrency_target: int = self._config.max_concurrent_chunks
        self._monitor_thread: threading.Thread | None = None
        self._monitor_interval: float = 5.0
        # F170 — Backpressure state
        self._backpressure_sleep: float = 0.01  # normal sleep between input polls

    def process_chunk(self, data: PipelineData) -> PipelineData:
        """Procesa un chunk con semáforo para limitar concurrencia."""
        with self._semaphore:
            with self._lock:
                self._active_chunks += 1

            try:
                start_time = time.time()
                data = self._process_modules(data)

                with self._lock:
                    self._chunks_processed += 1
                    self._total_time += time.time() - start_time

                return data
            except Exception as e:
                with self._lock:
                    self._chunks_failed += 1
                logger.error("ThreadParallelStrategy: chunk %s failed: %s", data.chunk_index, e)
                raise
            finally:
                with self._lock:
                    self._active_chunks -= 1

    def start_threads(self, ctx: PipelineContext) -> None:
        """Start input, worker, output, and monitor threads."""
        super().start_threads(ctx)

        # F170 — Initialize adaptive config from context
        if ctx and ctx.adaptive_config:
            self._backpressure_sleep = 0.01

        self._input_thread = threading.Thread(
            target=self._input_thread_loop,
            daemon=True,
            name="pipeline-input",
        )
        self._input_thread.start()

        initial_workers = (
            ctx.semaphore._value if hasattr(ctx.semaphore, "_value") else self._config.max_concurrent_chunks
        )
        self._concurrency_target = initial_workers
        self._worker_threads = []
        for i in range(initial_workers):
            worker = threading.Thread(
                target=self._worker_thread_loop,
                daemon=True,
                name=f"pipeline-worker-{i}",
            )
            worker.start()
            self._worker_threads.append(worker)

        self._output_thread = threading.Thread(
            target=self._output_thread_loop,
            daemon=True,
            name="pipeline-output",
        )
        self._output_thread.start()

        # F170 — Start adaptive monitor thread
        if ctx and ctx.hardware_monitor and ctx.adaptive_config and ctx.adaptive_config.get("enabled", True):
            self._monitor_thread = threading.Thread(
                target=self._adaptive_monitor_loop,
                daemon=True,
                name="pipeline-adaptive-monitor",
            )
            self._monitor_thread.start()

    def stop_threads(self) -> None:
        """Join all threads with timeout and warnings for stuck threads."""
        threads = [
            ("input", self._input_thread),
            *[(f"worker-{i}", w) for i, w in enumerate(self._worker_threads)],
            ("output", self._output_thread),
            ("monitor", self._monitor_thread),
        ]
        for name, thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=5.0)
                if thread.is_alive():
                    logger.warning(f"Thread '{name}' did not stop within 5s timeout")
        self._input_thread = None
        self._worker_threads.clear()
        self._output_thread = None
        self._monitor_thread = None

    def _adaptive_monitor_loop(self) -> None:
        """F170 — Monitor CPU/GPU and adjust concurrency target."""
        ctx = self._ctx
        assert ctx is not None
        adaptive = ctx.adaptive_config or {}
        cpu_high = adaptive.get("cpu_high_threshold", 80.0)
        gpu_high = adaptive.get("gpu_high_threshold", 85.0)
        cpu_low = adaptive.get("cpu_low_threshold", 40.0)
        gpu_low = adaptive.get("gpu_low_threshold", 50.0)
        min_conc = adaptive.get("min_concurrent", 1)
        max_conc = adaptive.get("max_concurrent", self._config.max_concurrent_chunks)

        logger.info(
            f"Adaptive monitor started: cpu_high={cpu_high}% gpu_high={gpu_high}% concurrency=[{min_conc}..{max_conc}]"
        )

        while not ctx.stop_event.is_set():
            try:
                hw = ctx.hardware_monitor
                if hw:
                    metrics = hw.get_system_metrics()
                    cpu = metrics.get("cpu_percent", 0.0)
                    gpu = metrics.get("gpu_percent", 0.0)
                    gpu_avail = metrics.get("gpu_available", False)

                    current = self._concurrency_target
                    if cpu > cpu_high or (gpu_avail and gpu > gpu_high):
                        new_target = max(min_conc, current - 1)
                    elif cpu < cpu_low and (not gpu_avail or gpu < gpu_low):
                        new_target = min(max_conc, current + 1)
                    else:
                        new_target = current

                    if new_target != current:
                        logger.info(f"Adaptive concurrency: {current} → {new_target} (cpu={cpu:.0f}% gpu={gpu:.0f}%)")
                        self._concurrency_target = new_target
                else:
                    logger.debug("Hardware monitor not available, skipping adaptive adjustment")
            except Exception as e:
                logger.exception("Adaptive monitor error: %s", e)

            time.sleep(self._monitor_interval)

    def _input_thread_loop(self) -> None:
        """Thread de lectura de entrada con backpressure (F170)."""
        ctx = self._ctx
        assert ctx is not None
        logger.info("Input thread started")
        chunk_index = 0
        bp_ratio = (ctx.adaptive_config or {}).get("backpressure_queue_ratio", 0.7)
        bp_threshold = int(ctx.buffer_size * bp_ratio)
        # F181: Idle timeout detection
        _idle_start: float | None = None
        _idle_warned = False
        _max_idle_before_warn = 60.0

        try:
            while not ctx.stop_event.is_set():
                if not ctx.input_source:
                    time.sleep(0.1)
                    continue

                # F170 — Backpressure: slow down if queues are filling up
                output_qsize = ctx.output_queue.qsize()
                chunk_qsize = ctx.chunk_queue.qsize()
                if output_qsize > bp_threshold or chunk_qsize > bp_threshold:
                    bp_sleep = min(0.5, 0.01 + 0.05 * max(output_qsize, chunk_qsize))
                    time.sleep(bp_sleep)

                data = ctx.input_source.get_next_chunk()
                if data is None:
                    # F181: Warn if input has been idle for too long
                    if _idle_start is None:
                        _idle_start = time.time()
                        _idle_warned = False
                    elif not _idle_warned and (time.time() - _idle_start) > _max_idle_before_warn:
                        self._log("warning", f"Input source idle for {_max_idle_before_warn:.0f}s — no chunks received")
                        _idle_warned = True
                    time.sleep(0.01)
                    continue

                # Reset idle tracking when data arrives
                _idle_start = None
                _idle_warned = False

                data.chunk_index = chunk_index
                data.timestamp = time.time()

                processor = ChunkProcessor(
                    chunk_index=chunk_index,
                    timestamp=time.time(),
                    data=data,
                )

                with ctx.lock:
                    ctx.results[chunk_index] = processor

                try:
                    ctx.chunk_queue.put(processor, timeout=1.0)
                except queue.Full:
                    self._log("warning", f"Queue full, dropping chunk {chunk_index}")

                chunk_index += 1

        except Exception as e:
            self._log("error", f"Input thread error: {e}")

    def _worker_thread_loop(self) -> None:
        """Thread worker para procesamiento paralelo con adaptación dinámica (F170)."""
        ctx = self._ctx
        assert ctx is not None
        logger.info("Worker thread started")

        try:
            while not ctx.stop_event.is_set():
                # F170 — Dynamic concurrency: back off if over target
                with self._lock:
                    if self._active_chunks >= self._concurrency_target:
                        time.sleep(0.2)
                        continue

                try:
                    processor = ctx.chunk_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                data = processor.data
                if data is None:
                    ctx.chunk_queue.task_done()
                    continue

                start_time = time.perf_counter()

                try:
                    data = self._process_modules_with_tracking(data, processor)
                    processor.data = data
                    elapsed = time.perf_counter() - start_time
                    processor.stages_completed["total"] = elapsed

                    ctx.output_queue.put(processor)

                except Exception as e:
                    processor.error = str(e)
                    self._log("error", f"Worker error processing chunk {processor.chunk_index}: {e}")
                finally:
                    ctx.chunk_queue.task_done()

        except Exception as e:
            self._log("error", f"Worker thread error: {e}")

    def _output_thread_loop(self) -> None:
        """Thread de escritura de salida ordenada con timeout para chunks perdidos."""
        ctx = self._ctx
        assert ctx is not None
        logger.info("Output thread started")
        pending: dict[int, ChunkProcessor] = {}
        next_expected = 0
        _last_pending_time: float = 0.0
        lost_timeout = ctx.lost_chunk_timeout
        # F170 — Chunk duration adaptation state
        _last_adapt_chunk = 0

        try:
            while not ctx.stop_event.is_set():
                try:
                    processor = ctx.output_queue.get(timeout=0.1)
                    pending[processor.chunk_index] = processor
                    _last_pending_time = time.time()
                except queue.Empty:
                    pass

                while next_expected in pending:
                    processor = pending.pop(next_expected)

                    if ctx.output_sink and processor.data and not processor.error:
                        try:
                            ctx.output_sink.write(processor.data)
                        except Exception as e:
                            self._log("error", f"Output error chunk {next_expected}: {e}")

                    with ctx.lock:
                        ctx.results.pop(next_expected, None)

                    ctx.metrics.chunks_processed += 1
                    ctx.metrics.total_processing_time += processor.stages_completed.get("total", 0)

                    for mod_name, mod_time_ms in processor.stages_completed.items():
                        if mod_name != "total":
                            ctx.metrics.record_module_timing(mod_name, mod_time_ms)

                    if ctx.on_chunk_complete and processor.data:
                        ctx.on_chunk_complete(next_expected, processor.data)

                    ctx.output_queue.task_done()
                    next_expected += 1
                    _last_pending_time = time.time()

                    # F170 — Chunk duration adaptation
                    if (
                        ctx.adaptive_config
                        and ctx.adaptive_config.get("chunk_duration_adapt", True)
                        and ctx.on_chunk_duration_change
                    ):
                        interval = ctx.adaptive_config.get("adaptation_interval_chunks", 10)
                        chunks_since = ctx.metrics.chunks_processed - _last_adapt_chunk
                        if chunks_since >= interval and ctx.metrics.avg_processing_time > 0:
                            _last_adapt_chunk = ctx.metrics.chunks_processed
                            avg = ctx.metrics.avg_processing_time
                            current_dur = ctx.chunk_duration
                            ratio = avg / current_dur if current_dur > 0 else 0
                            high_ratio = ctx.adaptive_config.get("chunk_duration_ratio_high", 0.8)
                            low_ratio = ctx.adaptive_config.get("chunk_duration_ratio_low", 0.3)
                            if ratio > high_ratio and current_dur < 60:
                                new_dur = min(60, int(current_dur * 1.5))
                                self._log(
                                    "info",
                                    f"Chunk duration adaptation: {current_dur}s → {new_dur}s "
                                    f"(avg_proc={avg:.1f}s, ratio={ratio:.2f})",
                                )
                                ctx.chunk_duration = new_dur
                                ctx.on_chunk_duration_change(float(new_dur))
                            elif ratio < low_ratio and current_dur > 2:
                                new_dur = max(2, int(current_dur / 1.5))
                                self._log(
                                    "info",
                                    f"Chunk duration adaptation: {current_dur}s → {new_dur}s "
                                    f"(avg_proc={avg:.1f}s, ratio={ratio:.2f})",
                                )
                                ctx.chunk_duration = new_dur
                                ctx.on_chunk_duration_change(float(new_dur))

                if pending and _last_pending_time > 0 and (time.time() - _last_pending_time) > lost_timeout:
                    self._log(
                        "warning",
                        f"Chunk {next_expected} appears lost after {lost_timeout}s — skipping to unblock output.",
                    )
                    with ctx.lock:
                        ctx.results.pop(next_expected, None)
                    ctx.metrics.chunks_failed += 1
                    next_expected += 1
                    _last_pending_time = time.time()

        except Exception as e:
            self._log("error", f"Output thread error: {e}")
        finally:
            # ROB-03: drain remaining pending items so task_done() is called
            # for every get(). Without this, queue.join() hangs on shutdown.
            import contextlib

            for idx in list(pending.keys()):
                pending.pop(idx, None)
                with contextlib.suppress(Exception):
                    ctx.output_queue.task_done()

    def get_metrics(self) -> dict[str, Any]:
        metrics = super().get_metrics()
        metrics["strategy"] = "thread_parallel"
        return metrics


class AsyncIOStrategy(PipelineStrategy):
    """
    Estrategia asyncio nativa - Procesa chunks concurrentemente con async/await.

    Adecuada para:
    - Alta concurrencia (muchos chunks)
    - I/O no bloqueante
    - Integración con servidores async (FastAPI)
    """

    def __init__(self, config: StrategyConfig | None = None):
        super().__init__(config)
        self._semaphore: asyncio.Semaphore | None = None
        self._async_tasks: list[asyncio.Task[Any]] = []
        self._worker_threads: list[threading.Thread] = []

    async def process_chunk_async(self, data: PipelineData) -> PipelineData:
        """Procesa un chunk de forma asíncrona."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._config.max_concurrent_chunks)

        async with self._semaphore:
            self._active_chunks += 1
            try:
                start_time = time.time()
                data = await asyncio.get_running_loop().run_in_executor(None, self._process_modules, data)

                self._chunks_processed += 1
                self._total_time += time.time() - start_time
                return data
            except Exception as e:
                self._chunks_failed += 1
                logger.error("AsyncIOStrategy: chunk %s failed: %s", data.chunk_index, e)
                raise
            finally:
                self._active_chunks -= 1

    def process_chunk(self, data: PipelineData) -> PipelineData:
        """Interfaz síncrona - crea un nuevo event loop si es necesario."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.process_chunk_async(data))
                    return future.result()
        except RuntimeError:
            pass
        return asyncio.run(self.process_chunk_async(data))

    def start_threads(self, ctx: PipelineContext) -> None:
        """Start the asyncio processing loop in a dedicated thread."""
        super().start_threads(ctx)
        self._ctx = ctx
        thread = threading.Thread(
            target=asyncio.run,
            args=(self._run_async_loop(),),
            daemon=True,
            name="asyncio-loop",
        )
        thread.start()
        self._worker_threads.append(thread)

    def stop_threads(self) -> None:
        """Stop async pipeline threads.

        ``stop_event`` is already set by pipeline.stop(), so the async
        loop in the worker thread will exit on its own. This method just
        waits for the thread to finish. The old async ``stop_threads``
        was changed to sync because it's called from the synchronous
        ``_sync_stop()`` and awaiting a coroutine from a thread executor
        was silently a no-op (the coroutine was created but never awaited).
        """
        for idx, thread in enumerate(self._worker_threads):
            if thread.is_alive():
                thread.join(timeout=5.0)
                if thread.is_alive():
                    logger.warning(f"AsyncIO worker thread {idx} did not stop within 5s timeout")
        self._worker_threads.clear()

    async def _run_async_loop(self) -> None:
        """Bucle principal asyncio."""
        ctx = self._ctx
        assert ctx is not None
        logger.info("Asyncio processing loop started")
        chunk_index = 0

        try:
            while not ctx.stop_event.is_set():
                if not ctx.input_source:
                    await asyncio.sleep(0.1)
                    continue

                data = (
                    await ctx.input_source.get_next_chunk()
                    if asyncio.iscoroutinefunction(ctx.input_source.get_next_chunk)
                    else ctx.input_source.get_next_chunk()
                )
                if data is None:
                    await asyncio.sleep(0.01)
                    continue

                data.chunk_index = chunk_index
                data.timestamp = time.time()

                task = asyncio.create_task(self._process_chunk_async_full(data))
                self._async_tasks.append(task)

                chunk_index += 1

        except asyncio.CancelledError:
            logger.info("Async loop cancelled")
        except Exception as e:
            self._log("error", f"Async loop error: {e}")
            from core.schemas import PipelineState

            ctx.set_state(PipelineState.ERROR)

    async def _process_chunk_async_full(self, data: PipelineData) -> PipelineData:
        """Procesar un chunk completo en modo asyncio (modules + output + metrics)."""
        ctx = self._ctx
        assert ctx is not None

        if hasattr(self._semaphore or asyncio.Semaphore(1), "__aenter__"):
            sem = self._semaphore or asyncio.Semaphore(self._config.max_concurrent_chunks)
            async with sem:
                return await self._process_chunk_unlocked(data)

        await asyncio.to_thread(self._semaphore.acquire if self._semaphore else threading.Semaphore(1).acquire)
        try:
            return await self._process_chunk_unlocked(data)
        finally:
            if self._semaphore:
                self._semaphore.release()

    async def _process_chunk_unlocked(self, data: PipelineData) -> PipelineData:
        """Process a chunk assuming concurrency limit is already acquired."""
        ctx = self._ctx
        assert ctx is not None
        chunk_start = time.perf_counter()
        chunk_index = data.chunk_index

        try:
            for module in ctx.modules:
                if ctx.stop_event.is_set():
                    break
                if not module.enabled:
                    continue

                try:
                    if asyncio.iscoroutinefunction(module.process):
                        data = await module.process(data)
                    else:
                        data = module.process(data)
                    if module.state.value == "degraded" and not getattr(module, "is_critical", True):
                        self._log("warning", f"Non-critical module {module.name} degraded, continuing pipeline")
                except Exception:
                    if not getattr(module, "is_critical", True):
                        self._log("warning", f"Non-critical module {module.name} failed, continuing in degraded mode")
                        continue
                    raise

            if ctx.output_sink and data:
                if asyncio.iscoroutinefunction(ctx.output_sink.write):
                    await ctx.output_sink.write(data)
                else:
                    ctx.output_sink.write(data)

            elapsed = time.perf_counter() - chunk_start
            ctx.metrics.chunks_processed += 1
            ctx.metrics.total_processing_time += elapsed

            if ctx.on_chunk_complete:
                ctx.on_chunk_complete(chunk_index, data)

            return data

        except Exception as e:
            ctx.metrics.chunks_failed += 1
            self._log("error", f"Error processing chunk {chunk_index}: {e}")
            raise

    def get_metrics(self) -> dict[str, Any]:
        metrics = super().get_metrics()
        metrics["strategy"] = "asyncio"
        return metrics


def create_strategy(mode: str, config: StrategyConfig | None = None) -> PipelineStrategy:
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
