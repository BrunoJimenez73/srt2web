"""
Composite Output - Gestiona múltiples salidas simultáneamente.
Delega el trabajo a cada salida individual.
"""

import threading
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from core.module_base import PipelineData
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
        self._outputs: Dict[str, OutputSink] = {}
        self._errors: Dict[str, str] = {}
        self._reconnect_attempts: Dict[str, int] = {}
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 5.0  # segundos
        self._lock = threading.Lock()

    def add_output(self, name: str, output: OutputSink) -> None:
        """Añadir una nueva salida al composite."""
        with self._lock:
            self._outputs[name] = output
            self._errors[name] = None
            self._reconnect_attempts[name] = 0

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

    def get_status(self) -> dict:
        """Obtener estado de todas las salidas (compatible con formato legacy)."""
        # Obtener el primer output para metrics legacy
        first_output = None
        first_name = None
        with self._lock:
            if self._outputs:
                first_name = list(self._outputs.keys())[0]
                first_output = list(self._outputs.values())[0]
        
        # Base del primer output o defaults
        if first_output and hasattr(first_output, 'get_status'):
            try:
                first_status = first_output.get_status()
                # Escribir merged en el dict principal para compatibilidad con API
                merged = {
                    "type": "composite",
                    "state": first_status.get("state", "idle"),
                    "enabled": first_status.get("enabled", True),
                    "processed_chunks": first_status.get("processed_chunks", 0),
                    "last_process_time_ms": first_status.get("last_process_time_ms", 0),
                    "extra": first_status.get("extra", {}),
                }
            except Exception:
                merged = {"type": "composite", "state": "idle", "enabled": True}
        else:
            merged = {"type": "composite", "state": "idle", "enabled": True}
        
        # Agregar outputs individuales
        outputs_dict = {}
        with self._lock:
            for name, output in self._outputs.items():
                try:
                    output_status = output.get_status()
                    outputs_dict[name] = {
                        "name": name,
                        "state": output_status.get("state", "unknown"),
                        "enabled": output_status.get("enabled", True),
                        "processed_chunks": output_status.get("processed_chunks", 0),
                        "last_process_time_ms": output_status.get("last_process_time_ms", 0),
                        "extra": output_status.get("extra", {})
                    }
                except Exception as e:
                    outputs_dict[name] = {
                        "name": name,
                        "state": "error",
                        "enabled": True,
                        "error": str(e)
                    }
        
        merged["outputs"] = outputs_dict
        merged["errors"] = self._errors.copy()
        return merged

    def get_output_status(self, name: str) -> Optional[OutputStatus]:
        """Obtener estado de una salida específica."""
        with self._lock:
            if name not in self._outputs:
                return None

            output = self._outputs[name]
            try:
                output_status = output.get_status()
                return OutputStatus(
                    name=name,
                    state=output_status.get("state", "unknown"),
                    enabled=output_status.get("enabled", True),
                    error=self._errors.get(name),
                    processed_chunks=output_status.get("processed_chunks", 0),
                    last_process_time_ms=output_status.get("last_process_time_ms", 0),
                    extra=output_status.get("extra", {})
                )
            except Exception as e:
                return OutputStatus(
                    name=name,
                    state="error",
                    enabled=True,
                    error=str(e)
                )

    def get_all_output_statuses(self) -> List[dict]:
        """Obtener estado de todas las salidas como diccionarios."""
        with self._lock:
            statuses = []
            for name, output in self._outputs.items():
                try:
                    output_status = output.get_status()
                    statuses.append({
                        "name": name,
                        "type": getattr(output, 'name', type(output).__name__.lower().replace('output', '')),
                        "state": output_status.get("state", "unknown"),
                        "enabled": output_status.get("enabled", True),
                        "error": self._errors.get(name),
                        "processed_chunks": output_status.get("processed_chunks", 0),
                        "last_process_time_ms": output_status.get("last_process_time_ms", 0),
                        "extra": output_status.get("extra", {}),
                        "stream_info": output.get_stream_info() if hasattr(output, 'get_stream_info') else {},
                    })
                except Exception as e:
                    statuses.append({
                        "name": name,
                        "type": type(output).__name__.lower().replace('output', ''),
                        "state": "error",
                        "enabled": getattr(output, 'enabled', True),
                        "error": f"Error al obtener estado: {str(e)}",
                        "processed_chunks": 0,
                        "last_process_time_ms": 0.0,
                        "extra": {},
                        "stream_info": {},
                    })
            return statuses

    def is_output_enabled(self, name: str) -> bool:
        """Verificar si una salida está habilitada."""
        with self._lock:
            if name not in self._outputs:
                return False
            output = self._outputs[name]
            if hasattr(output, 'enabled'):
                return output.enabled
            if hasattr(output, '_enabled'):
                return output._enabled
            return True

    def enable_output(self, name: str, enable: bool = True) -> bool:
        """Habilitar/deshabilitar una salida."""
        with self._lock:
            if name not in self._outputs:
                return False
            output = self._outputs[name]
            if hasattr(output, 'enabled'):
                output.enabled = enable
                return True
            if hasattr(output, '_enabled'):
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

    def get_output_names(self) -> List[str]:
        """Obtener lista de nombres de salidas."""
        with self._lock:
            return list(self._outputs.keys())

    def get_output_types(self) -> List[str]:
        """Obtener lista de tipos de salidas."""
        with self._lock:
            return [type(output).__name__ for output in self._outputs.values()]

    def get_output_by_name(self, name: str) -> Optional[OutputSink]:
        """Obtener una salida por nombre."""
        with self._lock:
            return self._outputs.get(name)

    def get_output_errors(self) -> Dict[str, str]:
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