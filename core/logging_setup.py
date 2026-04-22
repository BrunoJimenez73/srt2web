"""
Logging Setup - Extraído de main.py

Configuración de logging con consola, file rotation y broadcast a WebSocket.
Extraído para mejorar mantenibilidad.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional, List


class BroadcastHandler(logging.Handler):
    """Custom handler that sends logs to WebSocket subscribers."""
    
    _broadcaster = None
    
    @classmethod
    def set_broadcaster(cls, broadcaster):
        cls._broadcaster = broadcaster
    
    def emit(self, record):
        if self._broadcaster is None:
            return
        try:
            msg = self.format(record)
            self._broadcaster.broadcast(record.levelname.lower(), msg)
        except Exception:
            pass


class ConsoleFilter(logging.Filter):
    """Filter out security warnings from console output."""
    
    SECURITY_PATTERNS = ["SECURITY:", "auth_token not configured"]
    
    def filter(self, record):
        msg = record.getMessage()
        for pattern in self.SECURITY_PATTERNS:
            if pattern in msg:
                return False
        return True


def get_filter_patterns() -> List[str]:
    """Patterns to filter from frontend logs (noisy but non-critical)."""
    return [
        "[FFmpeg]",
        "[FFmpeg RTMP]",
        "CUDA not available",
        "falling back to CPU",
        "using CPU for",
        "Duration drift",
        "Heartbeat timeout",
        "[WS] Reconnecting",
        "No input video chunk",
        "Audio padding failed",
        "Audio truncation failed",
        "Failed to process TTS audio",
        "connection lost",
        "attempting reconnect",
        "Duration drift in subtitle timing",
        "srt_input",
        "rtmp_input",
        "SECURITY:",
        "auth_token not configured",
    ]


def setup_logging(
    log_file: Optional[str] = None,
    log_broadcaster=None,
    log_level: int = logging.DEBUG
) -> None:
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
    
    FILTER_PATTERNS = get_filter_patterns()
    
    class FilteredBroadcastHandler(logging.Handler):
        """Broadcast handler that filters noisy messages."""
        
        def emit(self, record):
            try:
                msg = self.format(record)
                for pattern in FILTER_PATTERNS:
                    if pattern in msg or pattern in record.name:
                        return
                if log_broadcaster:
                    log_broadcaster.broadcast(record.levelname.lower(), msg)
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
    broadcast.setFormatter(
        logging.Formatter("%(levelname)-5s │ %(name)s │ %(message)s")
    )
    
    # File handler - persists logs to disk for debugging crashes
    if log_file is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(project_root, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "srt2web.log")
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB per file
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.addFilter(ConsoleFilter())  # Filter noisy security warnings from file too
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s │ %(levelname)-5s │ %(name)s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    
    # Root logger
    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(console)
    root.addHandler(broadcast)
    root.addHandler(file_handler)
    
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