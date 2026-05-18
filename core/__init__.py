"""
SRT2Web Core - Núcleo del sistema de procesamiento de streams SRT.

Este módulo contiene los componentes principales del pipeline:
- Configuración y gestión
- Pipeline y módulos
- Tipos y excepciones compartidas
- Seguridad y utilidades
"""

# Tipos y excepciones (nuevos módulos de refactorización)
# Configuración y gestión
# Nuevas estrategias de pipeline (refactoring)
from core.config_manager import ConfigManager

# Constantes centralizadas
from core.constants import (
    ALLOWED_DEVICES,
    ALLOWED_ENCODER_MODES,
    ALLOWED_LANGUAGES,
    ALLOWED_TTS_ENGINES,
    ALLOWED_WHISPER_MODELS,
    API_BASE_PATH,
    API_ENDPOINTS,
    BIN_DIR,
    CONFIG_FILE,
    DEFAULT_STREAM_URLS,
    EXTERNAL_URLS,
    FFMPEG_URLS,
    HLS_PATH,
    LOGS_DIR,
    MODELS_DIR,
    OUTPUT_DIR,
    RTMP_PORT_DEFAULT,
    SERVER_HOST,
    SERVER_PORT_DEFAULT,
    SRT_PORT_DEFAULT,
    WS_BASE_PATH,
    WS_PATHS,
)

# Nuevos módulos de configuración (refactoring)
from core.cuda_paths import (
    get_cuda_paths,
    has_cuda_support,
    setup_cuda_environment,
)
from core.exceptions import (
    AudioMixerError,
    ChunkProcessingError,
    ConfigurationError,
    ConfigurationValidationError,
    CUDAError,
    FFmpegError,
    HLSMuxerError,
    InfrastructureError,
    InputSourceError,
    ModuleError,
    ModuleProcessingError,
    OutputSinkError,
    PipelineError,
    PipelineStateError,
    ResourceExhaustedError,
    RTMPConnectionError,
    SRT2WebError,
    SRTConnectionError,
    TranscriberError,
    TranslatorError,
    TTSError,
    WebRTCError,
)

# Hardware auto-detection (Sugerencia 2)
from core.logging_setup import (
    get_logger,
    setup_logging,
)
from core.module_base import BaseModule, PipelineData

# Interfaz de módulos (nueva arquitectura)
# Paths utilities
from core.paths import (
    ensure_directory,
    ensure_project_dirs,
    get_bin_dir,
    get_config_path,
    get_hls_output_dir,
    get_logs_dir,
    get_models_dir,
    get_output_dir,
    get_project_root,
    get_recording_dir,
    get_server_log_file,
    get_static_dir,
    get_temp_dir,
    is_within_project,
    resolve_path,
)
from core.schemas import (
    ModuleState,
    ModuleStatus,
    PipelineState,
    SystemMetrics,
)

# Seguridad y utilidades
from core.security import (
    sanitize_filename,
    sanitize_path,
    validate_latency,
    validate_port,
)
from core.types import (
    AudioConfig,
    ChunkInfo,
    DeviceType,
    EncoderMode,
    HLSConfig,
    InputType,
    LogLevel,
    LogMessage,
    OutputType,
    PipelineStatus,
    VideoConfig,
)

# Pipeline y módulos (legacy - para compatibilidad)
from core.unified_pipeline import UnifiedPipeline as Pipeline

__all__ = [
    # Tipos
    "PipelineState",
    "ModuleState",
    "LogLevel",
    "InputType",
    "OutputType",
    "DeviceType",
    "EncoderMode",
    "PipelineData",
    "ModuleStatus",
    "PipelineStatus",
    "LogMessage",
    "SystemMetrics",
    "ChunkInfo",
    "AudioConfig",
    "VideoConfig",
    "HLSConfig",
    # Excepciones
    "SRT2WebError",
    "ConfigurationError",
    "ConfigurationValidationError",
    "PipelineError",
    "PipelineStateError",
    "ChunkProcessingError",
    "ModuleError",
    "ModuleProcessingError",
    "InputSourceError",
    "SRTConnectionError",
    "RTMPConnectionError",
    "OutputSinkError",
    "HLSMuxerError",
    "WebRTCError",
    "TranscriberError",
    "TranslatorError",
    "TTSError",
    "AudioMixerError",
    "FFmpegError",
    "CUDAError",
    "ResourceExhaustedError",
    "InfrastructureError",
    # Componentes
    "ConfigManager",
    "Pipeline",
    "BaseModule",
    # Nuevos módulos (refactoring)
    "get_cuda_paths",
    "setup_cuda_environment",
    "has_cuda_support",
    "setup_logging",
    "get_logger",
    # Utilidades
    "sanitize_path",
    "sanitize_filename",
    "validate_port",
    "validate_latency",
    # Constantes
    "SERVER_HOST",
    "SERVER_PORT_DEFAULT",
    "SRT_PORT_DEFAULT",
    "RTMP_PORT_DEFAULT",
    "API_ENDPOINTS",
    "WS_PATHS",
    "API_BASE_PATH",
    "WS_BASE_PATH",
    "HLS_PATH",
    "DEFAULT_STREAM_URLS",
    "CONFIG_FILE",
    "OUTPUT_DIR",
    "LOGS_DIR",
    "MODELS_DIR",
    "BIN_DIR",
    "FFMPEG_URLS",
    "ALLOWED_WHISPER_MODELS",
    "ALLOWED_LANGUAGES",
    "ALLOWED_DEVICES",
    "ALLOWED_TTS_ENGINES",
    "ALLOWED_ENCODER_MODES",
    "EXTERNAL_URLS",
    # Paths
    "get_project_root",
    "get_config_path",
    "get_output_dir",
    "get_logs_dir",
    "get_models_dir",
    "get_bin_dir",
    "get_temp_dir",
    "get_hls_output_dir",
    "get_recording_dir",
    "ensure_directory",
    "ensure_project_dirs",
    "resolve_path",
    "is_within_project",
    "get_static_dir",
    "get_server_log_file",
]
