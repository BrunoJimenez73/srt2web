"""
Input Source - Clase base abstracta para fuentes de entrada.

Proporciona una interfaz común para diferentes tipos de fuentes de input:
- SRT: Protocolo SRT para streams en tiempo real
- File: Archivos de video locales
- RTMP: Protocolo RTMP
- Audio: Solo fuente de audio
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from core.module_base import PipelineData


class InputSource(ABC):
    """
    Interfaz base para todas las fuentes de entrada.

    Attributes:
        name: Identificador del tipo de input
        config: Configuración específica del input
    """

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"srt2web.input.{name}")
        self._output_dir: str = ""

    @abstractmethod
    def start(self) -> None:
        """
        Iniciar la fuente de entrada.
        Debe inicializar recursos (procesos FFmpeg, abrir archivos, etc.)
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Detener la fuente de entrada.
        Debe liberar todos los recursos.
        """
        pass

    @abstractmethod
    def get_next_chunk(self) -> PipelineData | None:
        """
        Obtener el siguiente chunk de datos.

        Returns:
            PipelineData con los datos del chunk, o None si no hay datos disponibles.
        """
        pass

    @abstractmethod
    def is_receiving(self) -> bool:
        """
        Verificar si la fuente está activa y recibiendo datos.

        Returns:
            True si está recibiendo datos, False en caso contrario.
        """
        pass

    def get_connection_info(self) -> dict[str, Any]:
        """
        Obtener información de conexión para mostrar al usuario.

        Returns:
            Dict con información relevante (URL, puerto, etc.)
        """
        return {"type": self.name}

    def set_output_dir(self, output_dir: str) -> None:
        """Establecer el directorio de salida para archivos temporales."""
        self._output_dir = output_dir

    def configure(self, config: dict[str, Any]) -> None:
        """
        Aplicar configuración específica del input.
        Override en subclases para manejar config específica.
        """
        self.config = config
