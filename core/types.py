"""
Tipos compartidos para SRT2Web.

Este módulo define tipos y estructuras de datos compartidas entre módulos,
facilitando la consistencia y el type checking.
"""

import time
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.schemas import ModuleState, ModuleStatus, PipelineState

# ============================================================================
# Enums (mantener los que no están en schemas)
# ============================================================================


class LogLevel(str, Enum):
    """Niveles de log."""

    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class InputType(str, Enum):
    """Tipos de input soportados."""

    SRT = "srt"
    RTMP = "rtmp"
    FILE = "file"
    WEBRTC = "webrtc"


class OutputType(str, Enum):
    """Tipos de output soportados."""

    HLS = "hls"
    WEBRTC = "webrtc"
    SRT = "srt"
    FILE = "file"


class DeviceType(str, Enum):
    """Tipos de dispositivo para procesamiento."""

    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"
    AUTO = "auto"


class EncoderMode(str, Enum):
    """Modos de encoding de video.

    DEPRECATED: Usar EncoderModeEnum en core.config_schema en su lugar.
    """

    SOFTWARE = "software"
    NVENC = "nvenc"  # NVIDIA (obsoleto, usar GPU_NVENC)
    VIDEOTOOLBOX = "videotoolbox"  # Apple (obsoleto, usar GPU_VIDEOTOOLBOX)
    QSZ = "qsv"  # Intel QuickSync (obsoleto, usar GPU_QSV)
    VAAPI = "vaapi"  # Linux VA-API


warnings.warn(
    "EncoderMode está deprecado. Usar EncoderModeEnum de core.config_schema.",
    DeprecationWarning,
    stacklevel=2,
)


@dataclass
class PipelineStatus:
    """
    Estado general del pipeline.
    """

    state: PipelineState = PipelineState.IDLE

    # Módulos
    modules: dict[str, ModuleStatus] = field(default_factory=dict)

    # Métricas generales
    uptime: float = 0.0
    start_time: float | None = None
    total_chunks_processed: int = 0

    # Información del sistema
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_usage: float = 0.0
    gpu_memory_usage: float = 0.0

    # Configuración actual
    input_type: InputType = InputType.SRT
    output_type: OutputType = OutputType.HLS

    @property
    def is_running(self) -> bool:
        """Verifica si el pipeline está corriendo."""
        return self.state in [PipelineState.RUNNING, PipelineState.STARTING]

    @property
    def all_modules_healthy(self) -> bool:
        """Verifica si todos los módulos están saludables."""
        return all(
            getattr(module, "is_healthy", module.state == ModuleState.RUNNING) for module in self.modules.values()
        )


@dataclass
class LogMessage:
    """
    Mensaje de log estructurado.
    """

    level: LogLevel
    message: str
    module: str | None = None
    timestamp: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def iso_timestamp(self) -> str:
        """Obtiene el timestamp en formato ISO."""
        from datetime import datetime

        return datetime.fromtimestamp(self.timestamp).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convierte el mensaje a diccionario."""
        return {
            "level": self.level.value,
            "message": self.message,
            "module": self.module,
            "timestamp": self.iso_timestamp,
            "context": self.context,
        }


@dataclass
class SystemMetrics:
    """
    Métricas del sistema.
    """

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0

    # GPU (si está disponible)
    gpu_available: bool = False
    gpu_name: str | None = None
    gpu_usage_percent: float = 0.0
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    gpu_temperature: float | None = None

    # Proceso actual
    process_cpu_percent: float = 0.0
    process_memory_percent: float = 0.0
    process_memory_used_mb: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convierte las métricas a diccionario."""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_total_mb": self.memory_total_mb,
            "disk_percent": self.disk_percent,
            "disk_used_gb": self.disk_used_gb,
            "disk_total_gb": self.disk_total_gb,
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "gpu_usage_percent": self.gpu_usage_percent,
            "gpu_memory_used_mb": self.gpu_memory_used_mb,
            "gpu_memory_total_mb": self.gpu_memory_total_mb,
            "gpu_temperature": self.gpu_temperature,
            "process_cpu_percent": self.process_cpu_percent,
            "process_memory_percent": self.process_memory_percent,
            "process_memory_used_mb": self.process_memory_used_mb,
        }


@dataclass
class ChunkInfo:
    """
    Información sobre un chunk de video/audio.
    """

    index: int
    path: str
    duration: float
    start_time: float
    end_time: float
    size_bytes: int = 0

    @property
    def is_valid(self) -> bool:
        """Verifica si el chunk es válido."""
        return self.duration > 0 and self.path is not None


@dataclass
class AudioConfig:
    """
    Configuración de audio.
    """

    sample_rate: int = 16000
    channels: int = 1
    format: str = "s16le"  # Signed 16-bit little-endian
    bitrate: int | None = None  # bits per second


@dataclass
class VideoConfig:
    """
    Configuración de video.
    """

    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    codec: str = "h264"
    bitrate: int | None = None  # bits per second
    keyframe_interval: int = 10  # frames entre keyframes
    encoder_mode: EncoderMode = EncoderMode.SOFTWARE


@dataclass
class HLSConfig:
    """
    Configuración de salida HLS.
    """

    segment_duration: float = 6.0  # segundos
    playlist_size: int = 5  # número máximo de segmentos en playlist
    allow_cache: bool = True
    version: int = 3
    target_duration: float | None = None  # se calcula automáticamente si es None
