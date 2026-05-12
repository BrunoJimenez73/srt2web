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

import logging
from pathlib import Path
from typing import Optional

from core.ffmpeg_utils import ensure_ffmpeg
from core.module_base import BaseModule, ModuleState, PipelineData

logger = logging.getLogger("srt2web.module.audio_mixer")


class AudioMixer(BaseModule):
    """
    Mixes original extracted audio with TTS dubbed audio.
    Applies volume attributes from configuration.

    CRITICAL: Ensures output audio duration exactly matches expected duration
    to prevent drift accumulation across chunks.
    """

    def __init__(self, config: Optional[dict] = None, output_dir: str = "./output") -> None:
        self._ffmpeg_path: Optional[str] = None
        self._output_dir = Path(output_dir)
        self._mixer_dir = Path()
        self._original_volume = 0.15  # 15% original volume (ducking)
        self._tts_volume = 1.0  # 100% TTS volume
        self._last_measured_duration = 0.0
        # Duration cache to avoid repeated ffprobe calls
        self._duration_cache: dict[str, float] = {}
        super().__init__("audio_mixer", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._original_volume = float(config.get("original_volume", self._original_volume))
        self._tts_volume = float(config.get("tts_volume", self._tts_volume))

    def start(self) -> None:
        """Initialize directory."""
        self._state = ModuleState.STARTING
        self._ffmpeg_path = ensure_ffmpeg()

        self._mixer_dir = Path(self._output_dir) / "temp_mix"
        self._mixer_dir.mkdir(parents=True, exist_ok=True)

        # Clear duration cache on start
        self._duration_cache.clear()

        # Clean old files
        for f in self._mixer_dir.iterdir():
            if f.suffix == ".wav":
                try:
                    f.unlink()
                except OSError:
                    pass

        self._state = ModuleState.RUNNING
        logger.info(f"AudioMixer ready with volumes orig={self._original_volume}, tts={self._tts_volume}")

    def stop(self) -> None:
        """Cleanup temporary files."""
        self._state = ModuleState.STOPPING
        try:
            for f in self._mixer_dir.iterdir():
                if f.suffix == ".wav":
                    f.unlink()
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

        if not orig_audio or not Path(orig_audio).exists():
            return data

        # If no TTS audio, use original as-is
        if not tts_audio or not Path(tts_audio).exists():
            logger.debug(f"[AudioMixer] No TTS audio for chunk {data.chunk_index}")
            data.mixed_audio_path = orig_audio
            if not getattr(data, "duration", None):
                with wave.open(str(orig_audio), "rb") as wf:
                    data.duration = wf.getnframes() / wf.getframerate()
            return data

        mix_wav = self._mixer_dir / f"mix_{data.chunk_index:06d}.wav"
        expected_duration = getattr(data, "duration", None)
        if not expected_duration:
            with wave.open(orig_audio, "rb") as wf:
                expected_duration = wf.getnframes() / wf.getframerate()
        expected_duration = max(0.1, min(expected_duration, 60.0))

        try:
            # Read original audio (from audio_extractor: 16kHz, 16-bit, mono)
            with wave.open(str(orig_audio), "rb") as wf:
                orig_sr = wf.getframerate()
                orig_channels = wf.getnchannels()
                orig_raw = wf.readframes(wf.getnframes())
            orig_samples = np.frombuffer(orig_raw, dtype=np.int16).astype(np.float64)
            if orig_channels > 1:
                orig_samples = orig_samples.reshape(-1, orig_channels).mean(axis=1)

            # Read TTS audio (from Piper: 22050Hz, 16-bit, mono)
            with wave.open(str(tts_audio), "rb") as wf:
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
            mixed = orig_samples * self._original_volume + tts_samples * self._tts_volume
            mixed = np.clip(mixed, -32768, 32767).astype(np.int16)

            # Write output WAV
            with wave.open(str(mix_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(orig_sr)
                wf.writeframes(mixed.tobytes())

            actual_duration = len(mixed) / orig_sr
            if not getattr(data, "duration", None):
                data.duration = actual_duration
            data.mixed_audio_path = mix_wav
            logger.debug(f"[AudioMixer] Numpy mix: {mix_wav} ({actual_duration:.3f}s)")

        except Exception as e:
            logger.error(f"[AudioMixer] Numpy mixing error: {e}", exc_info=True)
            data.mixed_audio_path = orig_audio

        return data

    @property
    def last_measured_duration(self) -> float:
        """Get the last measured output duration."""
        return self._last_measured_duration
