"""
SRT2Web Constants

Centralized constants for the application.
"""

# Server defaults
DEFAULT_SERVER_PORT = 9999
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_CORS_ORIGINS = ["http://localhost:*", "http://127.0.0.1:*"]
DEFAULT_AUTH_TOKEN = ""
DEFAULT_RATE_LIMIT_RPM = 60
DEFAULT_MAX_REQUEST_SIZE_MB = 1

# SRT input defaults
DEFAULT_SRT_PORT = 9000
DEFAULT_SRT_MODE = "listener"
DEFAULT_SRT_LATENCY_MS = 1000
DEFAULT_SRT_CALLER_ADDRESS = ""

# File input defaults
DEFAULT_FILE_PATH = ""
DEFAULT_FILE_LOOP = False
DEFAULT_FILE_SPEED = 1.0

# Web output defaults
DEFAULT_WEB_SEGMENT_DURATION = 15
DEFAULT_WEB_LIST_SIZE = 6
DEFAULT_WEB_AUDIO_OFFSET_MS = 0

# Pipeline defaults
DEFAULT_CHUNK_DURATION_SEC = 15

# HLS defaults
DEFAULT_HLS_SEGMENT_DURATION = 4
DEFAULT_HLS_LIST_SIZE = 6

# Audio defaults
DEFAULT_AUDIO_SAMPLERATE = 44100
DEFAULT_AUDIO_CHANNELS = 2

# Video defaults
DEFAULT_VIDEO_QUALITY = "medium"
DEFAULT_VIDEO_CRF = 26
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_BITRATE = "192k"
DEFAULT_AUDIO_SAMPLERATE_STR = "48000"

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

# TTS engines
ALLOWED_TTS_ENGINES = frozenset([
    "edge",
    "edge-tts",
    "piper",
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
    "gpu_nvenc",
    "gpu_amf",
    "gpu_qsv",
    "gpu_vaapi",
    "gpu_videotoolbox",
])

# GPU presets
ALLOWED_GPU_PRESETS = frozenset([
    "p1", "p2", "p3", "p4", "p5", "p6", "p7",
])

# FFmpeg presets
ALLOWED_FFMPEG_PRESETS = frozenset([
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
])

# Languages
ALLOWED_LANGUAGES = frozenset([
    "auto", "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", "ar", "nl", "hi", "tr", "pl", "cs", "sv", "da", "fi", "nb", "hu"
])

# Devices
ALLOWED_DEVICES = frozenset(["auto", "cpu", "cuda"])

# SRT modes
ALLOWED_SRT_MODES = frozenset(["listener", "caller"])

# TTS voices
ALLOWED_TTS_VOICES = frozenset([
    # Edge-TTS voices
    "es-ES-AlvaroNeural",
    "es-ES-ElviraNeural",
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "fr-FR-DeniseNeural",
    "de-DE-ConradNeural",
    # Piper voices
    "es_ES-carlfm-x_low",
    "es_ES-davefx-medium",
    "es_ES-sharvard-medium",
    "es_ES-mls_10246-low",
    "es_MX-claude-high",
    "es_AR-daniela-high",
    "en_US-lessac-medium",
    "en_US-lessac-low",
    "en_US-amy-low",
    "en_US-ryan-low",
    "fr_FR-gilles-low",
    "fr_FR-siwis-medium",
    "de_DE-eva_k-x_low",
    "de_DE-thorsten-medium",
    "it_IT-paola-medium",
    "it_IT-riccardo-x_low",
    "pt_BR-cadu-medium",
    "pt_PT-tugao-medium",
])

# Valid input/output types
VALID_INPUT_TYPES = frozenset(["srt", "file", "rtmp", "audio"])
VALID_OUTPUT_TYPES = frozenset(["web", "hls", "srt", "rtmp", "audio"])

# Subtitle formats
ALLOWED_SUBTITLE_FORMATS = frozenset([
    "srt", "vtt", "ass"
])


# HLS helper functions
def generate_master_playlist(
    subs_exist: bool = False,
    subtitle_language: str = "es",
    subtitle_language_name: str = "Spanish",
    bandwidth: int = 2000000,
    codec_video: str = "avc1.64001f",
    codec_audio: str = "mp4a.40.2",
    stream_filename: str = "stream.m3u8"
) -> list:
    """
    Generate master playlist content for HLS.
    
    Args:
        subs_exist: Whether subtitle VTT file exists
        subtitle_language: ISO language code for subtitles
        subtitle_language_name: Display name for subtitle track
        bandwidth: Stream bandwidth in bits/sec
        codec_video: Video codec string
        codec_audio: Audio codec string
        stream_filename: Name of the stream playlist file
    
    Returns:
        List of playlist lines
    """
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:4",
    ]
    
    codec_str = f'"{codec_video},{codec_audio}"'
    
    if subs_exist:
        lines.append(
            f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{subtitle_language_name}",'
            f'DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="{subtitle_language}",URI="subs.vtt"'
        )
        lines.append(
            f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},CODECS={codec_str},SUBTITLES="subs"'
        )
    else:
        lines.append(
            f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},CODECS={codec_str}'
        )
    
    lines.append(stream_filename)
    return lines
