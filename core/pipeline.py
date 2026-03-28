"""
Pipeline orchestrator for SRT2Web.

Manages the ordered execution of processing modules,
handles start/stop lifecycle, and emits status events.
"""

import logging
import time
import threading
from enum import Enum
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

    The pipeline connects an InputSource to an OutputSink through
    a chain of processing modules.

    Architecture:
        InputSource -> [Module1, Module2, ...] -> OutputSink

    The order of registered modules determines the processing flow.
    """

    def __init__(self):
        """
        Initialize pipeline orchestrator.
        """
        self._config_manager = None
        self._output_dir = ""

        self._modules: List[BaseModule] = []
        self._module_map: Dict[str, BaseModule] = {}
        self._module_configs: Dict[str, dict] = {}
        self._state = PipelineState.IDLE
        self._error_message: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._chunk_index = 0
        self._on_log: Optional[Callable[[str, str], None]] = None
        self._on_state_change: Optional[Callable[[str], None]] = None



    @property
    def state(self) -> PipelineState:
        return self._state

    def register_module(
        self, module: BaseModule, config: Optional[dict] = None
    ) -> None:
        """Register a module in the pipeline execution order."""
        self._modules.append(module)
        self._module_map[module.name] = module
        if config:
            self._module_configs[module.name] = config.copy()
        logger.info(f"Registered module: {module.name} (enabled={module.enabled})")

    def register_module(
        self, module: BaseModule, config: Optional[dict] = None
    ) -> None:
        """
        Register a module in the pipeline execution order.
        """
        self._modules.append(module)
        self._module_map[module.name] = module
        if config:
            self._module_configs[module.name] = config.copy()
        logger.info(f"Registered module: {module.name} (enabled={module.enabled})")

    def get_module(self, name: str) -> Optional[BaseModule]:
        """Get a module by name."""
        return self._module_map.get(name)

    def get_modules(self) -> List[BaseModule]:
        """Get all registered modules."""
        return list(self._modules)

    def get_all_components(self) -> dict:
        """Get all pipeline components (modules only, as input/output are now modules)."""
        components = {"modules": []}

        components["modules"] = [m.get_status().to_dict() for m in self._modules]

        return components

    def reconjecture(self, config_manager) -> None:
        """Update configuration for all modules while running."""
        # Save config manager reference for future access
        self._config_manager = config_manager

        # Reconfigure all modules uniformly
        for module in self._modules:
            try:
                mod_config = config_manager.get_module_config(module.name)
                old_config = self._module_configs.get(module.name, {})

                # Check if TTS engine voice/engine/device changed and restart if needed
                needs_restart = False
                if module.name == "tts_engine":
                    old_voice = old_config.get("voice", "")
                    new_voice = mod_config.get("voice", "")
                    old_engine = old_config.get("engine", "")
                    new_engine = mod_config.get("engine", "")
                    old_device = old_config.get("device", "auto")
                    new_device = mod_config.get("device", "auto")
                    if old_voice != new_voice or old_engine != new_engine or old_device != new_device:
                        needs_restart = True
                        self._log(
                            "info", f"TTS config changed (voice/engine/device), restarting module..."
                        )

                module.configure(mod_config)
                self._module_configs[module.name] = mod_config.copy()

                if needs_restart and module.enabled:
                    self._restart_module(module)
                    self._log("info", f"Restarted module: {module.name}")
                else:
                    self._log("info", f"Reconfigured module: {module.name}")
            except Exception as e:
                self._log("error", f"Failed to reconfigure {module.name}: {e}")

    def _restart_module(self, module) -> None:
        """Restart a module (stop then start)."""
        try:
            if hasattr(module, "stop"):
                module.stop()
        except Exception as e:
            self._log("error", f"Error stopping module {module.name}: {e}")
        
        try:
            if hasattr(module, "start"):
                module.start()
        except Exception as e:
            self._log("error", f"Failed to restart module {module.name}: {e}")
            self._log("error", f"Module will remain in current state")

    def recreate_input(self, input_type: str, type_config: dict = None) -> dict:
        """
        Recreate input source with new type (hot-swap).
        
        Args:
            input_type: Type of input ("srt", "file", "rtmp")
            type_config: Optional configuration for the input type
            
        Returns:
            Dict with status and connection info
        """
        from core.io_factory import InputFactory
        
        self._log("info", f"Recreating input: {input_type}")
        
        # Stop current input
        if self._input_source:
            try:
                self._input_source.stop()
                self._log("info", f"Stopped old input: {self._input_source.name}")
            except Exception as e:
                self._log("error", f"Error stopping input: {e}")
        
        # Get configuration
        config = type_config or {}
        config["chunk_duration_sec"] = config.get("chunk_duration_sec", 15)
        
        # Create new input
        try:
            self._input_source = InputFactory.create(input_type, config)
            if self._output_dir:
                self._input_source.set_output_dir(self._output_dir)
            
            # Start if pipeline is running
            if self._state == PipelineState.RUNNING:
                self._input_source.start()
                self._log("info", f"Started new input: {input_type}")
            
            info = self._input_source.get_connection_info()
            return {"status": "success", "input_type": input_type, "info": info}
            
        except Exception as e:
            self._log("error", f"Failed to create input {input_type}: {e}")
            return {"status": "error", "error": str(e)}

    def recreate_output(self, output_type: str, type_config: dict = None) -> dict:
        """
        Recreate output sink with new type (hot-swap).
        
        Args:
            output_type: Type of output ("web", "rtmp", "srt")
            type_config: Optional configuration for the output type
            
        Returns:
            Dict with status and stream info
        """
        from core.io_factory import OutputFactory
        
        self._log("info", f"Recreating output: {output_type}")
        
        # Stop current output
        if self._output_sink:
            try:
                self._output_sink.stop()
                self._log("info", f"Stopped old output: {self._output_sink.name}")
            except Exception as e:
                self._log("error", f"Error stopping output: {e}")
        
        # Create new output
        try:
            self._output_sink = OutputFactory.create(output_type, type_config or {})
            if self._output_dir:
                self._output_sink.set_output_dir(self._output_dir)
            
            # Start if pipeline is running
            if self._state == PipelineState.RUNNING:
                self._output_sink.start()
                self._log("info", f"Started new output: {output_type}")
            
            info = self._output_sink.get_stream_info()
            return {"status": "success", "output_type": output_type, "info": info}
            
        except Exception as e:
            self._log("error", f"Failed to create output {output_type}: {e}")
            return {"status": "error", "error": str(e)}

    def set_output_dir(self, output_dir: str) -> None:
        """Set output directory for input and output."""
        self._output_dir = output_dir
        if self._input_source:
            self._input_source.set_output_dir(output_dir)
        if self._output_sink:
            self._output_sink.set_output_dir(output_dir)

    def check_config_changes(self, config_manager) -> None:
        """
        No longer needed as input/output are now regular modules.
        Configuration changes are handled through the standard reconfigure method.
        """
        pass

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
        on_log: Optional[Callable[[str, str], None]] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Start the pipeline in a background thread.

        All registered modules (including input/output) are started automatically.
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

    def _run_loop(self) -> None:
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
                # Process through all enabled modules
                data = PipelineData()
                data.chunk_index = self._chunk_index
                data.timestamp = time.time()

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
                        continue

                self._chunk_index += 1

        except Exception as e:
            self._error_message = str(e)
            self._set_state(PipelineState.ERROR)
            self._log("error", f"Pipeline error: {e}")

    def get_status(self) -> dict:
        """Get full pipeline status including all components."""
        modules_status = [m.get_status().to_dict() for m in self._modules]

        status = {
            "state": self._state.value,
            "error": self._error_message,
            "chunks_processed": self._chunk_index,
            "modules": modules_status,
            "system": self._get_system_metrics(),
        }

        return status



    def _get_system_metrics(self) -> dict:
        """Get system metrics like CPU, memory, and GPU usage."""
        metrics = {
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "memory_percent": 0.0,
            "gpu_percent": 0.0,
            "gpu_memory_mb": 0.0,
            "gpu_available": False,
            "available": False,
        }
        try:
            import psutil

            process = psutil.Process()
            metrics = {
                "cpu_percent": round(process.cpu_percent(interval=0.1), 1),
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
                "memory_percent": round(process.memory_percent(), 1),
                "available": True,
            }
        except ImportError:
            logger.debug("psutil not available for system metrics")
        except Exception as e:
            logger.debug(f"Error getting system metrics: {e}")

        # Try to get GPU metrics using nvidia-ml-py (official NVIDIA library)
        try:
            import pynvml

            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)

                # GPU utilization
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    metrics["gpu_percent"] = round(util.gpu, 1)
                except Exception:
                    pass

                # GPU memory
                try:
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    metrics["gpu_memory_mb"] = round(mem_info.used / 1024 / 1024, 1)
                except Exception:
                    pass

                metrics["gpu_available"] = True
            pynvml.nvmlShutdown()
        except ImportError:
            logger.debug("pynvml not available for GPU metrics")
        except Exception as e:
            logger.debug(f"Error getting GPU metrics: {e}")

        return metrics
