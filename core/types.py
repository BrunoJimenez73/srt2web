"""
Tipos compartidos para SRT2Web.

Este módulo define tipos y estructuras de datos compartidas entre módulos,
facilitando la consistencia y el type checking.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time


# ============================================================================
# Enums
# ============================================================================

class PipelineState(str, Enum):
    """Estados posibles del pipeline."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    PAUSED = "paused"


class ModuleState(str, Enum):
    """Estados posibles de un módulo."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    DISABLED = "disabled"


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
    """Modos de encoding de video."""
    SOFTWARE = "software"
    NVENC = "nvenc"  # NVIDIA
    VIDEOTOOLBOX = "videotoolbox"  # Apple
    QSV = "qsv"  # Intel QuickSync
    VAAPI = "vaapi"  # Linux VA-API


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PipelineData:
    """
    Datos que fluyen a través del pipeline.
    
    Esta clase representa los datos que pasan entre módulos,
    incluyendo metadatos y estado del procesamiento.
    """
    # Datos de video/audio
    video_chunk_path: Optional[str] = None
    audio_chunk_path: Optional[str] = None
    tts_audio_path: Optional[str] = None
    mixed_audio_path: Optional[str] = None
    
    # Datos de texto
    transcript: Optional[str] = None
    translation: Optional[str] = None
    detected_language: Optional[str] = None
    
    # Timing
    chunk_index: int = 0
    duration: float = 0.0
    cumulative_duration: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    # Metadatos
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Estado de procesamiento
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Verifica si los datos son válidos para procesamiento."""
        return self.video_chunk_path is not None or self.audio_chunk_path is not None
    
    @property
    def has_audio(self) -> bool:
        """Verifica si hay audio disponible."""
        return self.audio_chunk_path is not None
    
    @property
    def has_video(self) -> bool:
        """Verifica si hay video disponible."""
        return self.video_chunk_path is not None
    
    @property
    def has_transcript(self) -> bool:
        """Verifica si hay transcripción disponible."""
        return self.transcript is not None
    
    @property
    def has_translation(self) -> bool:
        """Verifica si hay traducción disponible."""
        return self.translation is not None


@dataclass
class ModuleStatus:
    """
    Estado de un módulo del pipeline.
    """
    name: str
    state: ModuleState = ModuleState.IDLE
    enabled: bool = True
    
    # Métricas
    processed_chunks: int = 0
    total_processing_time: float = 0.0
    last_processing_time: float = 0.0
    average_processing_time: float = 0.0
    
    # Información de error
    last_error: Optional[str] = None
    error_count: int = 0
    
    # Información específica del módulo
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_processing(self) -> bool:
        """Verifica si el módulo está procesando actualmente."""
        return self.state == ModuleState.PROCESSING
    
    @property
    def is_healthy(self) -> bool:
        """Verifica si el módulo está saludable."""
        return self.enabled and self.state != ModuleState.ERROR
    
    def update_processing_time(self, processing_time: float):
        """Actualiza las métricas de tiempo de procesamiento."""
        self.processed_chunks += 1
        self.last_processing_time = processing_time
        self.total_processing_time += processing_time
        self.average_processing_time = self.total_processing_time / self.processed_chunks


@dataclass
class PipelineStatus:
    """
    Estado general del pipeline.
    """
    state: PipelineState = PipelineState.IDLE
    
    # Módulos
    modules: Dict[str, ModuleStatus] = field(default_factory=dict)
    
    # Métricas generales
    uptime: float = 0.0
    start_time: Optional[float] = None
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
        return all(module.is_healthy for module in self.modules.values())


@dataclass
class LogMessage:
    """
    Mensaje de log estructurado.
    """
    level: LogLevel
    message: str
    module: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def iso_timestamp(self) -> str:
        """Obtiene el timestamp en formato ISO."""
        from datetime import datetime
        return datetime.fromtimestamp(self.timestamp).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
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
    gpu_name: Optional[str] = None
    gpu_usage_percent: float = 0.0
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    gpu_temperature: Optional[float] = None
    
    # Proceso actual
    process_cpu_percent: float = 0.0
    process_memory_percent: float = 0.0
    process_memory_used_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
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
    bitrate: Optional[int] = None  # bits per second


@dataclass
class VideoConfig:
    """
    Configuración de video.
    """
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    codec: str = "h264"
    bitrate: Optional[int] = None  # bits per second
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
    target_duration: Optional[float] = None  # se calcula automáticamente si es None