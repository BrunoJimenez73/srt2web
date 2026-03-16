"""
Audio Mixer Module — combines original audio with synthetic dubbing.

Provides audio ducking (lowers original audio volume) when TTS is active,
producing a final mixed audio track using FFmpeg filters.
"""

import os
import sys
import logging
import subprocess
from typing import Optional

from core.module_base import BaseModule, PipelineData, ModuleState
from core.ffmpeg_utils import ensure_ffmpeg

logger = logging.getLogger("srt2web.module.audio_mixer")


class AudioMixer(BaseModule):
    """
    Mixes original extracted audio with TTS dubbed audio.
    Applies volume attributes from configuration.
    """

    def __init__(self, config: Optional[dict] = None, output_dir: str = "./output"):
        self._ffmpeg_path: Optional[str] = None
        self._output_dir = output_dir
        self._mixer_dir = ""
        self._original_volume = 0.15 # 15% original volume (ducking)
        self._tts_volume = 1.0       # 100% TTS volume
        super().__init__("audio_mixer", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._original_volume = float(config.get("original_volume", self._original_volume))
        self._tts_volume = float(config.get("tts_volume", self._tts_volume))

    def start(self) -> None:
        """Initialize directory."""
        self._state = ModuleState.STARTING
        self._ffmpeg_path = ensure_ffmpeg()

        self._mixer_dir = os.path.join(self._output_dir, "temp_mix")
        os.makedirs(self._mixer_dir, exist_ok=True)
        
        # Clean old files
        for f in os.listdir(self._mixer_dir):
            if f.endswith(".wav"):
                try:
                    os.remove(os.path.join(self._mixer_dir, f))
                except OSError:
                    pass

        self._state = ModuleState.RUNNING
        logger.info(f"AudioMixer ready with volumes orig={self._original_volume}, tts={self._tts_volume}")

    def stop(self) -> None:
        """Cleanup temporary files."""
        self._state = ModuleState.STOPPING
        try:
            for f in os.listdir(self._mixer_dir):
                if f.endswith(".wav"):
                    os.remove(os.path.join(self._mixer_dir, f))
        except OSError:
            pass
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Mix data.audio_chunk_path (original) with data.dubbed_audio_path (TTS).
        """
        orig_audio = data.audio_chunk_path
        tts_audio = data.dubbed_audio_path
        
        # If no original audio, we can't mix it
        if not orig_audio or not os.path.exists(orig_audio):
            return data

        # If no TTS generated for this chunk, just use original
        if not tts_audio or not os.path.exists(tts_audio):
            data.mixed_audio_path = orig_audio
            return data

        # Output WAV
        mix_wav = os.path.join(self._mixer_dir, f"mix_{data.chunk_index:06d}.wav")

        # FFmpeg filter complex:
        # [0:a]volume=0.15[orig]; [1:a]volume=1.0[tts]; [orig][tts]amix=inputs=2:duration=longest[out]
        
        filter_complex = (
            f"[0:a]volume={self._original_volume}[orig]; "
            f"[1:a]volume={self._tts_volume}[tts]; "
            f"[orig][tts]amix=inputs=2:duration=longest"
        )

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-i", orig_audio,
            "-i", tts_audio,
            "-filter_complex", filter_complex,
            "-ac", "2",                 # Output stereo
            "-ar", "44100",             # Standard audio rate
            "-c:a", "pcm_s16le",
            mix_wav,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            if result.returncode != 0:
                logger.error(f"FFmpeg audio mix error: {result.stderr[-500:]}")
                return data
                
            if os.path.exists(mix_wav):
                data.mixed_audio_path = mix_wav
                
                # Cleanup older chunks to save space
                try:
                    os.remove(tts_audio)
                except OSError:
                    pass

        except Exception as e:
            logger.error(f"FFmpeg audio mixing exception: {e}")

        return data
