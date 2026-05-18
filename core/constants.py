"""
Centralized constants for SRT2Web.
All hardcoded values should be defined here.
"""

# Server Configuration
SERVER_HOST: str = "0.0.0.0"
SERVER_PORT_DEFAULT: int = 9999
SERVER_CORS_ORIGINS: list[str] = [
    "http://localhost:*",
    "http://127.0.0.1:*",
    "http://localhost:9999",
    "http://127.0.0.1:9999",
]

# Input Ports
SRT_PORT_DEFAULT: int = 9000
RTMP_PORT_DEFAULT: int = 1935

# API Configuration
API_BASE_PATH: str = "/api"
API_VERSION: str = "v1"
WS_BASE_PATH: str = "/ws"

# API Endpoints
API_ENDPOINTS: dict[str, str] = {
    "status": f"{API_BASE_PATH}/status",
    "start": f"{API_BASE_PATH}/start",
    "stop": f"{API_BASE_PATH}/stop",
    "restart": f"{API_BASE_PATH}/restart",
    "config": f"{API_BASE_PATH}/config",
    "modules": f"{API_BASE_PATH}/modules",
    "modules_toggle": f"{API_BASE_PATH}/modules/{{module_name}}/toggle",
    "modules_debug": f"{API_BASE_PATH}/modules/{{module_name}}/debug",
    "input_info": f"{API_BASE_PATH}/input-info",
    "input_control": f"{API_BASE_PATH}/input/control/{{action}}",
    "output_info": f"{API_BASE_PATH}/output-info",
    "outputs": f"{API_BASE_PATH}/outputs",
    "outputs_available": f"{API_BASE_PATH}/outputs/available",
    "outputs_toggle": f"{API_BASE_PATH}/outputs/{{output_name}}/toggle",
    "health": f"{API_BASE_PATH}/health",
    "network_info": f"{API_BASE_PATH}/network/info",
    "srt_info": f"{API_BASE_PATH}/srt-info",
    "available": f"{API_BASE_PATH}/available",
}

# WebSocket Paths
WS_PATHS: dict[str, str] = {
    "logs": f"{WS_BASE_PATH}/logs",
    "status": f"{WS_BASE_PATH}/status",
}

# HLS Configuration
HLS_PATH: str = "/hls"
HLS_PLAYLIST_NAME: str = "stream.m3u8"
HLS_SEGMENT_PREFIX: str = "segment"

# Default Stream URLs
DEFAULT_STREAM_URLS: dict[str, str] = {
    "srt": "srt://localhost:{port}",
    "rtmp": "rtmp://localhost/live/stream",
}

# Directory Configuration
CONFIG_FILE: str = "config.yaml"
CONFIG_DIR: str = "config"
OUTPUT_DIR: str = "output"
LOGS_DIR: str = "logs"
MODELS_DIR: str = "models"
BIN_DIR: str = "bin"
TEMP_DIR: str = "temp"
RECORDING_DIR: str = f"{OUTPUT_DIR}/recording"
HLS_OUTPUT_DIR: str = f"{OUTPUT_DIR}/hls"
WEBRTC_OUTPUT_DIR: str = f"{OUTPUT_DIR}/webrtc"

# File Extensions
EXT_VIDEO: str = ".mp4"
EXT_AUDIO: str = ".wav"
EXT_SUBTITLE: str = ".vtt"
EXT_M3U8: str = ".m3u8"
EXT_TS: str = ".ts"

# FFmpeg Configuration
FFMPEG_URLS: dict[str, dict[str, str]] = {
    "windows": {
        "x86_64": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    },
    "darwin": {
        "x86_64": "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip",
        "arm64": "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip",
    },
}

# Pipeline Configuration
DEFAULT_CHUNK_DURATION_SEC: float = 10.0
MIN_CHUNK_DURATION_SEC: float = 1.0
MAX_CHUNK_DURATION_SEC: float = 60.0
DEFAULT_SEGMENT_DURATION: int = 10
DEFAULT_LIST_SIZE: int = 2
_MAX_CONCURRENT_CHUNKS: int = 4

# Timing Constants
_LOST_CHUNK_TIMEOUT: float = 30.0
WEBSOCKET_PING_INTERVAL: int = 30
WEBSOCKET_TIMEOUT: int = 300

# Whisper Models
ALLOWED_WHISPER_MODELS: list[str] = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
    "large-v3-turbo",
]
WHISPER_MODEL_SIZES: dict[str, int] = {
    "tiny": 75,
    "base": 148,
    "small": 488,
    "medium": 1500,
    "large-v3": 2900,
    "large-v3-turbo": 1600,
}

# Languages
ALLOWED_LANGUAGES: list[str] = [
    "auto",
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "ru",
    "zh",
    "ja",
    "ko",
    "ar",
    "hi",
    "nl",
    "pl",
    "tr",
]
LANGUAGE_NAMES: dict[str, str] = {
    "auto": "Auto-detect",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
}

# Devices
ALLOWED_DEVICES: list[str] = ["auto", "cpu", "cuda", "mps"]

# TTS Engines
ALLOWED_TTS_ENGINES: list[str] = ["edge", "piper"]

# Encoder Modes (sync con EncoderModeEnum en config_schema.py)
ALLOWED_ENCODER_MODES: list[str] = ["auto", "passthrough", "cpu", "gpu_nvenc", "gpu_amf", "gpu_qsv", "gpu_videotoolbox"]

# Quality Presets
QUALITY_PRESETS: dict[str, dict[str, int]] = {
    "low": {"crf": 28, "audio_bitrate": 96},
    "medium": {"crf": 23, "audio_bitrate": 128},
    "high": {"crf": 18, "audio_bitrate": 192},
    "ultra": {"crf": 15, "audio_bitrate": 256},
}

# Video Codecs
ALLOWED_VIDEO_CODECS: list[str] = [
    "h264",
    "h265",
    "hevc",
    "vp9",
    "av1",
    "copy",
    "nvenc",
    "qsv",
    "amf",
]

# Audio Codecs
ALLOWED_AUDIO_CODECS: list[str] = ["aac", "mp3", "opus", "flac", "copy"]

# Audio Bitrates
ALLOWED_AUDIO_BITRATES: list[str] = [
    "64k",
    "96k",
    "128k",
    "192k",
    "256k",
    "320k",
]

# Subtitle Formats
ALLOWED_SUBTITLE_FORMATS: list[str] = ["webvtt", "srt", "ass"]

# Security
RATE_LIMIT_RPM: int = 60
MAX_REQUEST_SIZE_MB: int = 100

# Logging
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
LOG_FILE_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT: int = 3

# External URLs (CDN, Fonts)
EXTERNAL_URLS: dict[str, str] = {
    "google_fonts": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap",
    "font_awesome": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css",
    "highlight_js": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css",
    "hls_js": "https://cdn.jsdelivr.net/npm/hls.js@1.5.7/dist/hls.min.js",
}
