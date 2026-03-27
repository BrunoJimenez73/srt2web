"""
Clase base para outputs - proporciona funcionalidad común.
"""

from core.output_sink import OutputSink


class BaseOutput(OutputSink):
    """
    Clase base común para outputs.

    Proporciona utilidades compartidas para todos los outputs.
    """

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self._segment_duration = config.get("segment_duration", 15)
        self._hls_dir: str = ""

    def _ensure_output_dir(self) -> str:
        """Asegurar que existe el directorio de salida."""
        import os

        if not self._hls_dir:
            self._hls_dir = self._output_dir or "./output"
            output_path = f"{self._hls_dir}"
            os.makedirs(output_path, exist_ok=True)
            self._hls_dir = output_path
        return self._hls_dir

    def get_segment_duration(self) -> float:
        """Obtener duración configurada de segmentos."""
        return self._segment_duration
