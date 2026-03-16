"""
Output Sink - Clase base abstracta para destinos de salida.

Proporciona una interfaz común para diferentes tipos de destinos:
- Web/HLS: Streaming via HLS para navegador
- SRT: Protocolo SRT para re-transmisión
- RTMP: Protocolo RTMP (YouTube, Twitch, etc.)
- Audio: Solo salida de audio
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
import logging

from core.module_base import PipelineData


class OutputSink(ABC):
    """
    Interfaz base para todos los destinos de salida.

    Attributes:
        name: Identificador del tipo de output
        config: Configuración específica del output
    """

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"srt2web.output.{name}")
        self._output_dir: str = ""

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

    def get_stream_info(self) -> dict:
        """
        Obtener información del stream para el cliente.

        Returns:
            Dict con URLs, puertos, etc.
        """
        return {"type": self.name}

    def set_output_dir(self, output_dir: str) -> None:
        """Establecer el directorio de salida."""
        self._output_dir = output_dir

    def configure(self, config: dict) -> None:
        """
        Aplicar configuración específica del output.
        Override en subclases para manejar config específica.
        """
        self.config = config
