"""
Pipeline orchestrator for SRT2Web.

Manages the ordered execution of processing modules,
handles start/stop lifecycle, and emits status events.
"""

import asyncio
import logging
import time
import threading
from enum import Enum
from pathlib import Path
from typing import List, Optional, Callable, Dict

from core.module_base import BaseModule, PipelineData, ModuleState

logger = logging.getLogger("srt2web.pipeline")


class PipelineState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class Pipeline:
    """
    Orchestrates the modular processing pipeline.

    Modules are registered in order and executed sequentially
    for each chunk of data.
    """

    def __init__(self):
        self._modules: List[BaseModule] = []
        self._module_map: Dict[str, BaseModule] = {}
        self._state = PipelineState.IDLE
        self._error_message: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._chunk_index = 0
        self._on_log: Optional[Callable[[str, str], None]] = None  # (level, message)
        self._on_state_change: Optional[Callable[[str], None]] = None

    @property
    def state(self) -> PipelineState:
        return self._state

    def register_module(self, module: BaseModule) -> None:
        """Register a module in the pipeline execution order."""
        self._modules.append(module)
        self._module_map[module.name] = module
        logger.info(f"Registered module: {module.name} (enabled={module.enabled})")

    def get_module(self, name: str) -> Optional[BaseModule]:
        """Get a module by name."""
        return self._module_map.get(name)

    def get_modules(self) -> List[BaseModule]:
        """Get all registered modules."""
        return list(self._modules)

    def reconfigure(self, config_manager) -> None:
        """Update configuration for all modules while running."""
        for module in self._modules:
            try:
                mod_config = config_manager.get_module_config(module.name)
                module.configure(mod_config)
                self._log("info", f"Reconfigured module: {module.name}")
            except Exception as e:
                self._log("error", f"Failed to reconfigure {module.name}: {e}")

    def _log(self, level: str, message: str) -> None:
        """Log a message and notify callback."""
        getattr(logger, level, logger.info)(message)
        if self._on_log:
            try:
                self._on_log(level, message)
            except Exception:
                pass

    def _set_state(self, state: PipelineState) -> None:
        """Update pipeline state and notify callback."""
        self._state = state
        self._log("info", f"Pipeline state: {state.value}")
        if self._on_state_change:
            try:
                self._on_state_change(state.value)
            except Exception:
                pass

    def start(
        self,
        data_source: Callable[[], Optional[PipelineData]],
        on_log: Optional[Callable[[str, str], None]] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Start the pipeline in a background thread.

        Args:
            data_source: Callable that returns the next PipelineData chunk,
                        or None when no data is available (will retry).
            on_log: Callback for log messages: (level, message)
            on_state_change: Callback for state changes: (new_state)
        """
        if self._state == PipelineState.RUNNING:
            self._log("warning", "Pipeline is already running")
            return

        self._on_log = on_log
        self._on_state_change = on_state_change
        self._stop_event.clear()
        self._chunk_index = 0

        self._thread = threading.Thread(
            target=self._run_loop,
            args=(data_source,),
            daemon=True,
            name="pipeline-loop",
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the pipeline gracefully."""
        if self._state not in (PipelineState.RUNNING, PipelineState.STARTING):
            return

        self._set_state(PipelineState.STOPPING)
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)

        # Stop all modules
        for module in self._modules:
            try:
                if module.enabled and module.state == ModuleState.RUNNING:
                    module.stop()
                    module._state = ModuleState.IDLE
            except Exception as e:
                self._log("error", f"Error stopping module {module.name}: {e}")

        self._set_state(PipelineState.IDLE)

    def _run_loop(self, data_source: Callable[[], Optional[PipelineData]]) -> None:
        """Main processing loop (runs in background thread)."""
        try:
            self._set_state(PipelineState.STARTING)

            # Start all enabled modules
            for module in self._modules:
                if module.enabled:
                    try:
                        self._log("info", f"Starting module: {module.name}")
                        module.start()
                        module._state = ModuleState.RUNNING
                    except Exception as e:
                        self._log("error", f"Failed to start module {module.name}: {e}")
                        module._state = ModuleState.ERROR
                        module._error_message = str(e)

            self._set_state(PipelineState.RUNNING)
            self._log("info", "Pipeline is running. Waiting for data...")

            # Main processing loop
            while not self._stop_event.is_set():
                try:
                    data = data_source()
                except Exception as e:
                    self._log("error", f"Data source error: {e}")
                    time.sleep(1)
                    continue

                if data is None:
                    # No data available, wait briefly
                    time.sleep(0.1)
                    continue

                data.chunk_index = self._chunk_index
                data.timestamp = time.time()

                # Process through all enabled modules (isolated per-module error handling)
                for module in self._modules:
                    if self._stop_event.is_set():
                        break
                    if not module.enabled:
                        continue
                    if module.state in (ModuleState.ERROR, ModuleState.DISABLED):
                        continue

                    try:
                        data = module.process(data)
                    except Exception as e:
                        self._log(
                            "error",
                            f"Module {module.name} error (chunk {self._chunk_index}): {e}",
                        )
                        module._state = ModuleState.ERROR
                        module._error_message = str(e)
                        # Continue to next module instead of stopping pipeline
                        continue

                self._chunk_index += 1

        except Exception as e:
            self._error_message = str(e)
            self._set_state(PipelineState.ERROR)
            self._log("error", f"Pipeline error: {e}")

    def get_status(self) -> dict:
        """Get full pipeline status including all modules."""
        return {
            "state": self._state.value,
            "error": self._error_message,
            "chunks_processed": self._chunk_index,
            "modules": [m.get_status().to_dict() for m in self._modules],
        }
