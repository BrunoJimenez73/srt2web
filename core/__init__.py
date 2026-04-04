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
    ConfigError,
    ValidationError,
    PipelineError,
    PipelineStateError,
    PipelineDataError,
    ModuleError,
    ModuleInitializationError,
    ModuleProcessingError,
    TranscriberError,
    TTSError,
    FFmpegError,
    GPUError,
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

# Pipeline y módulos (legacy - para compatibilidad)
from core.pipeline import Pipeline
from core.module_base import BaseModule

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
    "ConfigError",
    "ValidationError",
    "PipelineError",
    "PipelineStateError",
    "PipelineDataError",
    "ModuleError",
    "ModuleInitializationError",
    "ModuleProcessingError",
    "TranscriberError",
    "TTSError",
    "FFmpegError",
    "GPUError",
    # Componentes
    "ConfigManager",
    "Pipeline",
    "BaseModule",
    # Utilidades
    "sanitize_path",
    "sanitize_filename",
    "validate_port",
    "validate_latency",
]
