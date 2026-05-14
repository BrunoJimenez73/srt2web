"""
Centralized path utilities for SRT2Web.
All path operations should use functions from this module.
"""
from pathlib import Path
from typing import Optional

# Cache for project root (computed once)
_PROJECT_ROOT: Optional[Path] = None


def get_project_root() -> Path:
    """
    Get the project root directory.
    Cached after first call.
    """
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = Path(__file__).parent.parent.resolve()
    return _PROJECT_ROOT


def get_config_path() -> Path:
    """Get path to config.yaml."""
    return get_project_root() / "config.yaml"


def get_output_dir() -> Path:
    """Get output directory."""
    return get_project_root() / "output"


def get_logs_dir() -> Path:
    """Get logs directory."""
    return get_project_root() / "logs"


def get_models_dir() -> Path:
    """Get models directory."""
    return get_project_root() / "models"


def get_bin_dir() -> Path:
    """Get bin directory."""
    return get_project_root() / "bin"


def get_temp_dir() -> Path:
    """Get temp directory."""
    return get_project_root() / "temp"


def get_hls_output_dir() -> Path:
    """Get HLS output directory."""
    return get_output_dir() / "hls"


def get_recording_dir() -> Path:
    """Get recording output directory."""
    return get_output_dir() / "recording"


def get_webrtc_output_dir() -> Path:
    """Get WebRTC output directory."""
    return get_output_dir() / "webrtc"


def get_piper_models_dir() -> Path:
    """Get Piper TTS models directory."""
    return get_models_dir() / "piper"


def get_whisper_models_dir() -> Path:
    """Get Whisper models directory."""
    return get_models_dir() / "whisper"


def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, create if needed.
    Returns the same path for chaining.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_project_dirs() -> None:
    """Create all required project directories."""
    dirs = [
        get_output_dir(),
        get_logs_dir(),
        get_models_dir(),
        get_bin_dir(),
        get_temp_dir(),
        get_hls_output_dir(),
        get_recording_dir(),
        get_webrtc_output_dir(),
        get_piper_models_dir(),
        get_whisper_models_dir(),
    ]
    for d in dirs:
        ensure_directory(d)


def resolve_path(path: str | Path, relative_to: Optional[Path] = None) -> Path:
    """
    Resolve a path that may be relative or absolute.
    If relative, resolves relative to relative_to (default: project root).
    """
    p = Path(path)
    if p.is_absolute():
        return p
    base = relative_to or get_project_root()
    return (base / p).resolve()


def is_within_project(path: Path) -> bool:
    """Check if a path is within the project directory."""
    try:
        path.resolve().relative_to(get_project_root().resolve())
        return True
    except ValueError:
        return False


def get_static_dir() -> Path:
    """Get server static files directory."""
    return get_project_root() / "server" / "static"


def get_logs_file(name: str = "srt2web.log") -> Path:
    """Get path to a log file in logs directory."""
    return get_logs_dir() / name


def get_server_log_file() -> Path:
    """Get path to the main server log file."""
    return get_logs_file("srt2web.log")


def get_access_log_file() -> Path:
    """Get path to access log file."""
    return get_logs_file("access.log")


def get_error_log_file() -> Path:
    """Get path to error log file."""
    return get_logs_file("error.log")


def get_cache_dir() -> Path:
    """
    Get the user-level cache directory for models and other cached data.

    macOS: ~/Library/Caches/srt2web/
    Windows: %LOCALAPPDATA%/srt2web/cache/
    Linux: ~/.cache/srt2web/

    Falls back to project_root/.cache/ if platformdirs not available.
    """
    try:
        from platformdirs import user_cache_dir

        cache = Path(user_cache_dir("srt2web", ensure_exists=True))
        return cache
    except ImportError:
        cache = get_project_root() / ".cache"
        cache.mkdir(parents=True, exist_ok=True)
        return cache


def get_user_config_dir() -> Path:
    """
    Get the user-level configuration directory.

    macOS: ~/Library/Application Support/srt2web/
    Windows: %APPDATA%/srt2web/
    Linux: ~/.config/srt2web/

    Falls back to project_root/config/ if platformdirs not available.
    """
    try:
        from platformdirs import user_config_dir

        cfg = Path(user_config_dir("srt2web", ensure_exists=True))
        return cfg
    except ImportError:
        cfg = get_project_root() / "config"
        cfg.mkdir(parents=True, exist_ok=True)
        return cfg


def get_user_log_dir() -> Path:
    """
    Get the user-level log directory.

    macOS: ~/Library/Logs/srt2web/
    Windows: %LOCALAPPDATA%/srt2web/log/
    Linux: ~/.cache/srt2web/log/

    Falls back to project_root/logs/ if platformdirs not available.
    """
    try:
        from platformdirs import user_log_dir

        log = Path(user_log_dir("srt2web", ensure_exists=True))
        return log
    except ImportError:
        log = get_project_root() / "logs"
        log.mkdir(parents=True, exist_ok=True)
        return log
