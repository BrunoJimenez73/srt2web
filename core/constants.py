"""
SRT2Web Constants

Centralized constants for the application.
These can be imported from anywhere without causing circular imports.
"""

# Server defaults
DEFAULT_SERVER_PORT = 9999
DEFAULT_SERVER_HOST = "127.0.0.1"

# SRT input defaults
DEFAULT_SRT_PORT = 9000
DEFAULT_SRT_LATENCY_MS = 1000

# Pipeline defaults
DEFAULT_CHUNK_DURATION_SEC = 15

# HLS defaults
DEFAULT_HLS_SEGMENT_DURATION = 4
DEFAULT_HLS_LIST_SIZE = 6

# Audio defaults
DEFAULT_AUDIO_SAMPLERATE = 44100
DEFAULT_AUDIO_CHANNELS = 2

# Whisper models
ALLOWED_WHISPER_MODELS = frozenset([
    "tiny",
    "base",
    "small",
    "medium",
    "large",
    "large-v2",
    "large-v3",
])

# Valid module names
VALID_PIPELINE_MODULES = frozenset([
    "audio_extractor",
    "transcriber",
    "translator",
    "subtitle_generator",
    "tts_engine",
    "audio_mixer",
    "video_muxer",
])

# Encoder modes
VALID_ENCODER_MODES = frozenset([
    "auto",
    "cpu",
    "gpu",
])

# GPU presets
ALLOWED_GPU_PRESETS = frozenset([
    "p1", "p2", "p3", "p4", "p5", "p6", "p7",
])
