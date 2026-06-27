"""
Clase base para inputs - proporciona funcionalidad común.
"""

from typing import Any

from core.input_source import InputSource


class BaseInput(InputSource):
    """
    Clase base común para inputs.

    Proporciona utilidades compartidas para todos los inputs.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
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
        return float(self._chunk_duration)

    def set_chunk_duration(self, duration: float) -> None:
        """F170 — Actualizar chunk_duration dinámicamente."""
        new_dur = int(max(2, min(60, duration)))
        if new_dur != self._chunk_duration:
            logger = __import__("logging").getLogger("srt2web.input")
            logger.info(f"Chunk duration adapted: {self._chunk_duration}s → {new_dur}s")
            self._chunk_duration = new_dur
