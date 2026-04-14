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
]
