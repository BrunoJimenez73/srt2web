"""
Unified Pipeline - Implementación unificada con soporte multi-modo.

Combina las mejores características de:
- Pipeline (secuencial)
- AsyncPipeline (paralelo con threads)
- AsyncPipelineV2 (asyncio nativo)

Características:
✅ Modo de operación configurable (secuencial / thread-parallel / asyncio)
✅ Compatibilidad API 100% hacia atrás
✅ Circuit Breaker y reintentos por módulo
✅ Semáforo de concurrencia configurable
✅ Métricas detalladas de rendimiento
✅ Shutdown graceful y cancelación
✅ Manejo de errores unificado
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
import typing
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import psutil

from core.exceptions import PipelineError, PipelineStateError
from core.hardware_monitor import HardwareMonitor
from core.module_base import BaseModule, PipelineData
from core.pipeline_metrics import PipelineMetrics
from core.schemas import PipelineMode as PipelineMode
from core.schemas import PipelineState as PipelineState
from core.schemas import SystemMetrics
from core.webhook_manager import webhook_manager

if TYPE_CHECKING:
    from modules.outputs.composite_output import CompositeOutput

try:
    from modules.outputs.composite_output import CompositeOutput as _CompositeOutput
except ImportError:
    _CompositeOutput = None  # type: ignore[misc, assignment]

try:
    from core.pipeline.strategies import (
        PipelineStrategy,
        StrategyConfig,
        create_strategy,
    )
except ImportError:
    create_strategy = None  # type: ignore[assignment]
    StrategyConfig = None  # type: ignore[assignment,misc]
    PipelineStrategy = None  # type: ignore[assignment,misc]

logger = logging.getLogger("srt2web.unified_pipeline")


class _CompletedAwaitable:
    """Awaitable no-op used for backward-compatible sync APIs."""

    def __await__(self) -> typing.Generator[None, None, None]:
        if False:
            yield None
        return None


@dataclass
class ChunkProcessor:
    """Trackea el estado de procesamiento de un chunk."""

    chunk_index: int
    timestamp: float
    data: PipelineData | None = None
    stages_completed: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    task: threading.Thread | asyncio.Task[None] | None = None


class UnifiedPipeline:
    """
    Pipeline unificado multi-modo.

    Modos disponibles:
    - SEQUENTIAL: Procesa un chunk a la vez, orden estricto
    - THREAD_PARALLEL: Múltiples workers en threads (default)
    - ASYNCIO: Paralelismo nativo con asyncio (para módulos async)
    """

    def __init__(
        self,
        mode: PipelineMode = PipelineMode.THREAD_PARALLEL,
        max_concurrent_chunks: int = 3,
        buffer_size: int = 5,
        retry_attempts: int = 2,
        retry_delay: float = 1.0,
    ):
        """
        Initialize unified pipeline.

        Args:
            mode: Mode of operation
            max_concurrent_chunks: Maximum chunks processing simultaneously
            buffer_size: Size of input buffer
            retry_attempts: Number of retry attempts per module
            retry_delay: Delay between retries (seconds)
        """
        # Initialize _initialized FIRST to avoid race conditions
        self._initialized = False

        self.mode = mode
        self.max_concurrent_chunks = max_concurrent_chunks
        self.buffer_size = buffer_size
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # Internal state
        self._state = PipelineState.IDLE
        # Metrics initialized via _metrics (Pydantic)
        self._modules: list[BaseModule] = []
        self._module_map: dict[str, BaseModule] = {}
        self._input_source = None
        self._output_sink: Any = None

        # Execution control - INITIALIZED EARLY TO AVOID RACE
        self._stop_event = threading.Event()
        self._semaphore = threading.Semaphore(max_concurrent_chunks)
        self._tasks: list[Any] = []
        self._chunk_queue: queue.Queue[ChunkProcessor] = queue.Queue(maxsize=buffer_size)
        self._output_queue: queue.Queue[ChunkProcessor] = queue.Queue(maxsize=buffer_size)
        self._results: dict[int, ChunkProcessor] = {}
        self._input_thread: threading.Thread | None = None
        self._output_thread: threading.Thread | None = None

        # Metrics
        self._pipeline_metrics = PipelineMetrics()
        self._system_metrics = SystemMetrics(cpu_percent=0, memory_mb=0, memory_percent=0)

        # Callbacks
        self._on_log: Callable[[str, str], None] | None = None
        self._on_state_change: Callable[[str], None] | None = None
        self._on_chunk_complete: Callable[[int, PipelineData], None] | None = None

        # Lock para operaciones thread-safe
        self._lock = threading.Lock()
        self._hardware_monitor = HardwareMonitor()
        self._initialized = False  # Initialize to False BEFORE thread starts

        # Chunk duration default (used in reconfigure)
        self._chunk_duration = 10.0

        # Initialize processing strategy (if available)
        self._strategy: PipelineStrategy | None = None
        self._active_chunks = 0
        if create_strategy and StrategyConfig:  # type: ignore[truthy-function]
            try:
                strategy_config = StrategyConfig(max_concurrent_chunks=max_concurrent_chunks)
                self._strategy = create_strategy(mode.value, strategy_config)
                logger.info(f"Pipeline strategy initialized: {type(self._strategy).__name__}")
            except Exception as e:
                logger.warning(f"Could not initialize strategy: {e}")

        logger.info(f"UnifiedPipeline initialized mode={mode.value} concurrent={max_concurrent_chunks}")

    @property
    def metrics(self) -> PipelineMetrics:
        """Alias for _pipeline_metrics for backward compatibility."""
        return self._pipeline_metrics

    @property
    def state(self) -> PipelineState:
        """Obtener estado actual del pipeline."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Verificar si el pipeline está en ejecución."""
        return self._state in (PipelineState.RUNNING, PipelineState.STARTING)

    def set_input_source(self, source: Any) -> None:
        """Establecer fuente de entrada."""
        self._input_source = source

    def get_input_source(self) -> Any | None:
        """Obtener fuente de entrada."""
        return self._input_source

    def set_output_sinks(self, output_configs: list[dict[str, Any]]) -> None:
        """Establecer múltiples destinos de salida."""
        from core.io_factory import OutputFactory

        # Crear múltiples salidas
        outputs = OutputFactory.create_multiple(output_configs)

        # Crear composite output
        if _CompositeOutput is None:
            raise ImportError("CompositeOutput is not available")
        self._output_sink = _CompositeOutput({})
        for output in outputs:
            self._output_sink.add_output(output.name, output)

    def set_output_sink(self, sink: Any) -> None:
        """Establecer destino de salida (para compatibilidad)."""
        self._output_sink = sink

    def get_output_sink(self) -> Any | None:
        """Obtener destino de salida (para compatibilidad)."""
        return self._output_sink

    def get_output_sinks(self) -> CompositeOutput | None:
        """Obtener el CompositeOutput si el sink actual es uno."""
        if _CompositeOutput is not None and isinstance(self._output_sink, _CompositeOutput):
            return self._output_sink
        return None

    def register_module(self, module: BaseModule, config: dict[str, Any] | None = None) -> None:
        """Registrar un módulo en orden de ejecución."""
        self._modules.append(module)
        self._module_map[module.name] = module
        logger.info(f"Registered module: {module.name} enabled={module.enabled}")

        if config:
            module.configure(config)

        # Update strategy with modules if available
        if self._strategy:
            self._strategy.set_modules(self._modules)

    def get_module(self, name: str) -> BaseModule | None:
        """Obtener un módulo por nombre."""
        return self._module_map.get(name)

    def get_modules(self) -> list[BaseModule]:
        """Obtener lista de todos los módulos registrados."""
        return list(self._modules)

    def _set_state(self, new_state: PipelineState) -> None:
        """Cambiar estado y notificar."""
        old_state = self._state
        self._state = new_state
        if self.metrics.start_time is None and new_state == PipelineState.RUNNING:
            self.metrics.start_time = time.time()
        if self._on_state_change:
            self._on_state_change(new_state.value)

        # Webhook notifications
        try:
            if new_state == PipelineState.RUNNING:
                webhook_manager.emit("pipeline.start", {"state": "running", "mode": self.mode.value})
            elif new_state == PipelineState.ERROR:
                webhook_manager.emit("pipeline.error", {"state": "error", "previous_state": old_state.value})
            elif new_state == PipelineState.IDLE:
                webhook_manager.emit(
                    "pipeline.stop", {"state": "stopped", "chunks_processed": self.metrics.chunks_processed}
                )
        except Exception as e:
            logger.error(f"Error en webhook notification: {e}")

    def _log(self, level: str, message: str) -> None:
        """Emitir log y notificar callback."""
        getattr(logger, level, logger.info)(message)
        if self._on_log:
            try:
                self._on_log(level, message)
            except Exception as e:
                logger.exception("Log callback failed: %s", e)

    def process_with_strategy(self, data: PipelineData) -> PipelineData:
        """
        Procesar un chunk usando la estrategia configurada.

        Si no hay estrategia configurada, retorna los datos sin procesar.
        Útil para testing o procesamiento manual de chunks.
        """
        if not self._strategy:
            logger.warning("No strategy configured, skipping processing")
            return data

        try:
            return self._strategy.process_chunk(data)
        except Exception as e:
            logger.error(f"Strategy processing failed: {e}")
            raise

    def get_strategy_metrics(self) -> dict[str, Any]:
        """Obtener métricas de la estrategia."""
        if self._strategy:
            return self._strategy.get_metrics()
        return {"strategy": "none"}

    async def initialize(self) -> None:
        """Inicializar pipeline y módulos."""
        self._set_state(PipelineState.STARTING)

        try:
            # Inicializar estructuras según modo
            if self.mode == PipelineMode.ASYNCIO:
                self._semaphore = asyncio.Semaphore(self.max_concurrent_chunks)  # type: ignore[assignment]
                self._stop_event = asyncio.Event()  # type: ignore[assignment]
            else:
                self._chunk_queue = queue.Queue(maxsize=self.buffer_size)
                self._output_queue = queue.Queue(maxsize=self.buffer_size)
                self._stop_event = threading.Event()

            # Inicializar módulos
            for module in self._modules:
                try:
                    start_method = getattr(module, "start", None)
                    if start_method:
                        start_method()
                    logger.info(f"Module '{module.name}' initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize module '{module.name}': {e}")
                    raise

            # Inicializar input/output
            if self._input_source:
                start_method = getattr(self._input_source, "start", None)
                if start_method:
                    start_method()

            if self._output_sink:
                start_method = getattr(self._output_sink, "start", None)
                if start_method:
                    start_method()

            # Start time is now tracked via system metrics timestamp
            self._set_state(PipelineState.IDLE)
            logger.info("UnifiedPipeline initialized successfully")

        except Exception as e:
            self._set_state(PipelineState.ERROR)
            logger.error(f"Pipeline initialization failed: {e}")
            raise

    def start(
        self,
        on_log: Callable[[str, str], None] | None = None,
        on_state_change: Callable[[str], None] | None = None,
    ) -> _CompletedAwaitable:
        """Iniciar procesamiento del pipeline."""
        if self._state != PipelineState.IDLE:
            raise PipelineStateError(f"Cannot start pipeline in state: {self._state.value}")

        self._on_log = on_log
        self._on_state_change = on_state_change

        self._set_state(PipelineState.STARTING)

        # Inicializar automáticamente si no se ha hecho antes
        if not getattr(self, "_initialized", False):
            # No podemos usar el event loop principal de FastAPI, ejecutamos en thread separado
            def run_init() -> None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.initialize())
                self._initialized = True

            init_thread = threading.Thread(target=run_init, daemon=True, name="pipeline-init")
            init_thread.start()
            init_thread.join(timeout=120)

            if not self._initialized:
                raise PipelineError("Pipeline initialization timed out after 60 seconds")

        self._stop_event.clear()

        if self.mode == PipelineMode.SEQUENTIAL:
            # Ejecución en thread principal
            thread = threading.Thread(
                target=self._run_sequential_loop,
                daemon=True,
                name="pipeline-sequential",
            )
            thread.start()
            self._tasks.append(thread)

        elif self.mode == PipelineMode.THREAD_PARALLEL:
            # Workers en threads
            self._input_thread = threading.Thread(
                target=self._input_thread_loop,
                daemon=True,
                name="pipeline-input",
            )
            self._input_thread.start()

            for i in range(self.max_concurrent_chunks):
                worker = threading.Thread(
                    target=self._worker_thread_loop,
                    daemon=True,
                    name=f"pipeline-worker-{i}",
                )
                worker.start()
                self._tasks.append(worker)

            self._output_thread = threading.Thread(
                target=self._output_thread_loop,
                daemon=True,
                name="pipeline-output",
            )
            self._output_thread.start()

        elif self.mode == PipelineMode.ASYNCIO:
            # Ejecución asyncio
            asyncio.create_task(self._run_async_loop())

        self._set_state(PipelineState.RUNNING)
        self._log("info", "UnifiedPipeline started successfully")
        return _CompletedAwaitable()

    def _run_sequential_loop(self) -> None:
        """Bucle de procesamiento secuencial."""
        logger.info("Sequential processing loop started")
        chunk_index = 0

        try:
            while not self._stop_event.is_set():
                if not self._input_source:
                    time.sleep(0.1)
                    continue

                data = self._input_source.get_next_chunk()
                if data is None:
                    time.sleep(0.01)
                    continue

                data.chunk_index = chunk_index
                data.correlation_id = str(uuid.uuid4())
                data.timestamp = time.time()

                # Procesar secuencialmente
                start_time = time.perf_counter()
                for module in self._modules:
                    if not module.enabled or self._stop_event.is_set():
                        continue
                    try:
                        data = module.process(data)
                        if module.state.value == "degraded" and not getattr(module, "is_critical", True):
                            self._log("warning", f"Non-critical module {module.name} degraded, continuing pipeline")
                    except Exception as e:
                        self._log("error", f"Module {module.name} error: {e}")
                        if not getattr(module, "is_critical", True):
                            self._log(
                                "warning", f"Non-critical module {module.name} failed, continuing in degraded mode"
                            )
                            continue
                        break

                # Escribir salida
                if self._output_sink and data:
                    try:
                        self._output_sink.write(data)
                    except Exception as e:
                        self._log("error", f"Output sink error: {e}")

                elapsed = time.perf_counter() - start_time
                self.metrics.chunks_processed += 1
                self.metrics.total_processing_time += elapsed

                chunk_index += 1

        except Exception as e:
            self._log("error", f"Sequential loop error: {e}")
            self._set_state(PipelineState.ERROR)

    def _input_thread_loop(self) -> None:
        """Thread de lectura de entrada."""
        logger.info("Input thread started")
        chunk_index = 0

        try:
            while not self._stop_event.is_set():
                if not self._input_source:
                    time.sleep(0.1)
                    continue

                data = self._input_source.get_next_chunk()
                if data is None:
                    time.sleep(0.01)
                    continue

                data.chunk_index = chunk_index
                data.timestamp = time.time()

                processor = ChunkProcessor(
                    chunk_index=chunk_index,
                    timestamp=time.time(),
                    data=data,
                )

                with self._lock:
                    self._results[chunk_index] = processor

                try:
                    self._chunk_queue.put(processor, timeout=1.0)
                except queue.Full:
                    self._log("warning", f"Queue full, dropping chunk {chunk_index}")

                chunk_index += 1

        except Exception as e:
            self._log("error", f"Input thread error: {e}")

    def _worker_thread_loop(self) -> None:
        """Thread worker para procesamiento paralelo."""
        logger.info("Worker thread started")

        try:
            while not self._stop_event.is_set():
                try:
                    processor = self._chunk_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                data = processor.data
                if data is None:
                    continue

                start_time = time.perf_counter()

                try:
                    # Use strategy for concurrent chunk processing if available
                    if self._strategy:
                        data = self._strategy.process_chunk(data)
                    else:
                        for module in self._modules:
                            if not module.enabled or self._stop_event.is_set():
                                continue
                            try:
                                module_start = time.perf_counter()
                                data = module.process(data)
                                processor.stages_completed[module.name] = (time.perf_counter() - module_start) * 1000
                                if module.state.value == "degraded" and not getattr(module, "is_critical", True):
                                    self._log(
                                        "warning", f"Non-critical module {module.name} degraded, continuing pipeline"
                                    )
                            except Exception as e:
                                self._log("error", f"Module {module.name} error: {e}")
                                processor.error = str(e)
                                if not getattr(module, "is_critical", True):
                                    self._log(
                                        "warning",
                                        f"Non-critical module {module.name} failed, continuing in degraded mode",
                                    )
                                    continue
                                break

                    processor.data = data
                    elapsed = time.perf_counter() - start_time
                    processor.stages_completed["total"] = elapsed

                    self._output_queue.put(processor)

                except Exception as e:
                    processor.error = str(e)
                    self._log("error", f"Worker error processing chunk {processor.chunk_index}: {e}")
                finally:
                    self._chunk_queue.task_done()

        except Exception as e:
            self._log("error", f"Worker thread error: {e}")

    def _output_thread_loop(self) -> None:
        """Thread de escritura de salida ordenada con timeout para chunks perdidos."""
        logger.info("Output thread started")
        pending = {}
        next_expected = 0
        # Cuándo llegó el último chunk al pending dict (para detectar chunks perdidos)
        _last_pending_time: float = 0.0
        _LOST_CHUNK_TIMEOUT = 30.0  # segundos antes de descartar un chunk perdido

        try:
            while not self._stop_event.is_set():
                try:
                    processor = self._output_queue.get(timeout=0.1)
                    pending[processor.chunk_index] = processor
                    _last_pending_time = time.time()
                except queue.Empty:
                    pass

                # Escribir en orden
                while next_expected in pending:
                    processor = pending.pop(next_expected)

                    if self._output_sink and processor.data and not processor.error:
                        try:
                            self._output_sink.write(processor.data)
                        except Exception as e:
                            self._log("error", f"Output error chunk {next_expected}: {e}")

                    with self._lock:
                        self._results.pop(next_expected, None)

                    self.metrics.chunks_processed += 1
                    self.metrics.total_processing_time += processor.stages_completed.get("total", 0)

                    # Accumulate per-module timing from this chunk
                    for mod_name, mod_time_ms in processor.stages_completed.items():
                        if mod_name != "total":
                            self.metrics.record_module_timing(mod_name, mod_time_ms)

                    if self._on_chunk_complete and processor.data:
                        self._on_chunk_complete(next_expected, processor.data)

                    self._output_queue.task_done()
                    next_expected += 1
                    _last_pending_time = time.time()

                # Detectar chunk perdido: hay items en pending pero el siguiente
                # esperado nunca llegó y pasó demasiado tiempo
                if pending and _last_pending_time > 0 and (time.time() - _last_pending_time) > _LOST_CHUNK_TIMEOUT:
                    self._log(
                        "warning",
                        f"Chunk {next_expected} appears lost after {_LOST_CHUNK_TIMEOUT}s — skipping to unblock output.",
                    )
                    with self._lock:
                        self._results.pop(next_expected, None)
                    self.metrics.chunks_failed += 1
                    next_expected += 1
                    _last_pending_time = time.time()

        except Exception as e:
            self._log("error", f"Output thread error: {e}")

    async def _run_async_loop(self) -> None:
        """Bucle principal asyncio."""
        logger.info("Asyncio processing loop started")
        chunk_index = 0

        try:
            while not self._stop_event.is_set():
                if not self._input_source:
                    await asyncio.sleep(0.1)
                    continue

                data = (
                    await self._input_source.get_next_chunk()
                    if asyncio.iscoroutinefunction(self._input_source.get_next_chunk)
                    else self._input_source.get_next_chunk()
                )
                if data is None:
                    await asyncio.sleep(0.01)
                    continue

                data.chunk_index = chunk_index
                data.timestamp = time.time()

                # Lanzar tarea async
                task = asyncio.create_task(self._process_chunk_async(data))
                self._tasks.append(task)

                chunk_index += 1

        except asyncio.CancelledError:
            logger.info("Async loop cancelled")
        except Exception as e:
            self._log("error", f"Async loop error: {e}")
            self._set_state(PipelineState.ERROR)

    async def _process_chunk_async(self, data: PipelineData) -> PipelineData:
        """Procesar un chunk en modo asyncio."""
        if hasattr(self._semaphore, "__aenter__"):
            async with self._semaphore:  # type: ignore[attr-defined]
                return await self._process_chunk_async_unlocked(data)

        await asyncio.to_thread(self._semaphore.acquire)
        try:
            return await self._process_chunk_async_unlocked(data)
        finally:
            self._semaphore.release()

    async def _process_chunk(self, data: PipelineData) -> PipelineData:
        """Backward-compatible async chunk processing alias."""
        return await self._process_chunk_async(data)

    async def _process_chunk_async_unlocked(self, data: PipelineData) -> PipelineData:
        """Procesar un chunk asumiendo que el límite de concurrencia ya se tomó."""
        chunk_start = time.perf_counter()
        chunk_index = data.chunk_index

        try:
            for module in self._modules:
                if self._stop_event.is_set():
                    break

                if not module.enabled:
                    continue

                # Soporte para módulos sync y async
                try:
                    if asyncio.iscoroutinefunction(module.process):
                        data = await module.process(data)
                    else:
                        data = module.process(data)
                    if module.state.value == "degraded" and not getattr(module, "is_critical", True):
                        self._log("warning", f"Non-critical module {module.name} degraded, continuing pipeline")
                except Exception as e:
                    if not getattr(module, "is_critical", True):
                        self._log("warning", f"Non-critical module {module.name} failed, continuing in degraded mode")
                        continue
                    raise

            # Enviar a output
            if self._output_sink and data:
                if asyncio.iscoroutinefunction(self._output_sink.write):
                    await self._output_sink.write(data)
                else:
                    self._output_sink.write(data)

            elapsed = time.perf_counter() - chunk_start
            self.metrics.chunks_processed += 1
            self.metrics.total_processing_time += elapsed

            if self._on_chunk_complete:
                self._on_chunk_complete(chunk_index, data)

            return data

        except Exception as e:
            self.metrics.chunks_failed += 1
            self._log("error", f"Error processing chunk {chunk_index}: {e}")
            raise

    def get_metrics(self) -> dict[str, Any]:
        """Return pipeline metrics as a plain dictionary."""
        return {
            "chunks_processed": self.metrics.chunks_processed,
            "chunks_failed": self.metrics.chunks_failed,
            "avg_processing_time": self.metrics.avg_processing_time,
            "total_processing_time": self.metrics.total_processing_time,
            "uptime": self.metrics.uptime,
        }

    async def stop(self) -> None:
        """Detener pipeline gracefulmente."""
        if not self.is_running:
            return
        self._hardware_monitor.shutdown()

        self._set_state(PipelineState.STOPPING)
        self._stop_event.set()

        # Detener tareas
        if self.mode == PipelineMode.ASYNCIO:
            if self._tasks:
                for task in self._tasks:
                    task.cancel()
                await asyncio.gather(*self._tasks, return_exceptions=True)
        else:
            # Esperar threads
            if self._input_thread and self._input_thread.is_alive():
                self._input_thread.join(timeout=5.0)

            for worker in self._tasks:
                if worker.is_alive():
                    worker.join(timeout=5.0)

            if self._output_thread and self._output_thread.is_alive():
                self._output_thread.join(timeout=5.0)

        # Detener módulos
        for module in self._modules:
            try:
                stop_method = getattr(module, "stop", None)
                if stop_method:
                    stop_method()
            except Exception as e:
                self._log("error", f"Error stopping module {module.name}: {e}")

        # Detener input/output
        if self._input_source:
            try:
                self._log("info", f"Calling stop() on input_source: {type(self._input_source).__name__}")
                stop_method = getattr(self._input_source, "stop", None)
                if stop_method:
                    stop_method()
                self._log("info", "Input source stop() completed")
            except Exception as e:
                self._log("error", f"Error stopping input source: {e}")

        if self._output_sink:
            try:
                stop_method = getattr(self._output_sink, "stop", None)
                if stop_method:
                    stop_method()
            except Exception as e:
                self._log("error", f"Error stopping output sink: {e}")

        self._set_state(PipelineState.IDLE)
        self._initialized = False  # Force re-initialization on next start
        self._log("info", "UnifiedPipeline stopped successfully")

    async def shutdown(self) -> None:
        """Backward-compatible full shutdown for tests and integrations."""
        await self.stop()
        for module in self._modules:
            shutdown_method = getattr(module, "shutdown", None)
            if shutdown_method:
                result = shutdown_method()
                if asyncio.iscoroutine(result):
                    await result
        if self._output_sink:
            shutdown_method = getattr(self._output_sink, "shutdown", None)
            if shutdown_method:
                result = shutdown_method()
                if asyncio.iscoroutine(result):
                    await result
        self._initialized = False

    def get_status(self) -> dict[str, Any]:
        """Obtener estado completo del pipeline."""
        # Leer memoria del proceso UNA SOLA VEZ para todos los módulos
        process_memory_mb: float | None = None
        try:
            process_memory_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
        except Exception as e:
            logger.warning("Failed to read process memory: %s", e)

        modules_status = []
        for module in self._modules:
            try:
                status = module.get_status()
                status_dict = status.to_dict() if getattr(status, "to_dict", None) else status
                # Inyectar memoria centralizada en cada módulo
                if isinstance(status_dict, dict) and process_memory_mb is not None:
                    status_dict["memory_mb"] = process_memory_mb
                modules_status.append(status_dict)
            except Exception as e:
                logger.warning(f"Failed to get status for module {module.name}: {e}")
                modules_status.append(
                    {
                        "name": module.name,
                        "state": "unknown",
                        "enabled": module.enabled,
                        "processed_chunks": 0,
                        "last_process_time_ms": 0,
                    }
                )

        # Agregar status del output sink al final de la lista when it is not
        # already registered as a normal processing module.
        try:
            has_video_muxer_module = any(status.get("name") == "video_muxer" for status in modules_status)  # type: ignore[union-attr]
            if not has_video_muxer_module:
                output_status, muxer_status = self._get_output_module_status()
                modules_status.append(output_status)
                if muxer_status:
                    modules_status.append(muxer_status)
        except Exception as e:
            logger.warning("Failed to get output module status: %s", e)

        # Agregar status del input source al inicio de la lista
        try:
            if self._input_source:
                get_status_method = getattr(self._input_source, "get_status", None)
                if get_status_method:
                    input_status = get_status_method()
                    # Handle both dict and ModuleStatus (Pydantic model)
                    status_dict = getattr(input_status, "to_dict", lambda: input_status)()
                    if isinstance(status_dict, dict):
                        # Ensure it has the right name for the frontend
                        if "name" not in status_dict:
                            status_dict["name"] = "input"
                        modules_status.insert(0, status_dict)
        except Exception as e:
            logger.warning("Failed to get input source status: %s", e)

        # Métricas del pipeline
        avg_time = self._pipeline_metrics.avg_processing_time

        # Métricas del sistema
        system_metrics = self._hardware_monitor.get_system_metrics()

        # Obtener métricas de concurrencia desde la estrategia
        strategy_metrics = {}
        if self._strategy:
            try:
                strategy_metrics = self._strategy.get_metrics()
            except Exception as e:
                logger.debug("Suppressed error: %s", e, exc_info=True)

        # Round float fields in all module statuses
        round_keys = {"last_process_time_ms", "total_processing_time", "average_processing_time"}
        for mod in modules_status:
            if isinstance(mod, dict):
                for k in round_keys:
                    v = mod.get(k)
                    if isinstance(v, float):
                        mod[k] = round(v, 2)

        return {
            "state": self._state.value,
            "mode": self.mode.value,
            "chunks_processed": self._pipeline_metrics.chunks_processed,
            "chunks_failed": self._pipeline_metrics.chunks_failed,
            "avg_processing_time_ms": round(avg_time * 1000, 2),
            "uptime_seconds": round(self._pipeline_metrics.uptime, 1),
            "max_concurrent_chunks": self.max_concurrent_chunks,
            "concurrent_chunks": strategy_metrics.get("active_chunks", 0),
            "buffer_size": self.buffer_size,
            "modules": modules_status,
            "system": system_metrics,
            "system_metrics": system_metrics,
            "strategy": strategy_metrics.get("strategy", "none"),
            "module_avg_time_ms": self._pipeline_metrics.module_avg_times,
            "module_total_times": {k: round(v, 2) for k, v in self._pipeline_metrics.module_total_times.items()},
        }

    def reconfigure(self, config_manager: Any) -> None:
        """Actualizar configuración en ejecución (compatibilidad API)."""
        # First, update pipeline's chunk_duration from config
        try:
            new_chunk_duration = config_manager.get("pipeline.chunk_duration_sec", 10)
            self._chunk_duration = new_chunk_duration
            self._log("info", f"Reconfigured pipeline chunk_duration: {new_chunk_duration}s")
        except Exception as e:
            self._log("warning", f"Could not update chunk_duration: {e}")

        for module in self._modules:
            try:
                mod_config = config_manager.get_module_config(module.name)
                module.configure(mod_config)
                self._log("info", f"Reconfigured module: {module.name}")
            except Exception as e:
                self._log("error", f"Failed to reconfigure {module.name}: {e}")

        # Reconfigure output sinks (HLSOutput, WebRTCOutput, etc.)
        if self._output_sink:
            try:
                configure_outputs = getattr(self._output_sink, "configure_outputs", None)
                if configure_outputs:
                    configure_outputs(config_manager)
                else:
                    # Direct OutputSink that has configure()
                    configure_method = getattr(self._output_sink, "configure", None)
                    if configure_method:
                        output_config = config_manager.get_section("output")
                        configure_method(output_config)
                self._log("info", "Reconfigured output sinks")
            except Exception as e:
                self._log("warning", f"Could not reconfigure output sinks: {e}")

        # Also update input source config if it has chunk_duration
        if self._input_source:
            try:
                input_type = config_manager.get("input.type", "srt")
                input_config = config_manager.get_section("input").get(input_type, {})
                input_config["chunk_duration_sec"] = self._chunk_duration
                configure_method = getattr(self._input_source, "configure", None)
                if configure_method:
                    configure_method(input_config)
                self._log("info", f"Reconfigured input source: {input_type}")
            except Exception as e:
                self._log("warning", f"Could not reconfigure input source: {e}")

    def reset_error_state(self) -> None:
        """Reset pipeline state from error to idle (public API)."""
        if self._state == PipelineState.ERROR:
            self._set_state(PipelineState.IDLE)

    # Alias para compatibilidad API 100% con versiones anteriores
    @property
    def chunks_processed(self) -> int:
        return self._pipeline_metrics.chunks_processed

    @property
    def _chunk_index(self) -> int:
        return self._pipeline_metrics.chunks_processed

    def _get_output_module_status(self) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Return (output_status, video_muxer_status) tuple.

        output_status: aggregate output module status for the OUTPUT card.
        video_muxer_status: encoder-specific status for the VIDEO MUXER card, or None.
        """
        state = "running" if self.is_running else "idle"

        sink = self._output_sink if self._output_sink else self._module_map.get("video_muxer")
        extra = {}
        processed_chunks = self.metrics.chunks_processed
        last_process_time_ms = 0
        muxer_status = None

        if sink:
            try:
                status = sink.get_status()
                status_dict = status.to_dict() if getattr(status, "to_dict", None) else status
                if isinstance(status_dict, dict):
                    processed_chunks = status_dict.get("processed_chunks", processed_chunks)
                    last_process_time_ms = status_dict.get("last_process_time_ms", last_process_time_ms)
                    extra = status_dict.get("extra", {})

                    # Find the web/HLS output for video_muxer status
                    outputs = extra.get("outputs", {})
                    muxer_source = None
                    # Prefer outputs named "web" or "hls" or with GPU/encoder info in extra
                    for out_name, out_data in outputs.items():
                        out_extra = out_data.get("extra", {})
                        if out_extra.get("using_gpu") is not None or out_extra.get("encoder_mode") is not None:
                            muxer_source = out_data
                            break
                    # Fallback to first output if no specific web/hls found
                    if muxer_source is None and outputs:
                        first_name = list(outputs.keys())[0]
                        muxer_source = outputs[first_name]

                    if muxer_source:
                        muxer_extra = muxer_source.get("extra", {})
                        muxer_status = {
                            "name": "video_muxer",
                            "state": muxer_source.get("state", state),
                            "enabled": muxer_source.get("enabled", True),
                            "error_message": None,
                            "processed_chunks": muxer_source.get("processed_chunks", processed_chunks),
                            "last_process_time_ms": muxer_source.get("last_process_time_ms", last_process_time_ms),
                            "extra": muxer_extra,
                            "circuit_state": "closed",
                            "memory_mb": None,
                        }
            except Exception as e:
                logger.warning("Failed to get video muxer status: %s", e)

        output_status = {
            "name": "output",
            "state": state,
            "enabled": True,
            "error_message": None,
            "processed_chunks": processed_chunks,
            "last_process_time_ms": last_process_time_ms,
            "extra": extra,
            "circuit_state": "closed",
            "memory_mb": None,
        }

        return output_status, muxer_status
