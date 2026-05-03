"""
SRT2Web - Modular SRT Stream Processor

Entry point: starts the FastAPI server, initializes the pipeline,
and opens the browser to the dashboard.
"""

import logging
import signal
import sys
from types import FrameType

from core import SERVER_HOST, SERVER_PORT_DEFAULT, get_config_path, get_project_root
from core.app_context import create_app_context
from core.config_manager import ConfigManager
from core.cuda_paths import setup_cuda_environment
from server.app import create_app
from server.lifespan import graceful_shutdown, open_browser_on_startup, run_server

# Setup CUDA paths - must be called before any GPU-related imports
setup_cuda_environment()

PROJECT_ROOT = get_project_root()


def main() -> None:
    """Main entry point — bootstrap only."""
    logger = logging.getLogger("srt2web.main")

    # Load configuration
    config_manager = ConfigManager(get_config_path())
    config = config_manager._config

    host = config.get("server", {}).get("host", SERVER_HOST)
    port = config.get("server", {}).get("port", SERVER_PORT_DEFAULT)
    ssl_config = config.get("server", {}).get("ssl", {})

    # Build application context (pipeline + modules + I/O)
    output_dir = str(PROJECT_ROOT / "output")
    app_context = create_app_context(config_manager, output_dir)

    # Open browser after startup
    ssl_enabled = ssl_config.get("enabled", False)
    open_browser_on_startup(host, port, ssl_enabled)

    # Register signal handlers
    def handle_exit(signum: int, frame: FrameType | None) -> None:
        logger.info("Shutdown signal received. Cleaning up...")
        graceful_shutdown(app_context)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Log connection info
    input_source = app_context.get("input_source")
    if input_source:
        input_info = input_source.get_connection_info()
        input_url = input_info.get("url", f"port {input_info.get('port', 'N/A')}")
        logger.info(f"Input: {input_info.get('type', 'unknown').upper()} ({input_url})")
        logger.info(f"Stream: http://{host}:{port}/hls/stream.m3u8")
    print()

    # Create and run server
    app = create_app(app_context)
    run_server(host, port, app, ssl_config)


if __name__ == "__main__":
    main()
