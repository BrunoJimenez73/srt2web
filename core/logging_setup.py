"""
Logging Setup
"""

import json
import logging
import re
from logging.handlers import RotatingFileHandler
from re import Pattern
from typing import Any

from core.paths import get_user_log_dir

logger = logging.getLogger(__name__)


class BroadcastHandler(logging.Handler):
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
        except Exception as e:
            logger.debug("Suppressed error: %s", e, exc_info=True)


class ConsoleFilter(logging.Filter):
    SECURITY_PATTERNS = ("SECURITY:", "auth_token not configured")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return all(pattern not in msg for pattern in self.SECURITY_PATTERNS)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def get_filter_patterns() -> list[str]:
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
    escaped = [re.escape(p) for p in patterns]
    return re.compile("|".join(escaped))


def _make_formatter(log_format: str) -> logging.Formatter:
    if log_format == "json":
        return JSONFormatter(
            "%(asctime)s %(levelname)-5s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    return logging.Formatter(
        "%(asctime)s %(levelname)-5s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logging(
    log_file: str | None = None,
    log_broadcaster: Any = None,
    log_level: int = logging.DEBUG,
    log_format: str = "text",
) -> None:
    if log_broadcaster:
        BroadcastHandler.set_broadcaster(log_broadcaster)

    filter_regex = _compile_filter_pattern(get_filter_patterns())

    class FilteredBroadcastHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
                if filter_regex.search(msg) or filter_regex.search(record.name):
                    return
                if log_broadcaster:
                    log_broadcaster.broadcast(record.levelname.lower(), msg)
            except Exception as e:
                logger.debug("Suppressed error: %s", e, exc_info=True)

    class FilteredFileHandler(logging.Handler):
        def __init__(self, file_handler: logging.Handler) -> None:
            super().__init__()
            self._file_handler = file_handler

        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
                if filter_regex.search(msg) or filter_regex.search(record.name):
                    return
                self._file_handler.emit(record)
            except Exception as e:
                logger.debug("Suppressed error: %s", e, exc_info=True)

    file_fmt = _make_formatter(log_format)
    console_fmt = logging.Formatter(
        "%(asctime)s %(levelname)-5s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(console_fmt)
    console.addFilter(ConsoleFilter())

    broadcast = FilteredBroadcastHandler()
    broadcast.setLevel(logging.DEBUG)
    broadcast.setFormatter(logging.Formatter("%(levelname)-5s %(name)s %(message)s"))

    if log_file is None:
        logs_dir = get_user_log_dir()
        log_file = str(logs_dir / "srt2web.log")

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_fmt)

    filtered_file = FilteredFileHandler(file_handler)
    filtered_file.setLevel(log_level)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)
    root.addHandler(console)
    root.addHandler(broadcast)
    root.addHandler(filtered_file)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"srt2web.{name}")


__all__ = [
    "setup_logging",
    "get_logger",
    "get_filter_patterns",
    "JSONFormatter",
]
