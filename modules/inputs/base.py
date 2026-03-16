"""
Clase base para inputs - proporciona funcionalidad común.
"""

from core.input_source import InputSource


class BaseInput(InputSource):
    """
    Clase base común para inputs.

    Proporciona utilidades compartidas para todos los inputs.
    """

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self._chunk_duration = config.get("chunk_duration_sec", 15)
        self._chunks_dir: str = ""

    def _ensure_chunks_dir(self) -> str:
        """Asegurar que existe el directorio de chunks."""
        import os

        if not self._chunks_dir:
            self._chunks_dir = self._output_dir or "./output"
            chunks_dir = f"{self._chunks_dir}/chunks"
            os.makedirs(chunks_dir, exist_ok=True)
            self._chunks_dir = chunks_dir
        return self._chunks_dir

    def get_chunk_duration(self) -> float:
        """Obtener duración configurada de chunks."""
        return self._chunk_duration
