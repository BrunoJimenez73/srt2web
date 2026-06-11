"""
Pipeline Manager - Soporte para múltiples pipelines concurrentes.

Gestiona una colección de pipelines UnifiedPipeline aislados con límites
configurables de recursos y control de ciclo de vida.
"""

import copy
import logging
import threading
import uuid
from typing import Any

from core.schemas import PipelineMode
from core.unified_pipeline import UnifiedPipeline

logger = logging.getLogger("srt2web.pipeline_manager")


class PipelineManager:
    """Gestor de múltiples pipelines con aislamiento y límites de recursos."""

    def __init__(self, max_pipelines: int = 10):
        """
        Inicializar el gestor de pipelines.

        Args:
            max_pipelines: Número máximo de pipelines concurrentes permitidos.
        """
        self._pipelines: dict[str, UnifiedPipeline] = {}
        self._lock = threading.Lock()
        self._max_pipelines = max_pipelines
        logger.info(f"PipelineManager initialized (max_pipelines={max_pipelines})")

    def create_pipeline(
        self,
        config: dict[str, Any],
        output_dir: str,
        mode: PipelineMode = PipelineMode.THREAD_PARALLEL,
        max_concurrent_chunks: int = 2,
    ) -> str:
        """
        Crear y registrar un nuevo pipeline con configuración propia.

        Args:
            config: Configuración del pipeline.
            output_dir: Directorio de salida.
            mode: Modo de operación.
            max_concurrent_chunks: Número máximo de chunks concurrentes.

        Returns:
            ID único del pipeline creado.

        Raises:
            RuntimeError: Si se alcanza el límite de pipelines.
        """
        with self._lock:
            if len(self._pipelines) >= self._max_pipelines:
                raise RuntimeError(f"Pipeline limit reached (max={self._max_pipelines})")

            pipeline_id = str(uuid.uuid4())
            merged_config = self._merge_config(config)
            pipeline = UnifiedPipeline(
                mode=mode,
                max_concurrent_chunks=max_concurrent_chunks,
                buffer_size=merged_config.get("pipeline", {}).get("buffer_size", 5),
                retry_attempts=merged_config.get("pipeline", {}).get("retry_attempts", 2),
                retry_delay=merged_config.get("pipeline", {}).get("retry_delay", 1.0),
                lost_chunk_timeout_sec=merged_config.get("pipeline", {}).get("lost_chunk_timeout_sec", 30.0),
            )

            self._pipelines[pipeline_id] = pipeline
            logger.info(
                f"Pipeline created (id={pipeline_id}, mode={mode.value}, " f"max_chunks={max_concurrent_chunks})"
            )
            return pipeline_id

    def get_pipeline(self, pipeline_id: str) -> UnifiedPipeline | None:
        """Obtener un pipeline por su ID."""
        return self._pipelines.get(pipeline_id)

    async def stop_pipeline(self, pipeline_id: str) -> bool:
        """
        Detener y remover un pipeline.

        Args:
            pipeline_id: ID del pipeline a detener.

        Returns:
            True si el pipeline fue encontrado y detenido, False en otro caso.
        """
        with self._lock:
            pipeline = self._pipelines.pop(pipeline_id, None)

        if pipeline:
            try:
                await pipeline.stop()
                logger.info(f"Pipeline stopped (id={pipeline_id})")
            except Exception as e:
                logger.error(f"Error stopping pipeline (id={pipeline_id}): {e}")
            return True

        logger.warning(f"Pipeline not found for stop (id={pipeline_id})")
        return False

    def list_pipelines(self) -> list[str]:
        """Listar IDs de todos los pipelines activos."""
        with self._lock:
            return list(self._pipelines.keys())

    def get_pipeline_count(self) -> int:
        """Obtener el número de pipelines activos."""
        with self._lock:
            return len(self._pipelines)

    def start_pipeline(self, pipeline_id: str, on_log: Any, on_state_change: Any) -> bool:
        """
        Iniciar un pipeline existente.

        Args:
            pipeline_id: ID del pipeline.
            on_log: Callback para logs.
            on_state_change: Callback para cambios de estado.

        Returns:
            True si se inició correctamente.
        """
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            logger.warning(f"Pipeline not found for start (id={pipeline_id})")
            return False

        try:
            pipeline.start(
                on_log=on_log,
                on_state_change=on_state_change,
            )
            logger.info(f"Pipeline started (id={pipeline_id})")
            return True
        except Exception as e:
            logger.error(f"Error starting pipeline (id={pipeline_id}): {e}")
            return False

    def _merge_config(self, custom_config: dict[str, Any]) -> dict[str, Any]:
        """Fusionar configuración personalizada con defaults (deep merge recursivo).

        F128: Reemplaza el antiguo dict.update() de un solo nivel que perdía
        sub-dicts completos (ej: custom {"output": {"web": {"segment_duration": 5}}}
        borraba list_size del default).
        """
        default: dict[str, Any] = {
            "pipeline": {
                "chunk_duration_sec": 10,
                "buffer_size": 5,
                "retry_attempts": 2,
                "retry_delay": 1.0,
                "lost_chunk_timeout_sec": 30.0,
            },
            "input": {"type": "srt", "srt": {"chunk_duration_sec": 10}},
            "output": {
                "type": "web",
                "web": {"segment_duration": 10, "list_size": 2},
            },
            "modules": {
                "audio_mixer": {"original_volume": 0.15},
                "transcriber": {"beam_size": 2},
                "tts_engine": {"device": "cpu"},
                "hls_output": {},
            },
        }

        result = copy.deepcopy(default)
        for key, value in custom_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)

        return result

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge override into base. Override values take precedence."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = PipelineManager._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
