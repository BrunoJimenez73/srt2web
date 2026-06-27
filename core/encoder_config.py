"""
Configuración de encoder para módulos de video.

Proporciona configuración centralizada de parámetros de codificación
de video que puede ser usada por múltiples módulos.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("srt2web.encoder_config")

# Type alias for GPU info dict
GpuInfo = dict[str, bool]


class EncoderConfig:
    """Configuración de codificación de video y audio."""

    # Presets de CPU (libx264) con valores CRF asociados
    CPU_PRESETS = {  # noqa: RUF012
        "ultrafast": {"crf": 28, "description": "Máxima velocidad"},
        "superfast": {"crf": 26, "description": "Muy rápida"},
        "veryfast": {"crf": 24, "description": "Rápida"},
        "faster": {"crf": 22, "description": "Más rápida"},
        "fast": {"crf": 20, "description": "Rápida"},
        "medium": {"crf": 18, "description": "Equilibrada"},
        "slow": {"crf": 16, "description": "Lenta"},
        "slower": {"crf": 14, "description": "Más lenta"},
        "veryslow": {"crf": 12, "description": "Máxima calidad"},
    }

    # Presets de GPU (NVENC) con valores CQ asociados
    # Mayor CQ = menor calidad pero más rápido
    GPU_PRESETS = {  # noqa: RUF012
        "p1": {"cq": 28, "description": "Ultra velocidad"},
        "p2": {"cq": 26, "description": "Muy rápida"},
        "p3": {"cq": 24, "description": "Rápida"},
        "p4": {"cq": 22, "description": "Equilibrada"},
        "p5": {"cq": 20, "description": "Calidad"},
        "p6": {"cq": 18, "description": "Alta calidad"},
        "p7": {"cq": 17, "description": "Máxima calidad"},
        "p8": {"cq": 15, "description": "Ultra calidad"},
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """Inicializar configuración de encoder."""
        if config is None:
            config = {}

        # Modo de codificación
        self.encoder_mode = config.get("encoder_mode", "auto")  # auto, passthrough, cpu, gpu_nvenc, gpu_amf, gpu_qsv

        # Configuración de video (CPU)
        self.video_preset = config.get("video_preset", "medium")
        self.video_crf = config.get("video_crf", 18)
        self.video_profile = config.get("video_profile", "high")
        self.video_tune = config.get("video_tune", "zerolatency")

        # Configuración de GPU
        self.gpu_preset = config.get("gpu_preset") or "p4"

        # FPS de video (usado para GOP en NVENC)
        self.video_fps: int | None = config.get("video_fps")

        # Configuración de audio
        self.audio_codec = config.get("audio_codec") or "aac"
        self.audio_bitrate = config.get("audio_bitrate") or "192k"
        self.audio_sample_rate = config.get("audio_sample_rate") or 48000

    def get_cpu_args(self) -> list[str]:
        """Obtener argumentos FFmpeg para codificación CPU."""
        args = []

        # Preset y CRF
        crf = self.CPU_PRESETS[self.video_preset]["crf"] if self.video_preset in self.CPU_PRESETS else self.video_crf

        args.extend(["-preset", self.video_preset, "-crf", str(crf)])

        # Perfil de video
        args.extend(["-profile:v", self.video_profile])

        # Tuning
        if self.video_tune and self.video_tune != "none":
            args.extend(["-tune", self.video_tune])

        return args

    def get_gpu_nvenc_args(self) -> list[str]:
        """Obtener argumentos FFmpeg para GPU NVENC."""
        args = []

        # Preset y CQ
        preset_num = int(self.gpu_preset[1]) if len(self.gpu_preset) > 1 and self.gpu_preset[1].isdigit() else 3
        if preset_num <= 2:
            cq = "23"
        elif preset_num <= 4:
            cq = "20"
        else:
            cq = "17"

        args.extend(
            [
                "-preset",
                self.gpu_preset,
                "-rc",
                "vbr",
                "-cq",
                cq,
            ]
        )

        # Perfil de video
        args.extend(["-profile:v", self.video_profile])

        return args

    def get_gpu_amf_args(self) -> list[str]:
        """Obtener argumentos FFmpeg para GPU AMF."""
        args = []

        # Mapear preset a calidad AMF
        preset_map = {
            "ultrafast": "speed",
            "superfast": "speed",
            "veryfast": "speed",
            "faster": "balanced",
            "fast": "balanced",
            "medium": "balanced",
            "slow": "quality",
            "slower": "quality",
            "veryslow": "quality",
        }
        quality = preset_map.get(self.video_preset, "balanced")

        args.extend(["-usage", "lowlatency", "-quality", quality])

        return args

    def get_gpu_qsv_args(self) -> list[str]:
        """Obtener argumentos FFmpeg para GPU QSV."""
        args = []

        args.extend(["-low_power", "1", "-async_depth", "1"])

        return args

    def get_gpu_videotoolbox_args(self) -> list[str]:
        """Obtener argumentos FFmpeg para GPU VideoToolbox (Apple Silicon)."""
        return [
            "-preset",
            self.gpu_preset,
            "-profile:v",
            self.video_profile,
        ]

    def get_gpu_vaapi_args(self) -> list[str]:
        """Obtener argumentos FFmpeg para GPU VAAPI (Linux)."""
        return [
            "-preset",
            self.video_preset,
            "-profile:v",
            self.video_profile,
        ]

    def get_audio_args(self) -> list[str]:
        """Obtener argumentos FFmpeg para audio."""
        # Validar codec
        codec = self.audio_codec if self.audio_codec in ["aac", "opus"] else "aac"

        return [
            "-c:a",
            codec,
            "-b:a",
            self.audio_bitrate,
            "-ar",
            str(self.audio_sample_rate),
        ]

    def get_passthrough_args(self) -> list[str]:
        """Obtener argumentos FFmpeg para modo passthrough (sin recodificar)."""
        return ["-c:v", "copy", "-c:a", "copy"]

    def to_dict(self) -> dict[str, Any]:
        """Convertir configuración a diccionario."""
        return {
            "encoder_mode": self.encoder_mode,
            "video_preset": self.video_preset,
            "video_crf": self.video_crf,
            "video_profile": self.video_profile,
            "video_tune": self.video_tune,
            "gpu_preset": self.gpu_preset,
            "video_fps": self.video_fps,
            "audio_codec": self.audio_codec,
            "audio_bitrate": self.audio_bitrate,
            "audio_sample_rate": self.audio_sample_rate,
        }

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> EncoderConfig:
        """Crear configuración desde diccionario."""
        return cls(config_dict)

    def resolve_encoder(self, gpu_info: GpuInfo) -> tuple[str, str, list[str]]:
        """Resolve encoder, preset, and extra args based on mode and GPU availability.

        Returns:
            Tuple of (encoder_string, preset_string, extra_ffmpeg_args)
        """
        encoder = "libx264"
        preset = self.video_preset
        extra_args: list[str] = []
        encoder_mode = self.encoder_mode

        if encoder_mode == "auto":
            if gpu_info.get("nvenc"):
                encoder_mode = "gpu_nvenc"
            elif gpu_info.get("amf"):
                encoder_mode = "gpu_amf"
            elif gpu_info.get("qsv"):
                encoder_mode = "gpu_qsv"
            elif gpu_info.get("vaapi"):
                encoder_mode = "gpu_vaapi"
            elif gpu_info.get("videotoolbox"):
                encoder_mode = "gpu_videotoolbox"
            else:
                encoder_mode = "cpu"

        if encoder_mode == "passthrough":
            encoder = "copy"
            preset = ""
            extra_args = []
        elif encoder_mode == "gpu_nvenc" and gpu_info.get("nvenc"):
            encoder = "h264_nvenc"
            preset = self.gpu_preset
            extra_args = self.get_gpu_nvenc_args()
        elif encoder_mode == "gpu_amf" and gpu_info.get("amf"):
            encoder = "h264_amf"
            preset = self.video_preset
            extra_args = self.get_gpu_amf_args()
        elif encoder_mode == "gpu_qsv" and gpu_info.get("qsv"):
            encoder = "h264_qsv"
            preset = self.video_preset
            extra_args = self.get_gpu_qsv_args()
        elif encoder_mode == "gpu_videotoolbox" and gpu_info.get("videotoolbox"):
            encoder = "h264_videotoolbox"
            preset = self.gpu_preset
            extra_args = self.get_gpu_videotoolbox_args()
        elif encoder_mode == "gpu_vaapi" and gpu_info.get("vaapi"):
            encoder = "h264_vaapi"
            preset = self.video_preset
            extra_args = self.get_gpu_vaapi_args()
        else:
            encoder = "libx264"
            preset = self.video_preset
            extra_args = self.get_cpu_args()

        return encoder, preset, extra_args

    def get_encoder_status(self, gpu_info: GpuInfo, ffmpeg_path: str | None) -> dict[str, Any]:
        """Build encoder status dict for ModuleStatus.extra.

        Returns dict with keys: encoder_mode, actual_encoder, using_gpu,
        gpu_available, gpu_preset, encoder_label.
        """
        using_gpu = False
        actual_encoder = "libx264"
        encoder_label = "CPU"
        encoder_mode = self.encoder_mode

        if encoder_mode == "passthrough":
            actual_encoder = "copy"
            encoder_label = "Passthrough"
        elif ffmpeg_path and encoder_mode in (
            "auto",
            "gpu_nvenc",
            "gpu_amf",
            "gpu_qsv",
            "gpu_vaapi",
            "gpu_videotoolbox",
        ):
            if encoder_mode == "gpu_nvenc" and gpu_info.get("nvenc"):
                using_gpu = True
                actual_encoder = "h264_nvenc"
                encoder_label = "H.264 NVENC"
            elif encoder_mode == "gpu_nvenc" and not gpu_info.get("nvenc"):
                logger.warning("NVENC requested but not detected by FFmpeg. " "Assuming compatibility.")
                using_gpu = True
                actual_encoder = "h264_nvenc"
                encoder_label = "H.264 NVENC (ASSUMED)"
            elif gpu_info.get("nvenc"):
                using_gpu = True
                actual_encoder = "h264_nvenc"
                encoder_label = "H.264 NVENC"
            elif gpu_info.get("amf"):
                using_gpu = True
                actual_encoder = "h264_amf"
                encoder_label = "H.264 AMF"
            elif gpu_info.get("qsv"):
                using_gpu = True
                actual_encoder = "h264_qsv"
                encoder_label = "H.264 QSV"
            elif gpu_info.get("vaapi"):
                using_gpu = True
                actual_encoder = "h264_vaapi"
                encoder_label = "H.264 VAAPI"
            elif gpu_info.get("videotoolbox"):
                using_gpu = True
                actual_encoder = "h264_videotoolbox"
                encoder_label = "H.264 VideoToolbox"

        if not using_gpu and encoder_mode != "passthrough":
            encoder_label = "H.264 CPU"

        return {
            "encoder_mode": encoder_mode,
            "actual_encoder": actual_encoder,
            "using_gpu": using_gpu,
            "gpu_available": gpu_info,
            "gpu_preset": self.gpu_preset,
            "encoder_label": encoder_label,
        }
