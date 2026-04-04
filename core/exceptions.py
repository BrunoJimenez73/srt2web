"""
Excepciones personalizadas para SRT2Web.

Este módulo define una jerarquía de excepciones específicas para cada componente
del pipeline, facilitando el manejo de errores y el debugging.
"""

from typing import Any, Dict, Optional


class SRT2WebError(Exception):
    """
    Error base para todas las excepciones de SRT2Web.
    
    Attributes:
        message: Descripción del error
        module: Nombre del módulo que generó el error
        context: Información adicional sobre el contexto del error
    """
    
    def __init__(
        self, 
        message: str, 
        module: Optional[str] = None, 
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.module = module
        self.context = context or {}
        
        # Construir mensaje completo
        full_message = message
        if module:
            full_message = f"[{module}] {message}"
        if context:
            full_message += f" (context: {context})"
        
        super().__init__(full_message)


# ============================================================================
# Errores de Configuración
# ============================================================================

class ConfigError(SRT2WebError):
    """Error en la configuración del sistema."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="config", **kwargs)


class ValidationError(ConfigError):
    """Error de validación de configuración."""
    pass


# ============================================================================
# Errores de Pipeline
# ============================================================================

class PipelineError(SRT2WebError):
    """Error en el pipeline principal."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="pipeline", **kwargs)


class PipelineStateError(PipelineError):
    """Error en el estado del pipeline (ej: iniciar cuando ya está corriendo)."""
    pass


class PipelineDataError(PipelineError):
    """Error en los datos del pipeline (ej: datos faltantes o inválidos)."""
    pass


# ============================================================================
# Errores de Módulos
# ============================================================================

class ModuleError(SRT2WebError):
    """Error base para errores de módulos."""
    
    def __init__(self, message: str, module: str, **kwargs):
        super().__init__(message, module=module, **kwargs)


class ModuleInitializationError(ModuleError):
    """Error al inicializar un módulo."""
    pass


class ModuleProcessingError(ModuleError):
    """Error al procesar datos en un módulo."""
    pass


class ModuleShutdownError(ModuleError):
    """Error al cerrar/liberar recursos de un módulo."""
    pass


# ============================================================================
# Errores de Input
# ============================================================================

class InputError(ModuleError):
    """Error base para errores de input."""
    
    def __init__(self, message: str, module: str = "input", **kwargs):
        super().__init__(message, module=module, **kwargs)


class SRTInputError(InputError):
    """Error en la ingestión SRT."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="srt_input", **kwargs)


class RTMPInputError(InputError):
    """Error en la ingestión RTMP."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="rtmp_input", **kwargs)


class FileInputError(InputError):
    """Error en la lectura de archivo."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="file_input", **kwargs)


# ============================================================================
# Errores de Procesamiento
# ============================================================================

class AudioExtractorError(ModuleError):
    """Error al extraer audio del video."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="audio_extractor", **kwargs)


class TranscriberError(ModuleError):
    """Error en la transcripción de audio a texto."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="transcriber", **kwargs)


class TranslatorError(ModuleError):
    """Error en la traducción de texto."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="translator", **kwargs)


class SubtitleGeneratorError(ModuleError):
    """Error en la generación de subtítulos."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="subtitle_generator", **kwargs)


class TTSError(ModuleError):
    """Error en la generación de TTS (text-to-speech)."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="tts_engine", **kwargs)


class AudioMixerError(ModuleError):
    """Error en la mezcla de audio."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="audio_mixer", **kwargs)


class VideoMuxerError(ModuleError):
    """Error en el muxing de video."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="video_muxer", **kwargs)


# ============================================================================
# Errores de Output
# ============================================================================

class OutputError(ModuleError):
    """Error base para errores de output."""
    
    def __init__(self, message: str, module: str = "output", **kwargs):
        super().__init__(message, module=module, **kwargs)


class HLSOutputError(OutputError):
    """Error en la generación de HLS."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="hls_output", **kwargs)


class WebRTCOutputError(OutputError):
    """Error en la generación de WebRTC."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="webrtc_output", **kwargs)


# ============================================================================
# Errores de Servidor
# ============================================================================

class ServerError(SRT2WebError):
    """Error base para errores del servidor."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="server", **kwargs)


class APIError(ServerError):
    """Error en la API REST."""
    pass


class WebSocketError(ServerError):
    """Error en la conexión WebSocket."""
    pass


class SecurityError(ServerError):
    """Error de seguridad (auth, rate limiting, etc)."""
    pass


# ============================================================================
# Errores de Recursos
# ============================================================================

class ResourceError(SRT2WebError):
    """Error en la gestión de recursos (memoria, disco, GPU)."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="resource", **kwargs)


class MemoryError(ResourceError):
    """Error de memoria insuficiente."""
    pass


class DiskSpaceError(ResourceError):
    """Error de espacio en disco insuficiente."""
    pass


class GPUError(ResourceError):
    """Error relacionado con GPU (CUDA, MPS, etc)."""
    pass


# ============================================================================
# Errores de Dependencias Externas
# ============================================================================

class DependencyError(SRT2WebError):
    """Error en dependencia externa (FFmpeg, modelos, etc)."""
    pass


class FFmpegError(DependencyError):
    """Error en la ejecución de FFmpeg."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="ffmpeg", **kwargs)


class ModelError(DependencyError):
    """Error al cargar/ejecutar modelo (Whisper, TTS, etc)."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, module="model", **kwargs)
