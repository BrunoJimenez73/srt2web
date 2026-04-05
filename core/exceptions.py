"""
Excepciones estandarizadas para SRT2Web.

Todas las excepciones del proyecto heredan de SRT2WebException
para permitir manejo centralizado y logging consistente.

Jerarquía de excepciones:
✅ SRT2WebException (base)
  ├─ ConfigurationError
  ├─ PipelineError
  │  ├─ PipelineStateError
  │  ├─ ModuleProcessingError
  │  └─ ChunkProcessingError
  ├─ InputSourceError
  │  ├─ SRTConnectionError
  │  └─ RTMPConnectionError
  ├─ OutputSinkError
  │  ├─ HLSMuxerError
  │  └─ WebRTCError
  ├─ ModuleError
  │  ├─ TranscriberError
  │  ├─ TranslatorError
  │  ├─ TTSError
  │  └─ AudioMixerError
  └─ InfrastructureError
     ├─ FFmpegError
     ├─ CUDAError
     └─ ResourceExhaustedError
"""

from typing import Optional, Dict, Any


class SRT2WebError(Exception):
    """
    Clase base para TODAS las excepciones de SRT2Web.
    
    Atributos:
        code: Código de error único
        message: Mensaje descriptivo
        details: Diccionario con detalles adicionales
        recoverable: Indica si el error es recuperable
    """
    code: str = "ERR_UNKNOWN"
    message: str = "Unknown error occurred"
    recoverable: bool = False

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recoverable: Optional[bool] = None,
        cause: Optional[Exception] = None,
    ):
        self.details = details or {}
        self.cause = cause
        
        if message is not None:
            self.message = message
            
        if recoverable is not None:
            self.recoverable = recoverable
            
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convertir excepción a diccionario serializable."""
        return {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
            "details": self.details,
        }

    def __str__(self) -> str:
        base = f"[{self.code}] {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        if self.cause:
            base += f" | Caused by: {type(self.cause).__name__}: {str(self.cause)}"
        return base


# -----------------------------------------------------------------------------
# Errores de Configuración
# -----------------------------------------------------------------------------

class ConfigurationError(SRT2WebError):
    """Error en la configuración del sistema."""
    code = "ERR_CONFIG"
    message = "Invalid configuration"


class ConfigurationValidationError(ConfigurationError):
    """Error de validación de campos de configuración."""
    code = "ERR_CONFIG_VALIDATION"
    message = "Configuration validation failed"


# -----------------------------------------------------------------------------
# Errores del Pipeline
# -----------------------------------------------------------------------------

class PipelineError(SRT2WebError):
    """Error general en el pipeline de procesamiento."""
    code = "ERR_PIPELINE"
    message = "Pipeline processing error"


class PipelineStateError(PipelineError):
    """Operación inválida para el estado actual del pipeline."""
    code = "ERR_PIPELINE_STATE"
    message = "Invalid pipeline state for operation"


class ModuleProcessingError(PipelineError):
    """Error en el procesamiento de un módulo."""
    code = "ERR_MODULE_PROCESSING"
    message = "Module processing failed"
    recoverable = True


class ChunkProcessingError(PipelineError):
    """Error procesando un chunk específico."""
    code = "ERR_CHUNK_PROCESSING"
    message = "Chunk processing failed"
    recoverable = True


# -----------------------------------------------------------------------------
# Errores de Fuente de Entrada
# -----------------------------------------------------------------------------

class InputSourceError(SRT2WebError):
    """Error en la fuente de entrada."""
    code = "ERR_INPUT"
    message = "Input source error"
    recoverable = True


class SRTConnectionError(InputSourceError):
    """Error de conexión SRT."""
    code = "ERR_INPUT_SRT_CONNECTION"
    message = "SRT connection error"


class RTMPConnectionError(InputSourceError):
    """Error de conexión RTMP."""
    code = "ERR_INPUT_RTMP_CONNECTION"
    message = "RTMP connection error"


# -----------------------------------------------------------------------------
# Errores de Salida
# -----------------------------------------------------------------------------

class OutputSinkError(SRT2WebError):
    """Error en el destino de salida."""
    code = "ERR_OUTPUT"
    message = "Output sink error"


class HLSMuxerError(OutputSinkError):
    """Error en el muxer HLS."""
    code = "ERR_OUTPUT_HLS"
    message = "HLS muxer error"
    recoverable = True


class WebRTCError(OutputSinkError):
    """Error en la conexión WebRTC."""
    code = "ERR_OUTPUT_WEBRTC"
    message = "WebRTC connection error"
    recoverable = True


# -----------------------------------------------------------------------------
# Errores de Módulos
# -----------------------------------------------------------------------------

class ModuleError(SRT2WebError):
    """Error específico de un módulo de procesamiento."""
    code = "ERR_MODULE"
    message = "Module error"


class TranscriberError(ModuleError):
    """Error en el transcriptor Whisper."""
    code = "ERR_MODULE_TRANSCRIBER"
    message = "Transcriber processing error"


class TranslatorError(ModuleError):
    """Error en el traductor."""
    code = "ERR_MODULE_TRANSLATOR"
    message = "Translator processing error"


class TTSError(ModuleError):
    """Error en el motor TTS."""
    code = "ERR_MODULE_TTS"
    message = "TTS processing error"


class AudioMixerError(ModuleError):
    """Error en el mezclador de audio."""
    code = "ERR_MODULE_AUDIO_MIXER"
    message = "Audio mixer error"


# -----------------------------------------------------------------------------
# Errores de Infraestructura
# -----------------------------------------------------------------------------

class InfrastructureError(SRT2WebError):
    """Error en la infraestructura subyacente."""
    code = "ERR_INFRASTRUCTURE"
    message = "Infrastructure error"


class FFmpegError(InfrastructureError):
    """Error en proceso FFmpeg."""
    code = "ERR_FFMPEG"
    message = "FFmpeg execution error"
    recoverable = True


class CUDAError(InfrastructureError):
    """Error de aceleración CUDA/GPU."""
    code = "ERR_CUDA"
    message = "CUDA/GPU acceleration error"


class ResourceExhaustedError(InfrastructureError):
    """Recursos del sistema agotados."""
    code = "ERR_RESOURCE_EXHAUSTED"
    message = "System resources exhausted"
    recoverable = True


# -----------------------------------------------------------------------------
# Funciones utilitarias
# -----------------------------------------------------------------------------

def wrap_exception(
    exc: Exception,
    target_exception: SRT2WebError,
    details: Optional[Dict[str, Any]] = None,
) -> SRT2WebError:
    """
    Envuelve una excepción externa en una excepción estandarizada de SRT2Web.
    
    Args:
        exc: Excepción original
        target_exception: Excepción SRT2Web para envolver
        details: Detalles adicionales
        
    Returns:
        Excepción SRT2Web estandarizada
    """
    if isinstance(exc, SRT2WebError):
        return exc
        
    if details is None:
        details = {}
        
    details["original_exception"] = type(exc).__name__
    details["original_message"] = str(exc)
    
    return target_exception(
        details=details,
        cause=exc,
    )