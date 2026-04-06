"""
Configuration Schema - Validación estricta de configuración con Pydantic.

Define la estructura completa y válida de config.yaml con tipos estrictos,
valores por defecto, validaciones de rango y validaciones cruzadas.

Características:
✅ Tipos estrictos para TODOS los campos
✅ Validaciones de rango automáticas
✅ Valores por defecto consistentes
✅ Validaciones cruzadas entre secciones
✅ Conversión automática desde/y a dict
✅ Serialización/deserialización segura
✅ Mensajes de error detallados
"""

from typing import Optional, Union, Literal, Dict, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class PipelineModeEnum(str, Enum):
    """Modos de operación permitidos."""
    SEQUENTIAL = "sequential"
    THREAD_PARALLEL = "thread_parallel"
    ASYNCIO = "asyncio"


class DeviceEnum(str, Enum):
    """Dispositivos de cómputo permitidos."""
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"


class ModelSizeEnum(str, Enum):
    """Tamaños de modelo Whisper permitidos."""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"


class LanguageEnum(str, Enum):
    """Idiomas soportados."""
    AUTO = "auto"
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    IT = "it"
    PT = "pt"
    JA = "ja"
    ZH = "zh"
    KO = "ko"
    RU = "ru"


class InputTypeEnum(str, Enum):
    """Tipos de entrada permitidos."""
    SRT = "srt"
    RTMP = "rtmp"
    FILE = "file"


class OutputTypeEnum(str, Enum):
    """Tipos de salida permitidos."""
    WEB = "web"
    SRT = "srt"
    RTMP = "rtmp"
    FILE = "file"


class EncoderModeEnum(str, Enum):
    """Modos de encoder de video permitidos."""
    AUTO = "auto"
    CPU = "cpu"
    GPU_NVENC = "gpu_nvenc"
    GPU_AMF = "gpu_amf"
    GPU_QSV = "gpu_qsv"
    GPU_VIDEOTOOLBOX = "gpu_videotoolbox"


class SubtitleFormatEnum(str, Enum):
    """Formatos de subtítulos permitidos."""
    WEBVTT = "webvtt"
    SRT = "srt"
    ASS = "ass"


class TTSEngineEnum(str, Enum):
    """Motores TTS permitidos."""
    EDGE_TTS = "edge-tts"
    PIPER = "piper"
    ELEVENLABS = "elevenlabs"


class AudioCodecEnum(str, Enum):
    """Códecs de audio permitidos."""
    AAC = "aac"
    MP3 = "mp3"
    OPUS = "opus"


class VideoCodecEnum(str, Enum):
    """Códecs de video permitidos."""
    H264 = "h264"
    H265 = "h265"
    VP8 = "vp8"
    VP9 = "vp9"


# -----------------------------------------------------------------------------
# Modelos de configuración por secciones
# -----------------------------------------------------------------------------

class ServerConfig(BaseModel):
    """Configuración del servidor web."""
    host: str = Field(default="127.0.0.1", description="Dirección de escucha")
    port: int = Field(default=9999, ge=1, le=65535, description="Puerto del servidor")
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:*", "http://127.0.0.1:*"], description="Orígenes CORS permitidos")
    auth_token: str = Field(default="", description="Token de autenticación")
    rate_limit_rpm: int = Field(default=600, ge=1, le=10000, description="Límite de peticiones por minuto")
    max_request_size_mb: int = Field(default=100, ge=1, le=1000, description="Tamaño máximo de request en MB")


class SRTInputConfig(BaseModel):
    """Configuración de entrada SRT."""
    listen_port: int = Field(default=9000, ge=1, le=65535, description="Puerto de escucha SRT")
    mode: Literal["listener", "caller"] = Field(default="listener", description="Modo SRT")
    latency_ms: int = Field(default=200, ge=0, le=5000, description="Latencia SRT en ms")
    caller_address: str = Field(default="", description="Dirección del caller en modo caller")


class RTMPInputConfig(BaseModel):
    """Configuración de entrada RTMP."""
    listen_port: int = Field(default=1935, ge=1, le=65535, description="Puerto de escucha RTMP")
    app: str = Field(default="live", description="Aplicación RTMP")
    stream_key: str = Field(default="stream", description="Clave de stream RTMP")
    url: str = Field(default="", description="URL RTMP en modo pull")
    mode: Literal["listener", "pull"] = Field(default="listener", description="Modo RTMP")
    chunk_duration_sec: int = Field(default=10, ge=1, le=60, description="Duración de chunk en segundos")


class FileInputConfig(BaseModel):
    """Configuración de entrada archivo."""
    path: str = Field(default="", description="Ruta al archivo de video")
    loop: bool = Field(default=False, description="Repetir archivo en bucle")
    speed: float = Field(default=1.0, ge=0.1, le=10.0, description="Velocidad de reproducción")
    chunk_duration_sec: int = Field(default=10, ge=1, le=60, description="Duración de chunk en segundos")


class InputConfig(BaseModel):
    """Configuración general de entrada."""
    type: InputTypeEnum = Field(default=InputTypeEnum.SRT, description="Tipo de entrada")
    srt: SRTInputConfig = Field(default_factory=SRTInputConfig, description="Configuración SRT")
    rtmp: RTMPInputConfig = Field(default_factory=RTMPInputConfig, description="Configuración RTMP")
    file: FileInputConfig = Field(default_factory=FileInputConfig, description="Configuración archivo")


class WebOutputConfig(BaseModel):
    """Configuración de salida Web (HLS)."""
    segment_duration: int = Field(default=4, ge=1, le=30, description="Duración de segmento HLS en segundos")
    list_size: int = Field(default=6, ge=1, le=20, description="Número de segmentos en manifiesto")
    audio_offset_ms: int = Field(default=0, ge=-1000, le=1000, description="Offset de audio en ms")
    encoder_mode: EncoderModeEnum = Field(default=EncoderModeEnum.AUTO, description="Modo de encoder de video")


class RTMPOutputConfig(BaseModel):
    """Configuración de salida RTMP."""
    url: str = Field(default="rtmp://localhost/live/stream", description="URL de destino RTMP")
    video_bitrate: str = Field(default="2500k", description="Bitrate de video")
    audio_bitrate: str = Field(default="128k", description="Bitrate de audio")
    video_codec: VideoCodecEnum = Field(default=VideoCodecEnum.H264, description="Códec de video")
    preset: str = Field(default="medium", description="Preset de calidad")
    audio_codec: AudioCodecEnum = Field(default=AudioCodecEnum.AAC, description="Códec de audio")
    encoder_mode: EncoderModeEnum = Field(default=EncoderModeEnum.AUTO, description="Modo de encoder de video")


class SRTOutputConfig(BaseModel):
    """Configuración de salida SRT."""
    url: str = Field(default="srt://localhost:9001", description="URL de destino SRT")
    mode: Literal["listener", "caller"] = Field(default="caller", description="Modo SRT")
    latency_ms: int = Field(default=200, ge=0, le=5000, description="Latencia SRT en ms")
    stream_id: str = Field(default="", description="Stream ID SRT")
    passphrase: str = Field(default="", description="Contraseña SRT")
    video_bitrate: str = Field(default="2500k", description="Bitrate de video")
    audio_bitrate: str = Field(default="128k", description="Bitrate de audio")
    video_codec: VideoCodecEnum = Field(default=VideoCodecEnum.H264, description="Códec de video")
    preset: str = Field(default="medium", description="Preset de calidad")
    audio_codec: AudioCodecEnum = Field(default=AudioCodecEnum.AAC, description="Códec de audio")


class FileOutputConfig(BaseModel):
    """Configuración de salida archivo."""
    save_video: bool = Field(default=True, description="Guardar video")
    save_audio: bool = Field(default=True, description="Guardar audio")
    save_subtitles: bool = Field(default=True, description="Guardar subtítulos")
    path: str = Field(default="./output", description="Directorio de salida")


class OutputConfig(BaseModel):
    """Configuración general de salida."""
    type: OutputTypeEnum = Field(default=OutputTypeEnum.WEB, description="Tipo de salida")
    web: WebOutputConfig = Field(default_factory=WebOutputConfig, description="Configuración Web/HLS")
    hls: WebOutputConfig = Field(default_factory=WebOutputConfig, description="Alias para web")
    rtmp: RTMPOutputConfig = Field(default_factory=RTMPOutputConfig, description="Configuración RTMP")
    srt: SRTOutputConfig = Field(default_factory=SRTOutputConfig, description="Configuración SRT")
    file: FileOutputConfig = Field(default_factory=FileOutputConfig, description="Configuración archivo")


class PipelineConfig(BaseModel):
    """Configuración del pipeline."""
    chunk_duration_sec: int = Field(default=15, ge=1, le=60, description="Duración de chunk en segundos")
    mode: PipelineModeEnum = Field(default=PipelineModeEnum.THREAD_PARALLEL, description="Modo de operación del pipeline")
    max_concurrent_chunks: int = Field(default=3, ge=1, le=10, description="Máximo de chunks procesando simultáneamente")
    buffer_size: int = Field(default=5, ge=1, le=20, description="Tamaño del buffer de entrada")
    retry_attempts: int = Field(default=2, ge=0, le=10, description="Número de reintentos por módulo")
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Retraso entre reintentos en segundos")


class AudioExtractorConfig(BaseModel):
    """Configuración de extractor de audio."""
    enabled: bool = Field(default=True, description="Módulo habilitado")


class TranscriberConfig(BaseModel):
    """Configuración de transcripción Whisper."""
    enabled: bool = Field(default=True, description="Módulo habilitado")
    model: ModelSizeEnum = Field(default=ModelSizeEnum.TINY, description="Tamaño del modelo Whisper")
    language: LanguageEnum = Field(default=LanguageEnum.AUTO, description="Idioma de transcripción")
    device: DeviceEnum = Field(default=DeviceEnum.AUTO, description="Dispositivo de cómputo")
    beam_size: int = Field(default=2, ge=1, le=10, description="Tamaño de beam para decoding")


class TranslatorConfig(BaseModel):
    """Configuración de traductor."""
    enabled: bool = Field(default=True, description="Módulo habilitado")
    source_lang: LanguageEnum = Field(default=LanguageEnum.EN, description="Idioma origen")
    target_lang: LanguageEnum = Field(default=LanguageEnum.ES, description="Idioma destino")


class SubtitleGeneratorConfig(BaseModel):
    """Configuración de generador de subtítulos."""
    enabled: bool = Field(default=True, description="Módulo habilitado")
    format: SubtitleFormatEnum = Field(default=SubtitleFormatEnum.WEBVTT, description="Formato de subtítulos")
    use_translated: bool = Field(default=True, description="Usar texto traducido")
    chunk_duration: int = Field(default=10, ge=1, le=60, description="Duración de chunk de subtítulos en segundos")


class TTSEngineConfig(BaseModel):
    """Configuración de motor TTS."""
    enabled: bool = Field(default=False, description="Módulo habilitado")
    engine: TTSEngineEnum = Field(default=TTSEngineEnum.EDGE_TTS, description="Motor TTS a usar")
    device: DeviceEnum = Field(default=DeviceEnum.AUTO, description="Dispositivo de cómputo")
    voice: str = Field(default="es-ES-ElviraNeural", description="Voz TTS")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Velocidad de habla")


class AudioMixerConfig(BaseModel):
    """Configuración de mezclador de audio."""
    enabled: bool = Field(default=False, description="Módulo habilitado")
    original_volume: float = Field(default=0.2, ge=0.0, le=2.0, description="Volumen audio original")
    tts_volume: float = Field(default=1.0, ge=0.0, le=2.0, description="Volumen audio TTS")
    dubbed_volume: float = Field(default=1.0, ge=0.0, le=2.0, description="Alias para tts_volume")


class VideoMuxerConfig(BaseModel):
    """Configuración de muxer de video."""
    enabled: bool = Field(default=True, description="Módulo habilitado")
    engine: Literal["hls", "webrtc"] = Field(default="hls", description="Motor de salida")
    hls_segment_duration: int = Field(default=4, ge=1, le=30, description="Duración de segmento HLS en segundos")
    hls_list_size: int = Field(default=6, ge=1, le=20, description="Número de segmentos en manifiesto")
    audio_offset_ms: int = Field(default=0, ge=-1000, le=1000, description="Offset de audio en ms")
    encoder_mode: EncoderModeEnum = Field(default=EncoderModeEnum.AUTO, description="Modo de encoder de video")
    video_quality: Literal["low", "medium", "high", "ultra"] = Field(default="medium", description="Calidad de video")
    video_crf: int = Field(default=23, ge=0, le=51, description="CRF para compresión video")
    audio_codec: AudioCodecEnum = Field(default=AudioCodecEnum.AAC, description="Códec de audio")
    audio_bitrate: str = Field(default="128k", description="Bitrate de audio")
    audio_samplerate: str = Field(default="48000", description="Sample rate de audio")
    video_bitrate: Optional[str] = Field(default=None, description="Bitrate de video fijo")
    video_fps: Optional[int] = Field(default=None, ge=1, le=120, description="FPS de video")
    video_width: Optional[int] = Field(default=None, ge=160, le=7680, description="Ancho de video")
    video_height: Optional[int] = Field(default=None, ge=90, le=4320, description="Alto de video")
    webrtc_audio_codec: Optional[AudioCodecEnum] = Field(default=None, description="Códec audio WebRTC")
    webrtc_audio_bitrate: Optional[str] = Field(default=None, description="Bitrate audio WebRTC")
    audio_sample_rate: Optional[int] = Field(default=None, ge=8000, le=96000, description="Sample rate de audio")
    gpu_preset: str = Field(default="p7", description="Preset de encoder GPU")
    video_preset: str = Field(default="medium", description="Preset de calidad CPU")


class ModulesConfig(BaseModel):
    """Configuración de módulos del pipeline."""
    audio_extractor: AudioExtractorConfig = Field(default_factory=AudioExtractorConfig, description="Extractor de audio")
    transcriber: TranscriberConfig = Field(default_factory=TranscriberConfig, description="Transcriptor Whisper")
    translator: TranslatorConfig = Field(default_factory=TranslatorConfig, description="Traductor")
    subtitle_generator: SubtitleGeneratorConfig = Field(default_factory=SubtitleGeneratorConfig, description="Generador de subtítulos")
    tts_engine: TTSEngineConfig = Field(default_factory=TTSEngineConfig, description="Motor TTS")
    audio_mixer: AudioMixerConfig = Field(default_factory=AudioMixerConfig, description="Mezclador de audio")
    video_muxer: VideoMuxerConfig = Field(default_factory=VideoMuxerConfig, description="Muxer de video")


class OutputDirConfig(BaseModel):
    """Configuración de directorio de salida."""
    directory: str = Field(default="./output", description="Directorio de salida")


class SRT2WebConfig(BaseModel):
    """
    Modelo completo de configuración de SRT2Web.

    Este modelo define TODOS los campos posibles con sus tipos,
    validaciones y valores por defecto. Cualquier campo que no
    cumpla con estas reglas será rechazado inmediatamente.
    """
    server: ServerConfig = Field(default_factory=ServerConfig, description="Configuración del servidor")
    input: InputConfig = Field(default_factory=InputConfig, description="Configuración de entrada")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Configuración de salida")
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig, description="Configuración del pipeline")
    modules: ModulesConfig = Field(default_factory=ModulesConfig, description="Configuración de módulos")
    output_dir: OutputDirConfig = Field(default_factory=OutputDirConfig, description="Directorio de salida")

    # -------------------------------------------------------------------------
    # Validaciones cruzadas entre secciones
    # -------------------------------------------------------------------------
    @model_validator(mode='after')
    def validate_module_dependencies(self) -> 'SRT2WebConfig':
        """Valida dependencias entre módulos."""
        errors = []

        # Subtítulos requieren traductor activado
        if self.modules.subtitle_generator.enabled and not self.modules.translator.enabled:
            errors.append("Subtitle generator requires translator to be enabled")

        # TTS requiere traductor activado
        if self.modules.tts_engine.enabled and not self.modules.translator.enabled:
            errors.append("TTS engine requires translator to be enabled")

        # Audio mixer requiere TTS y traductor activados
        if self.modules.audio_mixer.enabled:
            if not self.modules.translator.enabled:
                errors.append("Audio mixer requires translator to be enabled")
            if not self.modules.tts_engine.enabled:
                errors.append("Audio mixer requires TTS engine to be enabled")

        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

        return self

    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_video_codec(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrar valores antiguos de video_codec automáticamente."""
        # Mapeo de valores antiguos a nuevos estandarizados
        codec_migration = {
            "libx264": "h264",
            "x264": "h264",
            "h264_nvenc": "h264",
            "h264_qsv": "h264",
            "h264_amf": "h264",
            "libx265": "h265",
            "x265": "h265",
            "hevc_nvenc": "h265",
            "hevc_qsv": "h265",
            "hevc_amf": "h265",
            "libvpx": "vp8",
            "libvpx-vp9": "vp9",
        }

        # Migrar RTMP output
        if "output" in data and "rtmp" in data["output"]:
            old_codec = data["output"]["rtmp"].get("video_codec")
            if old_codec in codec_migration:
                data["output"]["rtmp"]["video_codec"] = codec_migration[old_codec]

        # Migrar SRT output
        if "output" in data and "srt" in data["output"]:
            old_codec = data["output"]["srt"].get("video_codec")
            if old_codec in codec_migration:
                data["output"]["srt"]["video_codec"] = codec_migration[old_codec]

        return data

    @model_validator(mode='after')
    def validate_chunk_duration_consistency(self) -> 'SRT2WebConfig':
        """Valida consistencia de duración de chunks entre secciones."""
        pipeline_chunk = self.pipeline.chunk_duration_sec

        # Chunk duration en input debe coincidir con pipeline
        if hasattr(self.input, 'srt'):
            if hasattr(self.input.srt, 'chunk_duration_sec'):
                self.input.srt.chunk_duration_sec = pipeline_chunk

        if hasattr(self.input, 'rtmp'):
            if hasattr(self.input.rtmp, 'chunk_duration_sec'):
                self.input.rtmp.chunk_duration_sec = pipeline_chunk

        if hasattr(self.input, 'file'):
            if hasattr(self.input.file, 'chunk_duration_sec'):
                self.input.file.chunk_duration_sec = pipeline_chunk

        # Chunk duration en subtitles debe coincidir
        if self.modules.subtitle_generator.enabled:
            self.modules.subtitle_generator.chunk_duration = pipeline_chunk

        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario serializable."""
        return self.model_dump(exclude_unset=False, exclude_defaults=False, mode='json')

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SRT2WebConfig':
        """Crear instancia desde diccionario con validación."""
        return cls(**data)