"""
MediaMTX Manager - Handles starting/stopping MediaMTX server for RTMP input.

MediaMTX is a lightweight media server that can receive RTMP streams from OBS
and forward them to FFmpeg for processing in the srt2web pipeline.

Flow: OBS → RTMP (port 1935) → MediaMTX → FFmpeg (srt2web) → Pipeline
"""

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("srt2web.mtx")

from core.paths import get_project_root, get_bin_dir

PROJECT_ROOT = get_project_root()
MEDIAMTX_DIR = get_bin_dir()
MEDIAMTX_BIN = MEDIAMTX_DIR / "mediamtx.exe"
MEDIAMTX_CONFIG = MEDIAMTX_DIR / "mediamtx.yml"


class MediaMTXManager:
    """Manages MediaMTX server for RTMP input."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._process: subprocess.Popen[bytes] | None = None
        self._config = config or {}
        self._rtmp_port = self._config.get("rtmp_port", 1935)
        self._app = self._config.get("app", "live")
        self._stream_key = self._config.get("stream_key", "stream")

    def configure(self, config: dict[str, Any]) -> None:
        """Update configuration at runtime."""
        self._config = config or {}
        # Handle both "rtmp_port" and "listen_port" from config
        self._rtmp_port = self._config.get("rtmp_port") or self._config.get("listen_port", 1935)
        self._app = self._config.get("app", "live")
        self._stream_key = self._config.get("stream_key", "stream")

    @property
    def is_running(self) -> bool:
        """Check if MediaMTX is running."""
        return self._process is not None and self._process.poll() is None

    def start(self) -> bool:
        """Start MediaMTX server."""
        if self.is_running:
            logger.info("MediaMTX is already running")
            return True

        # Check if MediaMTX binary exists
        if not MEDIAMTX_BIN.exists():
            logger.error(f"MediaMTX binary not found: {MEDIAMTX_BIN}")
            return False

        try:
            # Create config file with RTMP settings
            self._create_config()

            # Start MediaMTX
            logger.info(f"Starting MediaMTX on port {self._rtmp_port}...")

            # Don't hide the window so we can see errors
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 5  # SW_SHOW
                # Don't use CREATE_NO_WINDOW - causes issues

            self._process = subprocess.Popen(
                [MEDIAMTX_BIN, MEDIAMTX_CONFIG],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )

            # Wait a bit for the server to start
            time.sleep(3)

            if self.is_running:
                logger.info("MediaMTX started successfully")
                logger.info(f"OBS should stream to: rtmp://127.0.0.1:{self._rtmp_port}/{self._app}/{self._stream_key}")
                return True
            else:
                # Give it a bit more time and capture stderr
                time.sleep(2)
                stderr = ""
                try:
                    if self._process.stderr:
                        stderr = self._process.stderr.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
                if not stderr:
                    stderr = "No stderr available"
                logger.error(f"MediaMTX failed to start. stderr: {stderr[:500]}")
                return False

        except Exception as e:
            logger.error(f"Error starting MediaMTX: {e}")
            return False

    def stop(self) -> bool:
        """Stop MediaMTX server."""
        if not self.is_running:
            logger.info("MediaMTX is not running")
            return True

        try:
            logger.info("Stopping MediaMTX...")
            if self._process is not None:
                self._process.terminate()

                # Wait for process to exit
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()

                self._process = None
            logger.info("MediaMTX stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping MediaMTX: {e}")
            return False

    def _create_config(self) -> None:
        """Create MediaMTX configuration file."""
        # Minimal config - MediaMTX will use defaults for everything else
        config_content = f"""rtmpAddress: :{self._rtmp_port}
"""

        try:
            with open(MEDIAMTX_CONFIG, "w") as f:
                f.write(config_content)
            logger.info(f"MediaMTX config written to {MEDIAMTX_CONFIG}")
        except Exception as e:
            logger.error(f"Error writing MediaMTX config: {e}")

    def get_stream_url(self) -> str:
        """Get the RTMP URL for OBS to stream to."""
        return f"rtmp://127.0.0.1:{self._rtmp_port}/{self._app}/{self._stream_key}"

    def get_internal_url(self) -> str:
        """Get the internal URL that FFmpeg should read from."""
        # MediaMTX exposes the stream via multiple protocols
        # For FFmpeg, we can use rtmp://localhost:1935/live/stream
        return f"rtmp://127.0.0.1:{self._rtmp_port}/{self._app}/{self._stream_key}"


def get_mediamtx_manager(config: dict[str, Any] | None = None) -> MediaMTXManager:
    """Factory function to get MediaMTX manager instance."""
    return MediaMTXManager(config)
