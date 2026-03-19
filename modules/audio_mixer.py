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
        self._original_volume = 0.15  # 15% original volume (ducking)
        self._tts_volume = 1.0  # 100% TTS volume
        super().__init__("audio_mixer", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._original_volume = float(
            config.get("original_volume", self._original_volume)
        )
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
        logger.info(
            f"AudioMixer ready with volumes orig={self._original_volume}, tts={self._tts_volume}"
        )

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
        TTS audio is padded to match original duration to prevent sync issues.
        """
        orig_audio = data.audio_chunk_path
        original_tts_audio = data.dubbed_audio_path
        tts_audio = original_tts_audio

        if not orig_audio or not os.path.exists(orig_audio):
            return data

        if not tts_audio or not os.path.exists(tts_audio):
            data.mixed_audio_path = orig_audio
            return data

        mix_wav = os.path.join(self._mixer_dir, f"mix_{data.chunk_index:06d}.wav")

        orig_duration = self._get_audio_duration(orig_audio)
        tts_duration = self._get_audio_duration(tts_audio)
        expected_duration = getattr(data, "duration", None) or orig_duration

        logger.debug(
            f"[AudioMixer] chunk={data.chunk_index}, orig_dur={orig_duration:.3f}s, "
            f"tts_dur={tts_duration:.3f}s, expected={expected_duration:.3f}s"
        )

        needs_padding = tts_duration < expected_duration - 0.1
        if needs_padding:
            padded_tts = self._pad_audio(tts_audio, expected_duration)
            if padded_tts:
                tts_audio = padded_tts
                logger.debug(
                    f"[AudioMixer] TTS padded from {tts_duration:.3f}s to {expected_duration:.3f}s"
                )

        filter_complex = (
            f"[0:a]volume={self._original_volume}[orig]; "
            f"[1:a]volume={self._tts_volume}[tts]; "
            f"[orig][tts]amix=inputs=2:duration=first"
        )

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-i",
            orig_audio,
            "-i",
            tts_audio,
            "-filter_complex",
            filter_complex,
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            "-threads",
            "4",
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
                try:
                    if tts_audio and tts_audio != original_tts_audio:
                        os.remove(tts_audio)
                    if original_tts_audio:
                        os.remove(original_tts_audio)
                except OSError:
                    pass

        except Exception as e:
            logger.error(f"FFmpeg audio mixing exception: {e}")

        return data

        if not tts_audio or not os.path.exists(tts_audio):
            data.mixed_audio_path = orig_audio
            return data

        mix_wav = os.path.join(self._mixer_dir, f"mix_{data.chunk_index:06d}.wav")

        orig_duration = self._get_audio_duration(orig_audio)
        tts_duration = self._get_audio_duration(tts_audio)
        expected_duration = getattr(data, "duration", None) or orig_duration

        logger.debug(
            f"[AudioMixer] chunk={data.chunk_index}, orig_dur={orig_duration:.3f}s, "
            f"tts_dur={tts_duration:.3f}s, expected={expected_duration:.3f}s"
        )

        if tts_duration < expected_duration - 0.1:
            padded_tts = self._pad_audio(tts_audio, expected_duration)
            if padded_tts:
                tts_audio = padded_tts
                logger.debug(
                    f"[AudioMixer] TTS padded from {tts_duration:.3f}s to {expected_duration:.3f}s"
                )

        filter_complex = (
            f"[0:a]volume={self._original_volume}[orig]; "
            f"[1:a]volume={self._tts_volume}[tts]; "
            f"[orig][tts]amix=inputs=2:duration=first"
        )

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-i",
            orig_audio,
            "-i",
            tts_audio,
            "-filter_complex",
            filter_complex,
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            "-threads",
            "4",
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
                try:
                    if tts_audio != data.dubbed_audio_path:
                        os.remove(tts_audio)
                    os.remove(data.dubbed_audio_path)
                except OSError:
                    pass

        except Exception as e:
            logger.error(f"FFmpeg audio mixing exception: {e}")

        return data

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using ffprobe."""
        try:
            ffmpeg_bin = self._ffmpeg_path or ensure_ffmpeg()
            ffprobe = ffmpeg_bin.replace("ffmpeg", "ffprobe")
            if not os.path.exists(ffprobe):
                ffprobe = "ffprobe"
            cmd = [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def _pad_audio(self, audio_path: str, target_duration: float) -> Optional[str]:
        """Pad audio with silence to reach target duration."""
        current_duration = self._get_audio_duration(audio_path)
        if current_duration <= 0:
            return None

        padding_needed = target_duration - current_duration
        if padding_needed <= 0:
            return audio_path

        padded_path = audio_path.replace(".wav", "_padded.wav")
        ffmpeg_bin = self._ffmpeg_path or ensure_ffmpeg()
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            audio_path,
            "-af",
            f"apad=whole_dur={target_duration:.3f}",
            "-t",
            f"{target_duration:.3f}",
            "-ar",
            "44100",
            "-ac",
            "2",
            padded_path,
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
            if result.returncode == 0 and os.path.exists(padded_path):
                return padded_path
        except Exception as e:
            logger.error(f"Audio padding error: {e}")

        return None
