"""
SRT2Web Core - Núcleo del sistema de procesamiento de streams SRT.

Este módulo contiene los componentes principales del pipeline:
- Configuración y gestión
- Pipeline y módulos
- Tipos y excepciones compartidas
- Seguridad y utilidades
"""

# Tipos y excepciones (nuevos módulos de refactorización)
from core.exceptions import (
    SRT2WebError,
    ConfigurationError,
    ConfigurationValidationError,
    PipelineError,
    PipelineStateError,
    ChunkProcessingError,
    ModuleError,
    ModuleProcessingError,
    InputSourceError,
    SRTConnectionError,
    RTMPConnectionError,
    OutputSinkError,
    HLSMuxerError,
    WebRTCError,
    TranscriberError,
    TranslatorError,
    TTSError,
    AudioMixerError,
    FFmpegError,
    CUDAError,
    ResourceExhaustedError,
    InfrastructureError,
)
from core.types import (
    PipelineState,
    ModuleState,
    LogLevel,
    InputType,
    OutputType,
    DeviceType,
    EncoderMode,
    PipelineData,
    ModuleStatus,
    PipelineStatus,
    LogMessage,
    SystemMetrics,
    ChunkInfo,
    AudioConfig,
    VideoConfig,
    HLSConfig,
)

# Interfaz de módulos (nueva arquitectura)
from core.module_interface import BaseModule as BaseModuleInterface, ProcessingModule

# Configuración y gestión
from core.config_manager import ConfigManager

# Nuevos módulos de configuración (refactoring)
from core.cuda_paths import (
    get_cuda_paths,
    setup_cuda_environment,
    has_cuda_support,
)
from core.logging_setup import (
    setup_logging,
    get_logger,
)

# Pipeline y módulos (legacy - para compatibilidad)
from core.unified_pipeline import UnifiedPipeline as Pipeline
from core.module_base import BaseModule

# Nuevas estrategias de pipeline (refactoring)
from core.pipeline import (
    PipelineStrategy,
    PipelineMode,
    create_pipeline,
    get_available_modes,
    SequentialPipeline,
    ParallelPipeline,
    AsyncPipeline,
)

# Seguridad y utilidades
from core.security import (
    sanitize_path,
    sanitize_filename,
    validate_port,
    validate_latency,
)

# Constantes centralizadas
from core.constants import (
    SERVER_HOST,
    SERVER_PORT_DEFAULT,
    SRT_PORT_DEFAULT,
    RTMP_PORT_DEFAULT,
    API_ENDPOINTS,
    WS_PATHS,
    API_BASE_PATH,
    WS_BASE_PATH,
    HLS_PATH,
    DEFAULT_STREAM_URLS,
    CONFIG_FILE,
    OUTPUT_DIR,
    LOGS_DIR,
    MODELS_DIR,
    BIN_DIR,
    FFMPEG_URLS,
    ALLOWED_WHISPER_MODELS,
    ALLOWED_LANGUAGES,
    ALLOWED_DEVICES,
    ALLOWED_TTS_ENGINES,
    ALLOWED_ENCODER_MODES,
    EXTERNAL_URLS,
)

# Paths utilities
from core.paths import (
    get_project_root,
    get_config_path,
    get_output_dir,
    get_logs_dir,
    get_models_dir,
    get_bin_dir,
    get_temp_dir,
    get_hls_output_dir,
    get_recording_dir,
    ensure_directory,
    ensure_project_dirs,
    resolve_path,
    is_within_project,
    get_static_dir,
    get_server_log_file,
)

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
    "ALLOWED_ENCODER_MODELS",
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
