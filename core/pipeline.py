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
from core.input_source import InputSource
from core.output_sink import OutputSink

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

    def __init__(
        self,
        input_source: Optional[InputSource] = None,
        output_sink: Optional[OutputSink] = None,
    ):
        """
        Initialize pipeline with optional input/output.

        Args:
            input_source: Source of data (SRT, file, etc.)
            output_sink: Destination for processed data (HLS, SRT, etc.)
        """
        self._input_source = input_source
        self._output_sink = output_sink
        self._config_manager = None

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
    def input_source(self) -> Optional[InputSource]:
        """Get the input source."""
        return self._input_source

    @input_source.setter
    def input_source(self, source: InputSource) -> None:
        """Set the input source."""
        self._input_source = source

    @property
    def output_sink(self) -> Optional[OutputSink]:
        """Get the output sink."""
        return self._output_sink

    @output_sink.setter
    def output_sink(self, sink: OutputSink) -> None:
        """Set the output sink."""
        self._output_sink = sink

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

    def get_module(self, name: str) -> Optional[BaseModule]:
        """Get a module by name."""
        return self._module_map.get(name)

    def get_modules(self) -> List[BaseModule]:
        """Get all registered modules."""
        return list(self._modules)

    def get_all_components(self) -> dict:
        """Get all pipeline components (input, output, modules)."""
        components = {"input": None, "output": None, "modules": []}

        if self._input_source:
            components["input"] = {
                "type": self._input_source.name,
                "config": self._input_source.config,
                "info": self._input_source.get_connection_info(),
            }

        if self._output_sink:
            components["output"] = {
                "type": self._output_sink.name,
                "config": self._output_sink.config,
                "info": self._output_sink.get_stream_info(),
            }

        components["modules"] = [m.get_status().to_dict() for m in self._modules]

        return components

    def reconfigure(self, config_manager) -> None:
        """Update configuration for all components while running."""
        # Save config manager reference for future access
        self._config_manager = config_manager

        # Reconfigure input
        if self._input_source:
            try:
                input_config = config_manager.get_section("input")
                input_type = input_config.get("type", "srt")
                type_config = input_config.get(input_type, {})
                self._input_source.configure(type_config)
                self._log("info", f"Reconfigured input: {input_type}")
            except Exception as e:
                self._log("error", f"Failed to reconfigure input: {e}")

        # Reconfigure output
        if self._output_sink:
            try:
                output_config = config_manager.get_section("output")
                output_type = output_config.get("type", "web")
                type_config = output_config.get(output_type, {})
                self._output_sink.configure(type_config)
                self._log("info", f"Reconfigured output: {output_type}")
            except Exception as e:
                self._log("error", f"Failed to reconfigure output: {e}")

        # Reconfigure modules
        for module in self._modules:
            try:
                mod_config = config_manager.get_module_config(module.name)
                old_config = self._module_configs.get(module.name, {})

                # Check if TTS engine voice/engine changed and restart if needed
                needs_restart = False
                if module.name == "tts_engine":
                    old_voice = old_config.get("voice", "")
                    new_voice = mod_config.get("voice", "")
                    old_engine = old_config.get("engine", "")
                    new_engine = mod_config.get("engine", "")
                    if old_voice != new_voice or old_engine != new_engine:
                        needs_restart = True
                        self._log(
                            "info", f"TTS voice/engine changed, restarting module..."
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
            if hasattr(module, "start"):
                module.start()
        except Exception as e:
            self._log("error", f"Failed to restart module {module.name}: {e}")

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

        Uses the registered input_source and output_sink automatically.
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

        # Stop output sink first
        if self._output_sink:
            try:
                self._output_sink.stop()
            except Exception as e:
                self._log("error", f"Error stopping output sink: {e}")

        # Stop all modules
        for module in self._modules:
            try:
                if module.enabled and module.state == ModuleState.RUNNING:
                    module.stop()
                    module._state = ModuleState.IDLE
            except Exception as e:
                self._log("error", f"Error stopping module {module.name}: {e}")

        # Stop input source last
        if self._input_source:
            try:
                self._input_source.stop()
            except Exception as e:
                self._log("error", f"Error stopping input source: {e}")

        self._set_state(PipelineState.IDLE)

    def _run_loop(self) -> None:
        """Main processing loop (runs in background thread)."""
        try:
            self._set_state(PipelineState.STARTING)

            # Start input source
            if self._input_source:
                try:
                    self._log(
                        "info", f"Starting input source: {self._input_source.name}"
                    )
                    self._input_source.start()
                except Exception as e:
                    self._log("error", f"Failed to start input source: {e}")
                    self._error_message = str(e)
                    self._set_state(PipelineState.ERROR)
                    return

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

            # Start output sink
            if self._output_sink:
                try:
                    self._log("info", f"Starting output sink: {self._output_sink.name}")
                    self._output_sink.start()
                except Exception as e:
                    self._log("error", f"Failed to start output sink: {e}")
                    self._error_message = str(e)
                    self._set_state(PipelineState.ERROR)
                    return

            self._set_state(PipelineState.RUNNING)
            self._log("info", "Pipeline is running. Waiting for data...")

            # Determine data source
            data_source = None
            if self._input_source:
                data_source = self._input_source.get_next_chunk
            else:
                self._log("warning", "No input source configured!")

            # Main processing loop
            while not self._stop_event.is_set():
                if data_source is None:
                    time.sleep(0.5)
                    continue

                try:
                    data = data_source()
                except Exception as e:
                    self._log("error", f"Data source error: {e}")
                    time.sleep(1)
                    continue

                if data is None:
                    time.sleep(0.1)
                    continue

                data.chunk_index = self._chunk_index
                data.timestamp = time.time()

                # Process through all enabled modules
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

                # Write to output sink
                if self._output_sink and data:
                    try:
                        self._output_sink.write(data)
                    except Exception as e:
                        self._log("error", f"Output sink error: {e}")

                self._chunk_index += 1

        except Exception as e:
            self._error_message = str(e)
            self._set_state(PipelineState.ERROR)
            self._log("error", f"Pipeline error: {e}")

    def get_status(self) -> dict:
        """Get full pipeline status including all components."""
        modules_status = [m.get_status().to_dict() for m in self._modules]

        # Add output sink as a module (for frontend compatibility)
        if self._output_sink:
            output_module_status = self._get_output_module_status()
            if output_module_status:
                modules_status.append(output_module_status)

        status = {
            "state": self._state.value,
            "error": self._error_message,
            "chunks_processed": self._chunk_index,
            "input": None,
            "output": None,
            "modules": modules_status,
            "system": self._get_system_metrics(),
        }

        if self._input_source:
            status["input"] = {
                "type": self._input_source.name,
                "receiving": self._input_source.is_receiving(),
                "info": self._input_source.get_connection_info(),
            }

        if self._output_sink:
            status["output"] = {
                "type": self._output_sink.name,
                "info": self._output_sink.get_stream_info(),
            }

        return status

    def _get_output_module_status(self) -> dict:
        """Get output sink status in module format for frontend."""
        from core.module_base import ModuleState

        # Determine state based on pipeline state
        if self._state == PipelineState.RUNNING:
            state = "running"
        elif self._state == PipelineState.ERROR:
            state = "error"
        else:
            state = "idle"

        # Get encoder info from output sink
        extra = {}
        if hasattr(self._output_sink, "_encoder_config"):
            encoder_config = self._output_sink._encoder_config
            encoder_mode = encoder_config.encoder_mode

            # Auto-detect encoder mode
            if encoder_mode == "auto" and hasattr(self._output_sink, "_gpu_info"):
                gpu_info = self._output_sink._gpu_info
                if gpu_info.get("nvenc"):
                    encoder_mode = "gpu_nvenc"
                elif gpu_info.get("amf"):
                    encoder_mode = "gpu_amf"
                elif gpu_info.get("qsv"):
                    encoder_mode = "gpu_qsv"
                else:
                    encoder_mode = "cpu"

            extra["encoder_mode"] = encoder_mode
            extra["using_gpu"] = encoder_mode.startswith("gpu_")
            extra["gpu_available"] = getattr(self._output_sink, "_gpu_info", {})
            extra["gpu_preset"] = (
                encoder_config.gpu_preset
                if hasattr(encoder_config, "gpu_preset")
                else "p3"
            )

        return {
            "name": "video_muxer",
            "state": state,
            "enabled": True,
            "error_message": self._error_message
            if self._state == PipelineState.ERROR
            else None,
            "processed_chunks": self._chunk_index,
            "last_process_time_ms": 0.0,
            "extra": extra,
            "circuit_state": "closed",
            "memory_mb": None,
        }

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

        # Try to get GPU metrics
        try:
            import GPUtil

            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                metrics["gpu_percent"] = round(gpu.load * 100, 1)
                metrics["gpu_memory_mb"] = round(gpu.memoryUsed, 1)
                metrics["gpu_available"] = True
        except ImportError:
            logger.debug("GPUtil not available for GPU metrics")
        except Exception as e:
            logger.debug(f"Error getting GPU metrics: {e}")

        return metrics
