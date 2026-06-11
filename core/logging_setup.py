"""
Logging Setup - Centralized logging configuration with security audit channel.

Three log channels, all with rotation:
  - logs/srt2web.log   — main app log (RotatingFileHandler, 10MB, 3 backups)
  - logs/security.log  — security events only (srt2web.security logger, 10MB, 3 backups)
  - logs/crash.log     — unhandled exceptions via sys.excepthook (5MB, 2 backups)

F114 ensures the three channels are predictable, separated by concern, and
testable. main.py calls install_crash_handler() to capture unhandled exceptions.
"""

import json
import logging
import re
import sys
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path
from re import Pattern
from types import TracebackType
from typing import Any

from core.paths import get_user_log_dir

logger = logging.getLogger(__name__)

# Security events use this logger name prefix
SECURITY_LOGGER_PREFIX = "srt2web.security"

# Crash log: written via sys.excepthook, only on unhandled exceptions
CRASH_LOGGER_NAME = "srt2web.crash"
CRASH_LOG_FILENAME = "crash.log"
CRASH_MAX_BYTES = 5 * 1024 * 1024  # 5MB
CRASH_BACKUP_COUNT = 2


class SecurityLogHandler(RotatingFileHandler):
    """Dedicated handler for security-auditable events.
    Writes to a separate security.log file (never filtered).
    """

    def __init__(self, log_dir: str | None = None) -> None:
        if log_dir is None:
            log_dir = str(get_user_log_dir())
        super().__init__(
            f"{log_dir}/security.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        self.setLevel(logging.WARNING)
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-5s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )


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
    """Filters repetitive security warnings from console output.
    Security events are still logged to the security.log file.
    """

    NOISE_PATTERNS = ("SECURITY:", "auth_token not configured")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return all(pattern not in msg for pattern in self.NOISE_PATTERNS)


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
    """Noise suppression patterns for broadcast and file log handlers.
    Security events are NOT filtered here — they go to security.log.
    """
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

        def close(self) -> None:
            self._file_handler.close()
            super().close()

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

    # F114: derive the log dir from the chosen log_file so security.log and
    # any future channels live alongside srt2web.log. This makes setup_logging
    # predictable when called with a custom log_file (tests, embedded use).
    log_dir = str(Path(log_file).parent)

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

    security_handler = SecurityLogHandler(log_dir=log_dir)

    root = logging.getLogger()
    # Close old handlers before clearing (Windows file lock release)
    for h in root.handlers:
        try:
            h.close()
        except Exception:
            pass
    root.handlers.clear()
    root.setLevel(log_level)
    root.addHandler(console)
    root.addHandler(broadcast)
    root.addHandler(filtered_file)
    root.addHandler(security_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"srt2web.{name}")


def install_crash_handler(log_dir: str | Path | None = None) -> logging.Logger | None:
    """
    F114: Install a sys.excepthook that writes unhandled exceptions to crash.log.

    The crash logger:
      - Writes to ``{log_dir}/crash.log`` (RotatingFileHandler, 5MB, 2 backups)
      - Uses a dedicated logger (``srt2web.crash``) with ``propagate=False``
        so the crash entry does NOT also appear in srt2web.log
      - Replaces ``sys.excepthook`` while preserving the original hook so
        the user still sees the traceback on stderr

    Returns the crash logger, or None if the file could not be opened.

    Safe to call multiple times: each call replaces the prior hook and
    reopens the file handler. Call this early in main.py (after basic
    imports) so crashes during startup are captured.
    """
    if log_dir is None:
        # Resolve at call time (not import time) so tests can monkeypatch
        # core.paths.get_user_log_dir. This mirrors the pattern used elsewhere
        # in the codebase and keeps install_crash_handler testable.
        import core.paths

        log_dir = core.paths.get_user_log_dir()
    log_path = Path(log_dir)
    try:
        log_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.stderr.write(f"F114: cannot create log dir {log_path}: {e}\n")
        return None
    crash_path = log_path / CRASH_LOG_FILENAME
    try:
        crash_handler = RotatingFileHandler(
            crash_path,
            maxBytes=CRASH_MAX_BYTES,
            backupCount=CRASH_BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError as e:
        sys.stderr.write(f"F114: cannot open crash log {crash_path}: {e}\n")
        return None

    crash_handler.setLevel(logging.CRITICAL)
    crash_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s\n%(message)s\n---\n",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    crash_logger = logging.getLogger(CRASH_LOGGER_NAME)
    crash_logger.setLevel(logging.CRITICAL)
    # Replace handlers on every call so re-installation is idempotent
    # Must close old handlers first so the file lock is released (Windows).
    for h in crash_logger.handlers:
        try:
            h.close()
        except Exception:
            pass
    crash_logger.handlers.clear()
    crash_logger.addHandler(crash_handler)
    crash_logger.propagate = False  # do NOT also write to srt2web.log

    _original_excepthook: Callable[[type[BaseException], BaseException, TracebackType | None], Any] = sys.excepthook

    def _excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        # SystemExit/KeyboardInterrupt are normal control flow — don't pollute crash log
        if issubclass(exc_type, (SystemExit, KeyboardInterrupt)):
            _original_excepthook(exc_type, exc_value, exc_traceback)
            return
        try:
            crash_logger.critical(
                "Unhandled exception: %s",
                exc_value,
                exc_info=(exc_type, exc_value, exc_traceback),
            )
        except Exception:
            # Never let the crash handler itself crash — that would hide the
            # original exception. Best-effort: write minimal info to stderr.
            sys.stderr.write(f"F114 crash handler failed for {exc_type.__name__}: {exc_value}\n")
        # Always show the user the traceback via the original excepthook
        _original_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _excepthook
    return crash_logger


__all__ = [
    "CRASH_LOGGER_NAME",
    "CRASH_LOG_FILENAME",
    "SECURITY_LOGGER_PREFIX",
    "JSONFormatter",
    "SecurityLogHandler",
    "get_filter_patterns",
    "get_logger",
    "install_crash_handler",
    "setup_logging",
]
