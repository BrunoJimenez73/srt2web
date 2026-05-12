"""
Logging Setup - Extraído de main.py

Configuración de logging con consola, file rotation y broadcast a WebSocket.
Extraído para mejorar mantenibilidad.
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from re import Pattern
from typing import Any, Optional


class BroadcastHandler(logging.Handler):
    """Custom handler that sends logs to WebSocket subscribers."""

    _broadcaster = None

    @classmethod
    def set_broadcaster(cls, broadcaster: Any) -> None:
        cls._broadcaster = broadcaster

    def emit(self, record: logging.LogRecord) -> None:
        if self._broadcaster is None:
            return
        try:
            msg = self.format(record)
            self._broadcaster.broadcast(record.levelname.lower(), msg)
        except Exception:
            # Swallowing exceptions in logging handlers to prevent infinite loops
            pass


class ConsoleFilter(logging.Filter):
    """Filter out security warnings from console output."""

    SECURITY_PATTERNS = ("SECURITY:", "auth_token not configured")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pattern in self.SECURITY_PATTERNS:
            if pattern in msg:
                return False
        return True


def get_filter_patterns() -> list[str]:
    """Patterns to filter from frontend logs (noisy but non-critical)."""
    return [
        "[FFmpeg]",
        "[FFmpeg RTMP]",
        "CUDA not available",
        "falling back to CPU",
        "using CPU for",
        "Heartbeat timeout",
        "[WS] Reconnecting",
        "No input video chunk",
        "Audio padding failed",
        "Audio truncation failed",
        "Failed to process TTS audio",
        "connection lost",
        "attempting reconnect",
        "srt_input",
        "rtmp_input",
        "SECURITY:",
        "auth_token not configured",
    ]


def _compile_filter_pattern(patterns: list[str]) -> Pattern[str]:
    """Compile all filter patterns into a single regex for O(1) matching."""
    escaped = [re.escape(p) for p in patterns]
    return re.compile("|".join(escaped))


def setup_logging(log_file: Optional[str] = None, log_broadcaster: Any = None, log_level: int = logging.DEBUG) -> None:
    """
    Configure logging with console, file, and WebSocket broadcast.

    Args:
        log_file: Path to log file. If None, uses default 'logs/srt2web.log'
        log_broadcaster: LogBroadcaster instance for WebSocket broadcast
        log_level: Minimum log level (default DEBUG)
    """
    # Set broadcaster for BroadcastHandler
    if log_broadcaster:
        BroadcastHandler.set_broadcaster(log_broadcaster)

    # Compile filter pattern once (single regex pass per log line)
    filter_regex = _compile_filter_pattern(get_filter_patterns())

    class FilteredBroadcastHandler(logging.Handler):
        """Broadcast handler that filters noisy messages."""

        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
                # Single regex pass instead of O(n) pattern iterations
                if filter_regex.search(msg) or filter_regex.search(record.name):
                    return
                if log_broadcaster:
                    log_broadcaster.broadcast(record.levelname.lower(), msg)
            except Exception:
                pass

    class FilteredFileHandler(logging.Handler):
        """File handler that filters noisy messages."""

        def __init__(self, file_handler: logging.Handler) -> None:
            super().__init__()
            self._file_handler = file_handler

        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
                if filter_regex.search(msg) or filter_regex.search(record.name):
                    return
                self._file_handler.emit(record)
            except Exception:
                pass

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter(
            "%(asctime)s │ %(levelname)-5s │ %(name)s │ %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    console.addFilter(ConsoleFilter())

    # Broadcast handler (sends to WebSocket clients)
    broadcast = FilteredBroadcastHandler()
    broadcast.setLevel(logging.DEBUG)
    broadcast.setFormatter(logging.Formatter("%(levelname)-5s │ %(name)s │ %(message)s"))

    # File handler - persists logs to disk for debugging crashes
    if log_file is None:
        project_root = Path(__file__).resolve().parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(logs_dir / "srt2web.log")

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s │ %(levelname)-5s │ %(name)s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # Wrap file handler with filter (avoid duplicating RotatingFileHandler logic)
    filtered_file = FilteredFileHandler(file_handler)
    filtered_file.setLevel(log_level)

    # Root logger — clear previous handlers to avoid duplicates on reinit
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)
    root.addHandler(console)
    root.addHandler(broadcast)
    root.addHandler(filtered_file)

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(f"srt2web.{name}")


__all__ = [
    "setup_logging",
    "get_logger",
    "get_filter_patterns",
]
