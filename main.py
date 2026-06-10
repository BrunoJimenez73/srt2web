"""
SRT2Web - Modular SRT Stream Processor

Entry point: starts the FastAPI server, initializes the pipeline,
and opens the browser to the dashboard.
"""

import logging
import os
import signal
import sys
from types import FrameType

# F111: Wrap the project imports so that a numpy DLL load failure (common on
# Windows due to SmartScreen / AppLocker / EDR policies) shows an actionable
# error instead of a raw traceback. The chain is:
#     main → core → core.module_base → import numpy → ImportError
# We catch ImportError here, detect the Windows-specific pattern, and print
# a clear message pointing to docs/troubleshooting-windows.md.
try:
    from dotenv import load_dotenv  # F112: load .env (SRT2WEB_JWT_SECRET etc.) before other imports

    load_dotenv()  # noqa: E402 - intentional: must run before core imports below
    from core import SERVER_HOST, SERVER_PORT_DEFAULT, get_config_path, get_project_root
    from core.app_context import create_app_context
    from core.config_manager import ConfigManager, validate_secrets
    from core.cuda_paths import setup_cuda_environment
    from core.logging_setup import install_crash_handler, setup_logging
    from server.app import create_app
    from server.lifespan import graceful_shutdown, open_browser_on_startup, run_server
    from server.ws_routes import log_broadcaster
except ImportError as _f111_import_error:
    _err = str(_f111_import_error)
    _is_numpy_dll = (
        "_multiarray_umath" in _err
        or "DLL load failed" in _err
        or "Control de aplicaciones" in _err
    )
    sys.stderr.write("=" * 70 + "\n")
    sys.stderr.write("SRT2Web failed to start — required dependency is broken.\n\n")
    sys.stderr.write(f"Original error: {_err}\n\n")
    if _is_numpy_dll:
        sys.stderr.write(
            "This looks like the Windows-specific numpy C-extension failure\n"
            "documented in docs/troubleshooting-windows.md, section:\n"
            "  'ImportError: DLL load failed while importing _multiarray_umath'\n\n"
            "Quick fix:\n"
            "  1. venv\\Scripts\\python.exe -m pip uninstall numpy -y\n"
            "  2. venv\\Scripts\\python.exe -m pip install numpy --only-binary=:all:\n\n"
            "If that doesn't work, see docs/troubleshooting-windows.md for the\n"
            "6-step escalation (SmartScreen → AppLocker → EDR → admin).\n"
        )
    else:
        sys.stderr.write(
            "A required module could not be imported. Common causes:\n"
            "  - Virtual environment not activated (run Install.bat / install_Mac.sh)\n"
            "  - Dependencies not installed\n"
            "  - Python version mismatch (requires 3.12+)\n\n"
            "Try:\n"
            "  venv\\Scripts\\python.exe -m pip install -r config/requirements.txt\n"
        )
    sys.stderr.write("=" * 70 + "\n")
    sys.exit(1)

# Setup CUDA paths - must be called before any GPU-related imports
setup_cuda_environment()

# F114: Install crash capture EARLY (after core is importable, before main()
# runs). This captures any unhandled exception in main() to logs/crash.log
# while preserving the original sys.excepthook so the user still sees the
# traceback on stderr.
install_crash_handler()

PROJECT_ROOT = get_project_root()


def main() -> None:
    """Main entry point — bootstrap only."""
    logger = logging.getLogger("srt2web.main")

    # Setup logging with WebSocket broadcast
    setup_logging(log_broadcaster=log_broadcaster)

    # F112: Validate secrets (SRT2WEB_JWT_SECRET etc.) at startup.
    # In strict mode, an empty/insecure secret blocks startup. Override with
    # SRT2WEB_ALLOW_INSECURE_DEFAULTS=1 for local dev runs.
    allow_insecure = os.environ.get("SRT2WEB_ALLOW_INSECURE_DEFAULTS", "").lower() in ("1", "true", "yes")
    ok, msg = validate_secrets(strict=not allow_insecure)
    if not ok:
        logger.error("Secret validation failed: %s", msg)
        logger.error(
            "To skip this check (dev only), set SRT2WEB_ALLOW_INSECURE_DEFAULTS=1 "
            "in your environment."
        )
        sys.stderr.write("\n" + "=" * 70 + "\n")
        sys.stderr.write("SRT2Web refused to start — insecure secret configuration.\n")
        sys.stderr.write("=" * 70 + "\n\n")
        sys.stderr.write(f"Reason: {msg}\n\n")
        sys.stderr.write("Quick fix:\n")
        sys.stderr.write('  python -c "import secrets; print(secrets.token_urlsafe(32))"\n')
        sys.stderr.write("  # Copy the printed value to .env as SRT2WEB_JWT_SECRET=<value>\n")
        sys.stderr.write("  # Or run Install.bat / install_Mac.sh to auto-generate.\n")
        sys.stderr.write("\n")
        sys.stderr.write("Dev bypass (NEVER use in production):\n")
        sys.stderr.write("  set SRT2WEB_ALLOW_INSECURE_DEFAULTS=1    (Windows)\n")
        sys.stderr.write("  export SRT2WEB_ALLOW_INSECURE_DEFAULTS=1 (macOS/Linux)\n")
        sys.stderr.write("=" * 70 + "\n")
        sys.exit(1)

    # Load configuration
    config_manager = ConfigManager(get_config_path())
    host = config_manager.get("server.host", SERVER_HOST)
    port = config_manager.get("server.port", SERVER_PORT_DEFAULT)
    ssl_config = config_manager.get("server.ssl", {})

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
    # F114: Final safety net. The sys.excepthook installed above already
    # captures unhandled exceptions to logs/crash.log. This try/except
    # ensures the user sees a clear "FATAL: ..." line on stderr and that
    # the process exits with a non-zero code (useful for service managers
    # and CI).
    try:
        main()
    except SystemExit:
        raise  # sys.exit() inside main() — preserve the exit code
    except BaseException as _fatal:
        # The crash hook already wrote to logs/crash.log. Just print a
        # one-liner and exit.
        sys.stderr.write(f"\nFATAL: {type(_fatal).__name__}: {_fatal}\n")
        sys.stderr.write("See logs/crash.log for the full traceback.\n")
        sys.exit(1)
