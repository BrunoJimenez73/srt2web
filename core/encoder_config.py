"""
Configuración de encoder para módulos de video.

Proporciona configuración centralizada de parámetros de codificación
de video que puede ser usada por múltiples módulos.
"""

from typing import Dict, Any, Optional


class EncoderConfig:
    """Configuración de codificación de video y audio."""

    # Presets de CPU (libx264) con valores CRF asociados
    CPU_PRESETS = {
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
    GPU_PRESETS = {
        "p1": {"cq": 28, "description": "Ultra velocidad"},
        "p2": {"cq": 26, "description": "Muy rápida"},
        "p3": {"cq": 24, "description": "Rápida"},
        "p4": {"cq": 22, "description": "Equilibrada"},
        "p5": {"cq": 20, "description": "Calidad"},
        "p6": {"cq": 18, "description": "Alta calidad"},
        "p7": {"cq": 17, "description": "Máxima calidad"},
        "p8": {"cq": 15, "description": "Ultra calidad"},
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicializar configuración de encoder."""
        if config is None:
            config = {}

        # Modo de codificación
        self.encoder_mode = config.get(
            "encoder_mode", "auto"
        )  # auto, cpu, gpu_nvenc, gpu_amf, gpu_qsv

        # Configuración de video (CPU)
        self.video_preset = config.get("video_preset", "medium")
        self.video_crf = config.get("video_crf", 18)
        self.video_profile = config.get("video_profile", "high")
        self.video_tune = config.get("video_tune", "zerolatency")

        # Configuración de GPU
        self.gpu_preset = config.get("gpu_preset", "p3")

        # Configuración de audio
        self.audio_codec = config.get("audio_codec", "aac")
        self.audio_bitrate = config.get("audio_bitrate", "192k")
        self.audio_sample_rate = config.get("audio_sample_rate", 48000)

    def get_cpu_args(self) -> list:
        """Obtener argumentos FFmpeg para codificación CPU."""
        args = []

        # Preset y CRF
        if self.video_preset in self.CPU_PRESETS:
            crf = self.CPU_PRESETS[self.video_preset]["crf"]
        else:
            crf = self.video_crf

        args.extend(["-preset", self.video_preset, "-crf", str(crf)])

        # Perfil de video
        args.extend(["-profile:v", self.video_profile])

        # Tuning
        if self.video_tune and self.video_tune != "none":
            args.extend(["-tune", self.video_tune])

        return args

    def get_gpu_nvenc_args(self) -> list:
        """Obtener argumentos FFmpeg para GPU NVENC."""
        args = []

        # Preset y CQ
        preset_num = (
            int(self.gpu_preset[1])
            if len(self.gpu_preset) > 1 and self.gpu_preset[1].isdigit()
            else 3
        )
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

    def get_gpu_amf_args(self) -> list:
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

    def get_gpu_qsv_args(self) -> list:
        """Obtener argumentos FFmpeg para GPU QSV."""
        args = []

        args.extend(["-low_power", "1", "-async_depth", "1"])

        return args

    def get_audio_args(self) -> list:
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

    def to_dict(self) -> Dict[str, Any]:
        """Convertir configuración a diccionario."""
        return {
            "encoder_mode": self.encoder_mode,
            "video_preset": self.video_preset,
            "video_crf": self.video_crf,
            "video_profile": self.video_profile,
            "video_tune": self.video_tune,
            "gpu_preset": self.gpu_preset,
            "audio_codec": self.audio_codec,
            "audio_bitrate": self.audio_bitrate,
            "audio_sample_rate": self.audio_sample_rate,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "EncoderConfig":
        """Crear configuración desde diccionario."""
        return cls(config_dict)
