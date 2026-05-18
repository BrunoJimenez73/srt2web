"""
Composite Output - Gestiona múltiples salidas simultáneamente.
Delega el trabajo a cada salida individual.
"""

import logging
import threading
from dataclasses import dataclass
from typing import Any, Optional

from core.module_base import ModuleState, ModuleStatus, PipelineData
from core.output_sink import OutputSink
from modules.outputs.base import BaseOutput

logger = logging.getLogger("srt2web.output.composite")


@dataclass
class OutputStatus:
    """Estado de una salida individual."""

    name: str
    state: str
    enabled: bool
    error: Optional[str] = None
    processed_chunks: int = 0
    last_process_time_ms: float = 0.0
    extra: dict = None


class CompositeOutput(BaseOutput):
    """
    Gestiona múltiples salidas simultáneamente.
    Delega el trabajo a cada salida individual.
    """

    def __init__(self, config: dict):
        super().__init__("composite", config)
        self._outputs: dict[str, OutputSink] = {}
        self._errors: dict[str, str] = {}
        self._reconnect_attempts: dict[str, int] = {}
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 5.0  # segundos
        self._lock = threading.Lock()

    def add_output(self, name: str, output: OutputSink) -> None:
        """Añadir una nueva salida al composite."""
        with self._lock:
            self._outputs[name] = output
            self._errors[name] = None
            self._reconnect_attempts[name] = 0

    def configure_outputs(self, config_manager: Any) -> None:
        """Reconfigure each output sink from config_manager.

        Merges output section config (output.web, output.hls) with
        modules.video_muxer config so the full EncoderConfig is available.
        """
        for name, output in self._outputs.items():
            try:
                out_type = type(output).__name__.lower().replace("output", "")
                # Try specific output config first (output.web, output.hls, etc.)
                section_config = config_manager.get_section("output").get(out_type, {})
                if not section_config:
                    section_config = config_manager.get_section("output")

                # Merge video_muxer module config for full encoder settings
                video_muxer_config = config_manager.get_section("modules.video_muxer")
                if video_muxer_config:
                    merged = {**section_config, **video_muxer_config}
                else:
                    merged = section_config

                output.configure(merged)
                self._errors[name] = None
                logger.info(f"Reconfigured output '{name}' ({out_type})")
            except Exception as e:
                self._errors[name] = str(e)
                logger.warning(f"Failed to reconfigure output '{name}': {e}")

    def start(self) -> None:
        """Iniciar todas las salidas."""
        with self._lock:
            for name, output in self._outputs.items():
                try:
                    output.start()
                    self._errors[name] = None
                    self._reconnect_attempts[name] = 0
                except Exception as e:
                    self._errors[name] = str(e)
                    logger.error(f"Failed to start output '{name}': {e}")

    def stop(self) -> None:
        """Detener todas las salidas."""
        with self._lock:
            for name, output in self._outputs.items():
                try:
                    output.stop()
                except Exception as e:
                    logger.error(f"Error stopping output '{name}': {e}")

    def write(self, data: PipelineData) -> None:
        """Escribir en todas las salidas simultáneamente."""
        with self._lock:
            for name, output in self._outputs.items():
                if self._errors.get(name):
                    continue  # Omitir salidas con error

                try:
                    output.write(data)
                except Exception as e:
                    self._errors[name] = str(e)
                    logger.error(f"Output '{name}' error: {e}")
                    # Intentar reconectar automáticamente
                    self._schedule_reconnect(name)

    def _schedule_reconnect(self, name: str) -> None:
        """Programar reconexión automática."""
        if self._reconnect_attempts[name] >= self._max_reconnect_attempts:
            return  # No intentar más

        self._reconnect_attempts[name] += 1

        def reconnect():
            self._reconnect_output(name)

        # Programar reconexión después del delay
        timer = threading.Timer(self._reconnect_delay, reconnect)
        timer.daemon = True
        timer.start()

    def _reconnect_output(self, name: str) -> None:
        """Intentar reconectar una salida que falló."""
        with self._lock:
            if name not in self._outputs:
                return

            output = self._outputs[name]

            try:
                output.stop()
                output.start()
                self._errors[name] = None
                self._reconnect_attempts[name] = 0
                logger.info(f"Output '{name}' reconnected successfully")
            except Exception as e:
                logger.error(f"Reconnect attempt {self._reconnect_attempts[name]} failed: {e}")
                # Programar siguiente intento
                self._schedule_reconnect(name)

    def get_status(self) -> ModuleStatus:
        """Obtener estado de todas las salidas (compatible con formato legacy)."""
        # Obtener el primer output para metrics legacy
        first_output = None
        first_name = None
        with self._lock:
            if self._outputs:
                first_name = list(self._outputs.keys())[0]
                first_output = list(self._outputs.values())[0]

        # Base del primer output o defaults
        if first_output and hasattr(first_output, "get_status"):
            try:
                first_status = first_output.get_status()
                state = first_status.state
                enabled = first_status.enabled
                processed_chunks = first_status.processed_chunks
                last_process_time_ms = first_status.last_process_time_ms
                extra = first_status.extra.copy() if first_status.extra else {}
            except Exception:
                state = "idle"
                enabled = True
                processed_chunks = 0
                last_process_time_ms = 0.0
                extra = {}
        else:
            state = "idle"
            enabled = True
            processed_chunks = 0
            last_process_time_ms = 0.0
            extra = {}

        # Agregar outputs individuales y tipo
        outputs_dict = {}
        with self._lock:
            for name, output in self._outputs.items():
                try:
                    output_status = output.get_status()
                    outputs_dict[name] = {
                        "name": name,
                        "state": output_status.state,
                        "enabled": output_status.enabled,
                        "processed_chunks": output_status.processed_chunks,
                        "last_process_time_ms": output_status.last_process_time_ms,
                        "extra": output_status.extra,
                    }
                except Exception as e:
                    outputs_dict[name] = {"name": name, "state": "error", "enabled": True, "error": str(e)}

        extra["type"] = "composite"
        extra["outputs"] = outputs_dict
        extra["errors"] = self._errors.copy()

        return ModuleStatus(
            name="composite_output",
            state=ModuleState(state) if isinstance(state, str) else state,
            enabled=enabled,
            processed_chunks=processed_chunks,
            last_process_time_ms=last_process_time_ms,
            extra=extra,
        )

    def get_output_status(self, name: str) -> Optional[OutputStatus]:
        """Obtener estado de una salida específica."""
        with self._lock:
            if name not in self._outputs:
                return None

            output = self._outputs[name]
            try:
                output_status = output.get_status()
                # Handle both dict and object (ModuleStatus) returns
                if isinstance(output_status, dict):
                    return OutputStatus(
                        name=name,
                        state=output_status.get("state", "unknown"),
                        enabled=output_status.get("enabled", True),
                        error=self._errors.get(name),
                        processed_chunks=output_status.get("processed_chunks", 0),
                        last_process_time_ms=output_status.get("last_process_time_ms", 0.0),
                        extra=output_status.get("extra", {}),
                    )
                else:
                    # Assume it's a ModuleStatus or similar object
                    return OutputStatus(
                        name=name,
                        state=getattr(output_status, "state", "unknown"),
                        enabled=getattr(output_status, "enabled", True),
                        error=self._errors.get(name),
                        processed_chunks=getattr(output_status, "processed_chunks", 0),
                        last_process_time_ms=getattr(output_status, "last_process_time_ms", 0.0),
                        extra=getattr(output_status, "extra", {}),
                    )
            except Exception as e:
                return OutputStatus(name=name, state="error", enabled=True, error=str(e))

    def get_all_output_statuses(self) -> list[dict]:
        """Obtener estado de todas las salidas como diccionarios."""
        with self._lock:
            statuses = []
            for name, output in self._outputs.items():
                try:
                    output_status = output.get_status()  # ModuleStatus (Pydantic)
                    if isinstance(output_status, dict):
                        state = output_status.get("state", "unknown")
                        enabled = output_status.get("enabled", True)
                        processed_chunks = output_status.get("processed_chunks", 0)
                        last_process_time_ms = output_status.get("last_process_time_ms", 0.0)
                        extra = output_status.get("extra", {})
                    else:
                        state_value = getattr(output_status, "state", "unknown")
                        state = state_value.value if hasattr(state_value, "value") else state_value
                        enabled = getattr(output_status, "enabled", True)
                        processed_chunks = getattr(output_status, "processed_chunks", 0)
                        last_process_time_ms = getattr(output_status, "last_process_time_ms", 0.0)
                        extra = getattr(output_status, "extra", {})
                    statuses.append(
                        {
                            "name": name,
                            "type": getattr(output, "name", type(output).__name__.lower().replace("output", "")),
                            "state": state,
                            "enabled": enabled,
                            "error": self._errors.get(name),
                            "processed_chunks": processed_chunks,
                            "last_process_time_ms": last_process_time_ms,
                            "extra": extra,
                            "stream_info": output.get_stream_info() if hasattr(output, "get_stream_info") else {},
                        }
                    )
                except Exception as e:
                    statuses.append(
                        {
                            "name": name,
                            "type": type(output).__name__.lower().replace("output", ""),
                            "state": "error",
                            "enabled": getattr(output, "enabled", True),
                            "error": f"Error al obtener estado: {e!s}",
                            "processed_chunks": 0,
                            "last_process_time_ms": 0.0,
                            "extra": {},
                            "stream_info": {},
                        }
                    )
            return statuses

    def is_output_enabled(self, name: str) -> bool:
        """Verificar si una salida está habilitada."""
        with self._lock:
            if name not in self._outputs:
                return False
            output = self._outputs[name]
            if hasattr(output, "enabled"):
                return output.enabled
            if hasattr(output, "_enabled"):
                return output._enabled
            return True

    def enable_output(self, name: str, enable: bool = True) -> bool:
        """Habilitar/deshabilitar una salida."""
        with self._lock:
            if name not in self._outputs:
                return False
            output = self._outputs[name]
            if hasattr(output, "enabled"):
                output.enabled = enable
                return True
            if hasattr(output, "_enabled"):
                output._enabled = enable
                return True
            return False

    def remove_output(self, name: str) -> bool:
        """Eliminar una salida del composite."""
        with self._lock:
            if name in self._outputs:
                try:
                    self._outputs[name].stop()
                except Exception:
                    pass
                del self._outputs[name]
                del self._errors[name]
                del self._reconnect_attempts[name]
                return True
            return False

    def get_output_names(self) -> list[str]:
        """Obtener lista de nombres de salidas."""
        with self._lock:
            return list(self._outputs.keys())

    def get_output_types(self) -> list[str]:
        """Obtener lista de tipos de salidas."""
        with self._lock:
            return [type(output).__name__ for output in self._outputs.values()]

    def get_output_by_name(self, name: str) -> Optional[OutputSink]:
        """Obtener una salida por nombre."""
        with self._lock:
            return self._outputs.get(name)

    def get_output_errors(self) -> dict[str, str]:
        """Obtener todos los errores de salidas."""
        with self._lock:
            return self._errors.copy()

    def clear_output_errors(self) -> None:
        """Limpiar todos los errores de salidas."""
        with self._lock:
            for name in self._errors.keys():
                self._errors[name] = None
                self._reconnect_attempts[name] = 0


# Auto-register
def _register():
    """Auto-register this output module."""
    try:
        from core.io_factory import OutputFactory

        OutputFactory.register("composite", CompositeOutput)
    except ImportError:
        pass


_register()
