"""
Server Lifecycle - Manages FastAPI application lifecycle.

Handles startup initialization, graceful shutdown, cleanup,
and server execution.
"""

import logging
import os
import threading
import webbrowser
from typing import Any

import uvicorn

logger = logging.getLogger("srt2web.lifecycle")


def _cleanup_orphan_processes() -> None:
    """Cleanup any orphan FFmpeg processes on unexpected shutdown."""
    from core.ffmpeg_utils import cleanup_ffmpeg_processes
    from core.security import cleanup_temporary_files

    logger.info("Cleaning up orphan processes and temporary files...")
    try:
        cleanup_ffmpeg_processes()
        output_dir = "./output"
        cleanup_temporary_files(output_dir)
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")


def graceful_shutdown(app_context: dict) -> None:
    """Graceful shutdown handler."""
    try:
        pipeline = app_context.get("pipeline")
        if pipeline and pipeline.is_running:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(pipeline.stop())
            loop.close()
        logger.info("Pipeline shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    _cleanup_orphan_processes()


def open_browser_on_startup(host: str, port: int, ssl_enabled: bool = False) -> None:
    """Open browser in a daemon thread after short delay."""

    def _open():
        import time

        time.sleep(1.5)
        url = f"http{'s' if ssl_enabled else ''}://{host}:{port}"
        logger.info(f"Opening browser: {url}")
        webbrowser.open(url)

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def run_server(host: str, port: int, app: Any, ssl_config: dict | None = None) -> None:
    """
    Configure and run the uvicorn server.

    Args:
        host: Server host address
        port: Server port
        app: FastAPI application instance
        ssl_config: Optional SSL configuration dict
    """
    ssl_enabled = ssl_config.get("enabled", False) if ssl_config else False

    if ssl_enabled:
        cert_file = ssl_config.get("cert_file", "certs/cert.pem")
        key_file = ssl_config.get("key_file", "certs/key.pem")

        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            logger.warning(f"SSL cert/key not found: {cert_file}, {key_file}")
            logger.warning("Run: python scripts/generate_ssl_certs.py")
            logger.warning("Falling back to HTTP")
            ssl_enabled = False
        else:
            logger.info(f"SSL enabled: {cert_file}")

    protocol = "https" if ssl_enabled else "http"
    logger.info(f"Dashboard: {protocol}://{host}:{port}")

    uvicorn_kwargs: dict[str, Any] = {
        "host": host,
        "port": port,
        "log_level": "info",
        "access_log": True,
    }

    if ssl_enabled and ssl_config:
        uvicorn_kwargs["ssl_certfile"] = ssl_config.get("cert_file")
        uvicorn_kwargs["ssl_keyfile"] = ssl_config.get("key_file")

    config = uvicorn.Config(app, **uvicorn_kwargs)
    server = uvicorn.Server(config)
    server.run()
