"""
Pipeline Error Handler - Manejo centralizado de errores y recuperacion.

Responsabilidades:
- Clasificar errores (recuperables vs no recuperables)
- Aplicar politica de reintentos
- Registrar errores con contexto
- Notificar callbacks de error
- Decidir degradacion graceful vs fallo critico
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger("srt2web.pipeline.error_handler")


class ErrorSeverity(str, Enum):
    """Severidad del error."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Categoria del error."""

    MODULE_PROCESSING = "module_processing"
    INPUT_SOURCE = "input_source"
    OUTPUT_SINK = "output_sink"
    QUEUE_FULL = "queue_full"
    QUEUE_EMPTY = "queue_empty"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    """Registro de un error ocurrido en el pipeline."""

    timestamp: float
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    module_name: str | None = None
    chunk_index: int | None = None
    exception: Exception | None = None
    recovery_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "module_name": self.module_name,
            "chunk_index": self.chunk_index,
            "recovery_action": self.recovery_action,
        }


@dataclass
class ErrorPolicy:
    """Politica de manejo de errores."""

    max_retries: int = 2
    retry_delay: float = 1.0
    max_errors_per_minute: int = 10
    max_consecutive_errors: int = 5
    drop_chunk_after_retries: bool = True
    notify_on_critical: bool = True


class PipelineErrorHandler:
    """
    Manejador centralizado de errores para el pipeline.

    Clasifica errores, aplica reintentos, registra historial
    y decide cuando degradar graceful o fallar criticamente.
    """

    def __init__(self, policy: ErrorPolicy | None = None):
        self._policy = policy or ErrorPolicy()
        self._error_history: list[ErrorRecord] = []
        self._consecutive_errors: int = 0
        self._errors_this_minute: int = 0
        self._last_minute_reset: float = time.time()
        self._on_error: Callable[[ErrorRecord], None] | None = None

    @property
    def error_count(self) -> int:
        """Total de errores registrados."""
        return len(self._error_history)

    @property
    def consecutive_error_count(self) -> int:
        """Errores consecutivos sin exito."""
        return self._consecutive_errors

    def set_error_callback(self, callback: Callable[[ErrorRecord], None]) -> None:
        """Configurar callback para notificacion de errores."""
        self._on_error = callback

    def classify_error(self, error: Exception, module_name: str | None = None) -> tuple[ErrorCategory, ErrorSeverity]:
        """
        Clasificar un error por categoria y severidad.

        Returns:
            Tuple de (categoria, severidad)
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Errores de modulo
        if "module" in error_str or module_name:
            return ErrorCategory.MODULE_PROCESSING, ErrorSeverity.ERROR

        # Errores de input
        if any(x in error_str or x in error_type for x in ["input", "srt", "rtmp", "connection", "source"]):
            return ErrorCategory.INPUT_SOURCE, ErrorSeverity.ERROR

        # Errores de output
        if any(x in error_str or x in error_type for x in ["output", "sink", "muxer", "write"]):
            return ErrorCategory.OUTPUT_SINK, ErrorSeverity.ERROR

        # Errores de cola
        if "full" in error_str or "queue" in error_type:
            return ErrorCategory.QUEUE_FULL, ErrorSeverity.WARNING

        if "empty" in error_str:
            return ErrorCategory.QUEUE_EMPTY, ErrorSeverity.INFO

        # Timeouts
        if any(x in error_str or x in error_type for x in ["timeout", "timed out"]):
            return ErrorCategory.TIMEOUT, ErrorSeverity.ERROR

        # Recursos
        if any(x in error_str or x in error_type for x in ["memory", "resource", "exhausted"]):
            return ErrorCategory.RESOURCE_EXHAUSTED, ErrorSeverity.CRITICAL

        return ErrorCategory.UNKNOWN, ErrorSeverity.ERROR

    def is_recoverable(self, error: Exception) -> bool:
        """Determinar si un error es recuperable."""
        recoverable_patterns = [
            "timeout",
            "timed out",
            "temporary",
            "connection",
            "resource",
            "queue full",
            "stream",
            "ffmpeg",
        ]

        error_str = str(error).lower()
        return any(pattern in error_str for pattern in recoverable_patterns)

    def record_error(
        self,
        error: Exception,
        module_name: str | None = None,
        chunk_index: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> ErrorRecord:
        """
        Registrar un error y decidir accion de recuperacion.

        Returns:
            ErrorRecord con la accion de recuperacion sugerida
        """
        category, severity = self.classify_error(error, module_name)
        recoverable = self.is_recoverable(error)

        # Reset contador por minuto si paso mas de 60s
        now = time.time()
        if now - self._last_minute_reset > 60:
            self._errors_this_minute = 0
            self._last_minute_reset = now

        self._errors_this_minute += 1

        # Decidir accion de recuperacion
        recovery_action = self._decide_recovery(
            severity, recoverable, self._consecutive_errors, self._errors_this_minute
        )

        record = ErrorRecord(
            timestamp=now,
            category=category,
            severity=severity,
            message=str(error),
            module_name=module_name,
            chunk_index=chunk_index,
            exception=error,
            recovery_action=recovery_action,
        )

        self._error_history.append(record)

        # Limitar historial a 1000 entries
        if len(self._error_history) > 1000:
            self._error_history = self._error_history[-500:]

        # Actualizar contador de errores consecutivos
        self._consecutive_errors += 1

        # Log segun severidad
        log_level = {
            ErrorSeverity.INFO: "info",
            ErrorSeverity.WARNING: "warning",
            ErrorSeverity.ERROR: "error",
            ErrorSeverity.CRITICAL: "critical",
        }.get(severity, "error")

        log_msg = f"[{category.value}] {module_name or 'pipeline'}: {error}"
        if chunk_index is not None:
            log_msg += f" (chunk {chunk_index})"
        if recovery_action:
            log_msg += f" -> {recovery_action}"

        getattr(logger, log_level, logger.error)(log_msg)

        # Notificar callback
        if self._on_error:
            try:
                self._on_error(record)
            except Exception as e:
                logger.debug("Suppressed error: %s", e, exc_info=True)

        return record

    def record_success(self) -> None:
        """Registrar exito (reset contador de errores consecutivos)."""
        self._consecutive_errors = 0

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determinar si se debe reintentar."""
        if not self.is_recoverable(error):
            return False
        if attempt >= self._policy.max_retries:
            return False
        if self._consecutive_errors >= self._policy.max_consecutive_errors:
            return False
        if self._errors_this_minute >= self._policy.max_errors_per_minute:
            return False
        return True

    def get_retry_delay(self, attempt: int) -> float:
        """Calcular delay para reintento con backoff exponencial."""
        return self._policy.retry_delay * (2**attempt)  # type: ignore[no-any-return]

    def should_degrade(self) -> bool:
        """Determinar si el pipeline debe entrar en modo degradado."""
        return self._consecutive_errors >= self._policy.max_consecutive_errors

    def should_stop(self) -> bool:
        """Determinar si el pipeline debe detenerse por errores criticos."""
        return self._errors_this_minute >= self._policy.max_errors_per_minute * 2

    def get_recent_errors(self, count: int = 10) -> list[dict[str, Any]]:
        """Obtener los ultimos errores registrados."""
        return [err.to_dict() for err in self._error_history[-count:]]

    def clear_history(self) -> None:
        """Limpiar historial de errores."""
        self._error_history.clear()
        self._consecutive_errors = 0
        self._errors_this_minute = 0

    def _decide_recovery(
        self,
        severity: ErrorSeverity,
        recoverable: bool,
        consecutive_errors: int,
        errors_per_minute: int,
    ) -> str | None:
        """Decidir accion de recuperacion basada en contexto."""
        if severity == ErrorSeverity.CRITICAL:
            return "stop_pipeline"

        if consecutive_errors >= self._policy.max_consecutive_errors:
            return "degrade_module"

        if errors_per_minute >= self._policy.max_errors_per_minute:
            return "throttle_processing"

        if recoverable:
            return f"retry_delay_{self._policy.retry_delay}s"

        if severity == ErrorSeverity.WARNING:
            return "continue_with_warning"

        return "skip_chunk"
