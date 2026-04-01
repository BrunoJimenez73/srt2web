"""
Audio Mixer Module — combines original audio with synthetic dubbing.

Provides audio ducking (lowers original audio volume) when TTS is active,
producing a final mixed audio track using FFmpeg filters.

Key features:
- Precise duration matching: audio always matches expected duration
- Padding: adds silence if TTS is shorter
- Truncation: cuts audio if TTS is longer
- Duration validation: measures actual output duration
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

    CRITICAL: Ensures output audio duration exactly matches expected duration
    to prevent drift accumulation across chunks.
    """

    def __init__(self, config: Optional[dict] = None, output_dir: str = "./output"):
        self._ffmpeg_path: Optional[str] = None
        self._output_dir = output_dir
        self._mixer_dir = ""
        self._original_volume = 0.15  # 15% original volume (ducking)
        self._tts_volume = 1.0  # 100% TTS volume
        self._last_measured_duration = 0.0
        # Duration cache to avoid repeated ffprobe calls
        self._duration_cache: dict[str, float] = {}
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
        
        # Clear duration cache on start
        self._duration_cache.clear()

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
        Mix original audio with TTS dubbed audio using numpy (in-process, ~20ms).

        No FFmpeg subprocess needed — reads WAVs, mixes with numpy, writes WAV.
        Duration is exact by construction (no ffprobe verification needed).
        """
        import wave
        import numpy as np

        orig_audio = data.audio_chunk_path
        tts_audio = data.dubbed_audio_path

        if not orig_audio or not os.path.exists(orig_audio):
            return data

        # If no TTS audio, use original as-is
        if not tts_audio or not os.path.exists(tts_audio):
            logger.debug(f"[AudioMixer] No TTS audio for chunk {data.chunk_index}")
            data.mixed_audio_path = orig_audio
            # Measure duration from original
            with wave.open(orig_audio, "rb") as wf:
                data.duration = wf.getnframes() / wf.getframerate()
            return data

        mix_wav = os.path.join(self._mixer_dir, f"mix_{data.chunk_index:06d}.wav")
        expected_duration = getattr(data, "duration", None)
        if not expected_duration:
            with wave.open(orig_audio, "rb") as wf:
                expected_duration = wf.getnframes() / wf.getframerate()
        expected_duration = max(0.1, min(expected_duration, 60.0))

        try:
            # Read original audio (from audio_extractor: 16kHz, 16-bit, mono)
            with wave.open(orig_audio, "rb") as wf:
                orig_sr = wf.getframerate()
                orig_channels = wf.getnchannels()
                orig_raw = wf.readframes(wf.getnframes())
            orig_samples = np.frombuffer(orig_raw, dtype=np.int16).astype(np.float64)
            if orig_channels > 1:
                orig_samples = orig_samples.reshape(-1, orig_channels).mean(axis=1)

            # Read TTS audio (from Piper: 22050Hz, 16-bit, mono)
            with wave.open(tts_audio, "rb") as wf:
                tts_sr = wf.getframerate()
                tts_raw = wf.readframes(wf.getnframes())
            tts_samples = np.frombuffer(tts_raw, dtype=np.int16).astype(np.float64)

            # Resample TTS to match original sample rate if needed
            if tts_sr != orig_sr:
                tts_indices = np.linspace(0, len(tts_samples) - 1, int(len(tts_samples) * orig_sr / tts_sr))
                tts_samples = np.interp(tts_indices, np.arange(len(tts_samples)), tts_samples)

            # Target length in samples
            target_samples = int(expected_duration * orig_sr)

            # Pad or trim original to expected duration
            if len(orig_samples) < target_samples:
                orig_samples = np.pad(orig_samples, (0, target_samples - len(orig_samples)))
            else:
                orig_samples = orig_samples[:target_samples]

            # Pad or trim TTS to expected duration
            if len(tts_samples) < target_samples:
                tts_samples = np.pad(tts_samples, (0, target_samples - len(tts_samples)))
            else:
                tts_samples = tts_samples[:target_samples]

            # Mix: apply volumes and add
            mixed = (orig_samples * self._original_volume + tts_samples * self._tts_volume)
            mixed = np.clip(mixed, -32768, 32767).astype(np.int16)

            # Write output WAV
            with wave.open(mix_wav, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(orig_sr)
                wf.writeframes(mixed.tobytes())

            actual_duration = len(mixed) / orig_sr
            data.duration = actual_duration
            data.mixed_audio_path = mix_wav
            logger.debug(f"[AudioMixer] Numpy mix: {mix_wav} ({actual_duration:.3f}s)")

        except Exception as e:
            logger.error(f"[AudioMixer] Numpy mixing error: {e}", exc_info=True)
            data.mixed_audio_path = orig_audio

        return data

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using ffprobe with caching."""
        if not audio_path or not os.path.exists(audio_path):
            return 0.0

        # Check cache first
        mtime = os.path.getmtime(audio_path)
        cache_key = f"{audio_path}:{mtime}"
        if cache_key in self._duration_cache:
            return self._duration_cache[cache_key]

        try:
            ffmpeg_bin = self._ffmpeg_path or ensure_ffmpeg()
            # Use rsplit to replace only the filename, not the full path
            if sys.platform == "win32":
                ffprobe = ffmpeg_bin.rsplit(os.sep, 1)[0] + os.sep + "ffprobe.exe"
            else:
                ffprobe = ffmpeg_bin.rsplit("/", 1)[0] + "/ffprobe"
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
            duration = float(result.stdout.strip())
            
            # Cache the result (limit cache size)
            if len(self._duration_cache) > 100:
                self._duration_cache.clear()
            self._duration_cache[cache_key] = duration
            
            return duration
        except Exception as e:
            logger.debug(f"Duration query failed for {audio_path}: {e}")
            return 0.0

    def _cleanup_temp_file(self, file_path: str) -> None:
        """Safely remove temporary file."""
        if not file_path or not os.path.exists(file_path):
            return
        try:
            os.remove(file_path)
        except OSError:
            pass

    @property
    def last_measured_duration(self) -> float:
        """Get the last measured output duration."""
        return self._last_measured_duration
