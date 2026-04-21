"""Path management utilities for SRT2Web Desktop."""
import os
import sys
import platform
from pathlib import Path

def is_frozen():
    """Check if running as PyInstaller bundle."""
    return getattr(sys, 'frozen', False)

def get_bundle_dir():
    """Get the bundle directory (where the exe is located)."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent

def get_app_dir():
    """Get the application data directory (platform-specific)."""
    system = platform.system()
    
    if system == 'Windows':
        base = os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')
    elif system == 'Darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
    
    return Path(base) / 'SRT2Web'

def get_data_dir():
    """Get the data directory for models and configuration."""
    return get_app_dir() / 'data'

def get_cache_dir():
    """Get the cache directory for downloaded models."""
    system = platform.system()
    
    if system == 'Windows':
        base = os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')
    elif system == 'Darwin':
        base = Path.home() / 'Library' / 'Caches'
    else:
        base = os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')
    
    return Path(base) / 'SRT2Web' / 'cache'

def get_log_dir():
    """Get the log directory."""
    return get_app_dir() / 'logs'

def ensure_dirs():
    """Ensure all required directories exist."""
    for dir_path in [get_app_dir(), get_data_dir(), get_cache_dir(), get_log_dir()]:
        dir_path.mkdir(parents=True, exist_ok=True)