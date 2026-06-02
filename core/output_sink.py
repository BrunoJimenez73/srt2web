"""
Output Sink - Clase base abstracta para destinos de salida.

Proporciona una interfaz común para diferentes tipos de destinos:
- Web/HLS: Streaming via HLS para navegador
- SRT: Protocolo SRT para re-transmisión
- RTMP: Protocolo RTMP (YouTube, Twitch, etc.)
- Audio: Solo salida de audio
"""

import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from core.module_base import PipelineData
from core.schemas import ModuleState, ModuleStatus


class HealthState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


# Global broadcaster for output health events (set by server/ws_routes.py)
_output_health_broadcaster = None


def set_output_health_broadcaster(broadcaster: Any) -> None:
    """Set the broadcaster for output health events."""
    global _output_health_broadcaster
    _output_health_broadcaster = broadcaster


class OutputSink(ABC):
    """
    Interfaz base para todos los destinos de salida.

    Attributes:
        name: Identificador del tipo de output
        config: Configuración específica del output
    """

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"srt2web.output.{name}")
        self._output_dir: str = ""
        self._enabled: bool = config.get("enabled", True)

        # Health tracking
        self._uptime_start: float = time.time()
        self._last_write_time: float = 0.0
        self._bytes_written: int = 0
        self._last_error: str | None = None
        self._last_error_time: float | None = None
        self._health_state: HealthState = HealthState.HEALTHY

    @abstractmethod
    def start(self) -> None:
        """
        Iniciar el destino de salida.
        Debe inicializar recursos necesarios.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Detener el destino de salida.
        Debe liberar todos los recursos.
        """
        pass

    @abstractmethod
    def write(self, data: PipelineData) -> None:
        """
        Escribir datos al destino.

        Args:
            PipelineData con los datos a escribir.
        """
        pass

    def _update_write_stats(self, size_bytes: int) -> None:
        """Actualizar estadísticas de escritura."""
        self._last_write_time = time.time()
        self._bytes_written += size_bytes
        # Clear error on successful write
        if self._last_error is not None:
            self._last_error = None
            self._last_error_time = None

    def _set_error(self, error_msg: str) -> None:
        """Establecer el último error ocurrido."""
        self._last_error = error_msg
        self._last_error_time = time.time()

    def _clear_error(self) -> None:
        """Limpiar el último error."""
        self._last_error = None
        self._last_error_time = None

    def get_stream_info(self) -> dict[str, Any]:
        """
        Obtener información del stream para el cliente.

        Returns:
            Dict con URLs, puertos, etc.
        """
        return {"type": self.name}

    def set_output_dir(self, output_dir: str) -> None:
        """Establecer el directorio de salida."""
        self._output_dir = output_dir

    def configure(self, config: dict[str, Any]) -> None:
        """
        Aplicar configuración específica del output.
        Override en subclases para manejar config específica.
        """
        self.config = config

    def get_status(self) -> ModuleStatus:
        """
        Obtener estado del output.
        Override en subclases para proporcionar estado específico.
        """
        return ModuleStatus(
            name=self.name,
            state=ModuleState.IDLE,
            enabled=True,
            processed_chunks=0,
            last_process_time_ms=0.0,
            extra={},
        )

    def health_check(self) -> HealthState:
        """
        Verificar la salud del output.
        Debe ser implementado por subclases para verificar estado específico.

        Returns:
            HealthState: estado de salud actual.
        """
        # Por defecto, considerar saludable si no hay errores recientes y ha escrito en los últimos 30s
        if self._last_error is not None:
            return HealthState.FAILED
        if time.time() - self._last_write_time > 30:
            return HealthState.DEGRADED
        return HealthState.HEALTHY

    def check_health(self) -> None:
        """
        Verificar salud y emitir evento si ha cambiado.
        """
        new_state = self.health_check()
        if new_state != self._health_state:
            old_state = self._health_state
            self._health_state = new_state
            self.logger.info(f"Health state changed from {old_state} to {new_state}")
            # Emitir evento WebSocket si hay broadcaster
            if _output_health_broadcaster is not None:
                try:
                    _output_health_broadcaster.broadcast_output_health(
                        output_name=self.name,
                        health=new_state.value,
                        extra={
                            "uptime": time.time() - self._uptime_start,
                            "bytes_written": self._bytes_written,
                            "last_error": self._last_error,
                            "last_error_time": self._last_error_time,
                        },
                    )
                except Exception as e:
                    self.logger.error(f"Failed to broadcast health event: {e}")
