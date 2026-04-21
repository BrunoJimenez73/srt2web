#!/usr/bin/env python3
"""
SRT2Web Desktop Launcher

Punto de entrada para la aplicación de escritorio.
Funciona tanto en desarrollo como en producción (Electron bundle).
"""

import sys
import os
import platform
import subprocess
import logging
import time
import signal
from pathlib import Path
from typing import Optional

# ============================================================================
# DETECCIÓN DE MODO (DESARROLLO vs PRODUCCIÓN)
# ============================================================================

def is_frozen() -> bool:
    """Check if running as PyInstaller/Electron bundle."""
    return getattr(sys, 'frozen', False)

def get_bundle_dir() -> Path:
    """Get the project root directory (where main.py is located)."""
    # Siempre priorizar env var de Electron
    if 'SRT2WEB_PROJECT_ROOT' in os.environ:
        project_root = Path(os.environ['SRT2WEB_PROJECT_ROOT'])
        logger.info(f"Using SRT2WEB_PROJECT_ROOT: {project_root}")
        return project_root
    
    # PyInstaller frozen
    if is_frozen():
        return Path(sys._MEIPASS)
    
    # En desarrollo: launcher está en desktop/src/python/, buscar main.py
    # desktop/src/python/ -> desktop/src/ -> desktop/
    return Path(__file__).parent.parent

def get_app_dir() -> Path:
    """Get the application data directory (platform-specific)."""
    system = platform.system()
    
    if system == 'Windows':
        base = os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')
    elif system == 'Darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
    
    return Path(base) / 'SRT2Web'

def get_data_dir() -> Path:
    return get_app_dir() / 'data'

def get_cache_dir() -> Path:
    system = platform.system()
    if system == 'Windows':
        base = os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')
    elif system == 'Darwin':
        base = Path.home() / 'Library' / 'Caches'
    else:
        base = os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')
    return Path(base) / 'SRT2Web' / 'cache'

def get_log_dir() -> Path:
    return get_app_dir() / 'logs'

def ensure_dirs():
    for dir_path in [get_app_dir(), get_data_dir(), get_cache_dir(), get_log_dir()]:
        dir_path.mkdir(parents=True, exist_ok=True)

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configure logging to file and console."""
    ensure_dirs()
    log_file = get_log_dir() / 'srt2web.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('srt2web.launcher')

logger = setup_logging()

# ============================================================================
# GLOBAL STATE
# ============================================================================

_server_process: Optional[subprocess.Popen] = None
_ffmpeg_path: Optional[str] = None
_should_exit = False

# ============================================================================
# FFmpeg
# ============================================================================

def find_ffmpeg_system() -> Optional[str]:
    """Find FFmpeg in system PATH."""
    import shutil
    
    paths_to_check = [
        'ffmpeg',
        'ffmpeg.exe',
        Path(os.environ.get('ProgramFiles', 'C:\\Program Files')) / 'FFmpeg' / 'bin' / 'ffmpeg.exe',
        Path(os.environ.get('LOCALAPPDATA', '')) / 'ffmpeg' / 'ffmpeg.exe',
    ]
    
    for path in paths_to_check:
        if Path(path).exists():
            return str(path)
    
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg and Path(ffmpeg).exists():
        return ffmpeg
    
    return None

def check_ffmpeg() -> bool:
    """Check if FFmpeg is available."""
    global _ffmpeg_path
    
    logger.info("Checking FFmpeg availability...")
    
    # Primero buscar en el bundle (producción)
    bundle_dir = get_bundle_dir()
    bundled_ffmpeg = bundle_dir / 'resources' / 'ffmpeg' / 'ffmpeg.exe'
    
    if bundled_ffmpeg.exists():
        _ffmpeg_path = str(bundled_ffmpeg)
        logger.info(f"Using bundled FFmpeg: {_ffmpeg_path}")
        return True
    
    # Buscar en sistema
    system_ffmpeg = find_ffmpeg_system()
    if system_ffmpeg:
        _ffmpeg_path = system_ffmpeg
        logger.info(f"Using system FFmpeg: {_ffmpeg_path}")
        return True
    
    logger.warning("FFmpeg not found. Please install FFmpeg.")
    return False

def check_python_version() -> bool:
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        logger.error(f"Python 3.10+ required, found {version.major}.{version.minor}")
        return False
    return True

# ============================================================================
# COMMUNICATION WITH ELECTRON
# ============================================================================

def send_ready(port: int):
    """Send ready signal to Electron via stdout."""
    print(f"READY:{port}", flush=True)
    logger.info(f"Server ready on port {port}")

def send_error(message: str):
    """Send error signal to Electron via stdout."""
    print(f"ERROR:{message}", flush=True)
    logger.error(message)

def send_status(message: str):
    """Send status update to Electron via stdout."""
    print(f"STATUS:{message}", flush=True)
    logger.info(message)

# ============================================================================
# SERVER STARTUP
# ============================================================================

def find_main_py() -> Optional[Path]:
    """Find main.py by searching from bundle directory upward."""
    bundle_dir = get_bundle_dir()
    logger.info(f"Searching for main.py from: {bundle_dir}")
    
    # Buscar en el directorio actual y padres (máx 5 niveles)
    for i in range(6):
        candidate = bundle_dir / 'main.py'
        if candidate.exists():
            logger.info(f"Found main.py at depth {i}: {candidate}")
            return candidate
        bundle_dir = bundle_dir.parent
    
    # No encontrado - mostrar qué hay en recursos
    logger.error(f"main.py not found after searching 5 levels up")
    if is_frozen() and hasattr(sys, '_MEIPASS'):
        logger.error(f"_MEIPASS: {Path(sys._MEIPASS)}")
        # Mostrar contenido
        meipass = Path(sys._MEIPASS)
        if meipass.exists():
            for item in list(meipass.iterdir())[:10]:
                logger.info(f"  _MEIPASS content: {item.name}")
    
    return None

def start_server(port: int = 9999) -> Optional[subprocess.Popen]:
    """Start the SRT2Web server."""
    global _server_process, _should_exit
    
    logger.info(f"Starting server on port {port}...")
    
    # Encontrar main.py
    main_py = find_main_py()
    
    if not main_py:
        # En producción, si no encuentra main.py, crear uno mínimo embebido
        logger.error("Could not find main.py")
        send_error("main.py not found in bundle")
        return None
    
    logger.info(f"Using main.py: {main_py}")
    
    # Environment
    env = os.environ.copy()
    
    # Añadir FFmpeg al PATH si está bundled
    if _ffmpeg_path:
        ffmpeg_dir = Path(_ffmpeg_path).parent
        env['PATH'] = f"{ffmpeg_dir}{os.pathsep}{env.get('PATH', '')}"
    
    # Puerto - verificar si está libre
    test_port = port
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(('127.0.0.1', test_port))
        sock.close()
        
        if result == 0:
            # Puerto ocupado
            logger.warning(f"Port {test_port} is already in use, trying {test_port + 1}")
            test_port = test_port + 1
    except Exception:
        pass
    
    port = test_port
    
    try:
        # Iniciar proceso - en producción el cwd debe ser el bundle
        cwd = str(get_bundle_dir()) if is_frozen() else str(main_py.parent)
        
        _server_process = subprocess.Popen(
            [sys.executable, str(main_py)],
            env=env,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Enviar puerto inmediatamente
        send_ready(port)
        
        logger.info(f"Server started on port {port}")
        return _server_process
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        send_error(f"Failed to start server: {e}")
        return None

def stop_server():
    """Stop the SRT2Web server."""
    global _server_process, _should_exit
    
    logger.info("Stopping server...")
    _should_exit = True
    
    if _server_process:
        try:
            _server_process.terminate()
            _server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        except Exception as e:
            logger.warning(f"Error stopping server: {e}")
        
        _server_process = None

def handle_signal(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    stop_server()
    sys.exit(0)

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    global _should_exit
    
    print("=" * 40, flush=True)
    print("  SRT2Web Desktop v0.6.6", flush=True)
    print("=" * 40, flush=True)
    print(flush=True)
    
    logger.info(f"SRT2Web Desktop starting...")
    logger.info(f"Mode: {'PRODUCTION' if is_frozen() else 'DEVELOPMENT'}")
    logger.info(f"Bundle dir: {get_bundle_dir()}")
    
    # Ensure directories exist
    ensure_dirs()
    
    # Check Python version
    if not check_python_version():
        send_error("Python 3.10+ required")
        sys.exit(1)
    
    # Check FFmpeg
    if not check_ffmpeg():
        send_error("FFmpeg not found. Please install FFmpeg.")
        sys.exit(1)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    send_status("Starting server...")
    
    # Start server
    server = start_server()
    
    if not server:
        send_error("Failed to start server")
        sys.exit(1)
    
    # Keep running until signaled to exit
    logger.info("Server running. Press Ctrl+C to stop.")
    
    try:
        while not _should_exit:
            if server.poll() is not None:
                logger.warning("Server process exited unexpectedly")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_server()
    
    logger.info("SRT2Web Desktop stopped")

if __name__ == '__main__':
    main()