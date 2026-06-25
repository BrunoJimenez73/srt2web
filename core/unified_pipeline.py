"""
Unified Pipeline — init, registration, state management, delegation.
Loop execution in core/pipeline/strategies.py (F132).
"""

from __future__ import annotations

import asyncio
import logging
import os
import queue
import threading
import time
import typing
from collections.abc import Callable
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

_DEFAULT_INIT_TIMEOUT_S = 300.0


def _get_init_timeout() -> float:
    """Read pipeline init timeout from env. Default 300s."""
    raw = os.environ.get("SRT2WEB_PIPELINE_INIT_TIMEOUT")
    if raw is None:
        return _DEFAULT_INIT_TIMEOUT_S
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return _DEFAULT_INIT_TIMEOUT_S
    return value if value > 0 else _DEFAULT_INIT_TIMEOUT_S


if TYPE_CHECKING:
    from modules.outputs.composite_output import CompositeOutput

try:
    from modules.outputs.composite_output import CompositeOutput as _CompositeOutput
except ImportError:
    _CompositeOutput = None  # type: ignore[misc, assignment]

# Lazy imports to avoid circular dependency (strategies → module_base → core.__init__ → unified_pipeline)
# These are imported on first use in __init__ or start().
_strategy_module = None
_helpers_module = None


def _ensure_strategy_imports() -> None:
    """Lazily import strategy module to break circular dependency."""
    global _strategy_module, _helpers_module
    if _strategy_module is None:
        try:
            import importlib

            _strategy_module = importlib.import_module("core.pipeline.strategies")
            _helpers_module = importlib.import_module("core.pipeline.pipeline_helpers")
        except ImportError as e:
            logger.warning("Could not import strategy modules: %s", e)


def _get_strategy_attrs() -> tuple[Any, Any, Any, Any, Any]:
    """Get strategy attributes from lazily-imported module."""
    _ensure_strategy_imports()
    if _strategy_module is None:
        return None, None, None, None, None
    return (
        getattr(_strategy_module, "ChunkProcessor", None),
        getattr(_strategy_module, "PipelineContext", None),
        getattr(_strategy_module, "PipelineStrategy", None),
        getattr(_strategy_module, "StrategyConfig", None),
        getattr(_strategy_module, "create_strategy", None),
    )


logger = logging.getLogger("srt2web.unified_pipeline")


class _CompletedAwaitable:
    """Awaitable no-op used for backward-compatible sync APIs.

    DT-07: uses ``__iter__`` instead of ``__await__`` generator for
    Python 3.12+ compatibility (generator-based coroutines are deprecated
    in CPython 3.14+ but ``__await__`` returning an iterator is fine).
    """

    def __await__(self) -> typing.Generator[None, None, None]:
        return typing.cast(typing.Generator[None, None, None], iter([]))


class UnifiedPipeline:
    """Pipeline unificado multi-modo (sequential / thread_parallel / asyncio)."""

    def __init__(
        self,
        mode: PipelineMode = PipelineMode.THREAD_PARALLEL,
        max_concurrent_chunks: int = 3,
        buffer_size: int = 5,
        retry_attempts: int = 2,
        retry_delay: float = 1.0,
        lost_chunk_timeout_sec: float = 30.0,
    ):
        self._initialized = False

        self.mode = mode
        self.max_concurrent_chunks = max_concurrent_chunks
        self.buffer_size = buffer_size
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.lost_chunk_timeout = lost_chunk_timeout_sec
        self._state = PipelineState.IDLE
        self._modules: list[BaseModule] = []
        self._module_map: dict[str, BaseModule] = {}
        self._input_source = None
        self._output_sink: Any = None
        self._stop_event = threading.Event()
        self._semaphore = threading.Semaphore(max_concurrent_chunks)
        self._tasks: list[Any] = []
        self._chunk_queue: queue.Queue[Any] = queue.Queue(maxsize=buffer_size)
        self._output_queue: queue.Queue[Any] = queue.Queue(maxsize=buffer_size)
        self._results: dict[int, Any] = {}
        self._input_thread: threading.Thread | None = None
        self._output_thread: threading.Thread | None = None
        self._pipeline_metrics = PipelineMetrics()
        self._system_metrics = SystemMetrics(cpu_percent=0, memory_mb=0, memory_percent=0)
        self._on_log: Callable[[str, str], None] | None = None
        self._on_state_change: Callable[[str], None] | None = None
        self._on_chunk_complete: Callable[[int, PipelineData], None] | None = None
        self._lock = threading.Lock()
        self._hardware_monitor = HardwareMonitor()
        self._init_thread: threading.Thread | None = None
        self._init_error: BaseException | None = None
        self._chunk_duration = 10.0

        # Initialize processing strategy (lazy import)
        self._strategy: Any = None
        self._active_chunks = 0
        _ensure_strategy_imports()
        if _strategy_module:
            create_fn = getattr(_strategy_module, "create_strategy", None)
            cfg_cls = getattr(_strategy_module, "StrategyConfig", None)
            if create_fn and cfg_cls:
                try:
                    strategy_config = cfg_cls(max_concurrent_chunks=max_concurrent_chunks)
                    self._strategy = create_fn(mode.value, strategy_config)
                    logger.info(f"Pipeline strategy initialized: {type(self._strategy).__name__}")
                except Exception as e:
                    logger.warning(f"Could not initialize strategy: {e}")

        logger.info(f"UnifiedPipeline initialized mode={mode.value} concurrent={max_concurrent_chunks}")

    @property
    def metrics(self) -> PipelineMetrics:
        return self._pipeline_metrics

    @property
    def state(self) -> PipelineState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state in (PipelineState.RUNNING, PipelineState.STARTING)

    def set_input_source(self, source: Any) -> None:
        self._input_source = source

    def get_input_source(self) -> Any | None:
        return self._input_source

    def set_output_sinks(self, output_configs: list[dict[str, Any]]) -> None:
        from core.io_factory import OutputFactory

        outputs = OutputFactory.create_multiple(output_configs)
        if _CompositeOutput is None:
            raise ImportError("CompositeOutput is not available")
        self._output_sink = _CompositeOutput({})
        for output in outputs:
            self._output_sink.add_output(output.name, output)

    def set_output_sink(self, sink: Any) -> None:
        self._output_sink = sink

    def get_output_sink(self) -> Any | None:
        return self._output_sink

    def get_output_sinks(self) -> CompositeOutput | None:
        if _CompositeOutput is not None and isinstance(self._output_sink, _CompositeOutput):
            return self._output_sink
        return None

    def register_module(self, module: BaseModule, config: dict[str, Any] | None = None) -> None:
        self._modules.append(module)
        self._module_map[module.name] = module
        logger.info(f"Registered module: {module.name} enabled={module.enabled}")
        if config:
            module.configure(config)
        if self._strategy:
            self._strategy.set_modules(self._modules)

    def get_module(self, name: str) -> BaseModule | None:
        return self._module_map.get(name)

    def get_modules(self) -> list[BaseModule]:
        return list(self._modules)

    def _set_state(self, new_state: PipelineState) -> None:
        """Cambiar estado y notificar."""
        old_state = self._state
        self._state = new_state
        if self.metrics.start_time is None and new_state == PipelineState.RUNNING:
            self.metrics.start_time = time.time()
        if self._on_state_change:
            self._on_state_change(new_state.value)
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
        """Procesar un chunk usando la estrategia configurada."""
        if not self._strategy:
            logger.warning("No strategy configured, skipping processing")
            return data
        try:
            result: PipelineData = self._strategy.process_chunk(data)
            return result
        except Exception as e:
            logger.error(f"Strategy processing failed: {e}")
            raise

    def get_strategy_metrics(self) -> dict[str, Any]:
        """Obtener métricas de la estrategia."""
        if self._strategy:
            result: dict[str, Any] = self._strategy.get_metrics()
            return result
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

            self._set_state(PipelineState.IDLE)
            logger.info("UnifiedPipeline initialized successfully")

        except Exception as e:
            self._set_state(PipelineState.ERROR)
            logger.error(f"Pipeline initialization failed: {e}")
            raise

    def _make_context(self) -> Any:
        """Create a PipelineContext from current state for the strategy."""
        _ensure_strategy_imports()
        ctx_cls = getattr(_strategy_module, "PipelineContext", None) if _strategy_module else None
        if ctx_cls is None:
            raise RuntimeError("PipelineContext not available")
        return ctx_cls(
            stop_event=self._stop_event,
            semaphore=self._semaphore,
            chunk_queue=self._chunk_queue,
            output_queue=self._output_queue,
            results=self._results,
            lock=self._lock,
            modules=list(self._modules),
            input_source=self._input_source,
            output_sink=self._output_sink,
            on_log=self._on_log,
            on_state_change=self._on_state_change,
            on_chunk_complete=self._on_chunk_complete,
            set_state=self._set_state,
            metrics=self._pipeline_metrics,
            lost_chunk_timeout=self.lost_chunk_timeout,
            buffer_size=self.buffer_size,
        )

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
            # F107: reject if a previous init thread is still running
            existing = self._init_thread
            if existing is not None and existing.is_alive():
                self._set_state(PipelineState.ERROR)
                raise PipelineError(
                    "Pipeline initialization already in progress; wait for it to finish or restart the server"
                )

            self._init_error = None
            timeout_s = _get_init_timeout()

            def run_init() -> None:
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.initialize())
                    self._initialized = True
                except BaseException as exc:
                    self._init_error = exc
                finally:
                    try:
                        loop.close()
                    except Exception as close_err:
                        logger.debug("Init loop close failed: %s", close_err)

            init_thread = threading.Thread(target=run_init, daemon=True, name="pipeline-init")
            self._init_thread = init_thread
            init_thread.start()
            init_thread.join(timeout=timeout_s)

            if init_thread.is_alive():
                self._set_state(PipelineState.ERROR)
                raise PipelineError(
                    f"Pipeline initialization timed out after {timeout_s:.0f}s "
                    "(model download may still be running in background). "
                    "Set SRT2WEB_PIPELINE_INIT_TIMEOUT to a higher value if needed."
                )

            captured = self._init_error
            if captured is not None:
                self._init_error = None
                self._set_state(PipelineState.ERROR)
                raise PipelineError(f"Pipeline initialization failed: {captured}") from captured

            if not self._initialized:
                self._set_state(PipelineState.ERROR)
                raise PipelineError("Pipeline initialization did not complete")

        self._stop_event.clear()

        # Delegate loop execution to strategy (F132)
        if self._strategy:
            ctx = self._make_context()
            self._strategy.set_context(ctx)
            self._strategy.start()
            self._strategy.start_threads(ctx)
        else:
            # Fallback: no strategy, just set state
            logger.warning("No strategy configured, pipeline will be idle")

        self._set_state(PipelineState.RUNNING)
        self._log("info", "UnifiedPipeline started successfully")
        return _CompletedAwaitable()

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
        """Detener pipeline gracefulmente.

        The guard + state transition are atomic under ``self._lock`` (ROB-01).
        The rest of the shutdown runs outside the lock to avoid deadlocks with
        module or strategy ``stop()`` methods that may acquire other locks.
        """
        with self._lock:
            if not self.is_running:
                return
            self._hardware_monitor.shutdown()
            self._set_state(PipelineState.STOPPING)
            self._stop_event.set()

        # Delegate thread stopping to strategy (F132)
        if self._strategy:
            try:
                self._strategy.stop_threads()
            except Exception as e:
                self._log("error", f"Error stopping strategy threads: {e}")
            self._strategy.stop()

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

        try:
            has_video_muxer_module = any(status.get("name") == "video_muxer" for status in modules_status)  # type: ignore[union-attr]
            if not has_video_muxer_module:
                output_status, muxer_status = self._get_output_module_status()
                modules_status.append(output_status)
                if muxer_status:
                    modules_status.append(muxer_status)
        except Exception as e:
            logger.warning("Failed to get output module status: %s", e)

        try:
            if self._input_source:
                get_status_method = getattr(self._input_source, "get_status", None)
                if get_status_method:
                    input_status = get_status_method()
                    status_dict = getattr(input_status, "to_dict", lambda: input_status)()
                    if isinstance(status_dict, dict):
                        if "name" not in status_dict:
                            status_dict["name"] = "input"
                        modules_status.insert(0, status_dict)
        except Exception as e:
            logger.warning("Failed to get input source status: %s", e)

        avg_time = self._pipeline_metrics.avg_processing_time
        system_metrics = self._hardware_monitor.get_system_metrics()

        strategy_metrics = {}
        if self._strategy:
            try:
                strategy_metrics = self._strategy.get_metrics()
            except Exception as e:
                logger.debug("Suppressed error: %s", e, exc_info=True)

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
        _ensure_strategy_imports()
        reconfigure_fn = getattr(_helpers_module, "reconfigure_pipeline", None) if _helpers_module else None
        if reconfigure_fn:
            reconfigure_fn(self, config_manager, self._log)
        else:
            self._log("warning", "reconfigure_pipeline helper not available")

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
        """Return (output_status, video_muxer_status) tuple."""
        _ensure_strategy_imports()
        get_status_fn = getattr(_helpers_module, "get_output_module_status", None) if _helpers_module else None
        if get_status_fn:
            result: tuple[dict[str, Any], dict[str, Any] | None] = get_status_fn(
                self.is_running, self._output_sink, self._module_map, self.metrics.chunks_processed
            )
            return result
        return {
            "name": "output",
            "state": "idle",
            "enabled": True,
            "error_message": None,
            "processed_chunks": 0,
            "last_process_time_ms": 0,
            "extra": {},
            "circuit_state": "closed",
            "memory_mb": None,
        }, None
