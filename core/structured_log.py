"""
Structured Logging - Logs estructurados con campos estandarizados.

Provee funciones para generar logs con campos consistentes:
- module: Nombre del modulo
- chunk_index: Indice del chunk (si aplica)
- stage: Etapa del procesamiento
- duration_ms: Tiempo de ejecucion en ms
- status: success/error/warning
- message: Mensaje descriptivo

Uso:
    from core.structured_log import log_structured, ModuleLogger
    
    # Log simple
    log_structured("transcriber", "transcribe", chunk_index=1, duration_ms=150.5, status="success")
    
    # Usando ModuleLogger (recomendado)
    logger = ModuleLogger("transcriber")
    logger.info("transcribe", chunk_index=1, duration_ms=150.5)
    logger.error("transcribe", error="CUDA not available")
"""

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

# Logger principal
_logger = logging.getLogger("srt2web.structured")


def log_structured(
    module: str,
    stage: str,
    level: str = "info",
    chunk_index: Optional[int] = None,
    duration_ms: Optional[float] = None,
    status: str = "info",
    message: str = "",
    extra: Optional[dict] = None,
) -> None:
    """
    Log estructurado con campos estandarizados.

    Args:
        module: Nombre del modulo (transcriber, tts, muxer, etc.)
        stage: Etapa del procesamiento (transcribe, generate, mux, etc.)
        level: Nivel de log (debug, info, warning, error)
        chunk_index: Indice del chunk (opcional)
        duration_ms: Tiempo de ejecucion en milisegundos
        status: Estado del procesamiento (success, error, warning, info)
        message: Mensaje descriptivo
        extra: Campos adicionales (opcional)
    """
    log_data = {
        "module": module,
        "stage": stage,
        "status": status,
        "timestamp": time.time(),
    }

    if chunk_index is not None:
        log_data["chunk_index"] = chunk_index
    if duration_ms is not None:
        log_data["duration_ms"] = round(duration_ms, 2)
    if message:
        log_data["message"] = message
    if extra:
        log_data.update(extra)

    # Formatear como JSON para facil parsing
    log_message = json.dumps(log_data, ensure_ascii=False)

    # Enviar al logger correspondiente
    log_func = getattr(_logger, level, _logger.info)
    log_func(log_message)


class ModuleLogger:
    """
    Logger estructurado para un modulo especifico.

    Provee metodos convenientes para logging estructurado:
    - info(), warning(), error(), debug()
    - time_stage() como context manager para medir tiempos
    """

    def __init__(self, module_name: str):
        """
        Inicializar logger para un modulo.

        Args:
            module_name: Nombre del modulo (ej: "transcriber", "tts_engine")
        """
        self.module = module_name
        self._logger = logging.getLogger(f"srt2web.{module_name}")

    def _log(
        self,
        level: str,
        stage: str,
        chunk_index: Optional[int] = None,
        correlation_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        status: str = "info",
        message: str = "",
        **kwargs,
    ) -> None:
        """Metodo interno para generar log estructurado."""
        log_structured(
            module=self.module,
            stage=stage,
            level=level,
            chunk_index=chunk_index,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            status=status,
            message=message,
            extra=kwargs if kwargs else None,
        )

    def debug(
        self,
        stage: str,
        chunk_index: Optional[int] = None,
        duration_ms: Optional[float] = None,
        message: str = "",
        **kwargs,
    ) -> None:
        """Log nivel debug."""
        self._log("debug", stage, chunk_index, duration_ms, "debug", message, **kwargs)

    def info(
        self,
        stage: str,
        chunk_index: Optional[int] = None,
        duration_ms: Optional[float] = None,
        message: str = "",
        **kwargs,
    ) -> None:
        """Log nivel info."""
        self._log("info", stage, chunk_index, duration_ms, "success", message, **kwargs)

    def warning(
        self,
        stage: str,
        chunk_index: Optional[int] = None,
        duration_ms: Optional[float] = None,
        message: str = "",
        **kwargs,
    ) -> None:
        """Log nivel warning."""
        self._log("warning", stage, chunk_index, duration_ms, "warning", message, **kwargs)

    def error(
        self,
        stage: str,
        chunk_index: Optional[int] = None,
        duration_ms: Optional[float] = None,
        message: str = "",
        error: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log nivel error."""
        extra = {"error": error} if error else {}
        extra.update(kwargs)
        self._log("error", stage, chunk_index, duration_ms, "error", message, **extra)

    @contextmanager
    def time_stage(
        self,
        stage: str,
        chunk_index: Optional[int] = None,
        level: str = "info",
        **kwargs,
    ):
        """
        Context manager para medir tiempo de ejecucion de una etapa.

        Uso:
            with logger.time_stage("transcribe", chunk_index=1) as timer:
                result = transcribe_audio()
            # Automaticamente logea duration_ms al salir

        Yields:
            dict con start_time que se actualiza con duration_ms
        """
        start = time.perf_counter()
        context = {"start_time": start, "duration_ms": 0}
        try:
            yield context
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            context["duration_ms"] = elapsed_ms
            self._log(
                level,
                stage,
                chunk_index=chunk_index,
                duration_ms=elapsed_ms,
                status="success" if level != "error" else "error",
                **kwargs,
            )


@contextmanager
def time_operation(module: str, stage: str, chunk_index: Optional[int] = None, **kwargs):
    """
    Context manager global para medir operaciones.

    Uso:
        with time_operation("transcriber", "transcribe", chunk_index=1) as t:
            result = transcribe()
    """
    logger = ModuleLogger(module)
    with logger.time_stage(stage, chunk_index, **kwargs) as ctx:
        yield ctx


def parse_structured_log(log_line: str) -> Optional[dict]:
    """
    Parsear un log estructurado desde una linea de texto.

    Args:
        log_line: Linea de log (debe ser JSON valido)

    Returns:
        Dict con campos del log, o None si no es JSON valido
    """
    try:
        # Buscar JSON en la linea (puede tener prefijo de log estandar)
        start = log_line.find("{")
        if start == -1:
            return None
        end = log_line.rfind("}") + 1
        json_str = log_line[start:end]
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None
end]
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None
