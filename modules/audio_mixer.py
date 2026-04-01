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
        Mix data.audio_chunk_path (original) with data.dubbed_audio_path (TTS).

        CRITICAL: Output duration is ALWAYS exactly expected_duration to prevent drift.
        """
        # Debug: Check what's in data
        debug_path = os.path.join(self._mixer_dir, "debug.log")
        with open(debug_path, "a") as f:
            f.write(f"Chunk {data.chunk_index}: orig={data.audio_chunk_path}, tts={data.dubbed_audio_path}\n")
        
        orig_audio = data.audio_chunk_path
        tts_audio = data.dubbed_audio_path

        if not orig_audio or not os.path.exists(orig_audio):
            return data

        # If no TTS audio, use original audio (with optional volume adjustment)
        if not tts_audio or not os.path.exists(tts_audio):
            logger.warning(f"[AudioMixer] No TTS audio for chunk {data.chunk_index}: {tts_audio}")
            data.mixed_audio_path = orig_audio
            data.duration = self._get_audio_duration(orig_audio)
            return data

        mix_wav = os.path.join(self._mixer_dir, f"mix_{data.chunk_index:06d}.wav")
        expected_duration = getattr(data, "duration", None) or self._get_audio_duration(orig_audio)
        expected_duration = max(0.1, min(expected_duration, 60.0))

        # ──────────────────────────────────────────────────────────
        # SINGLE FFmpeg call: pad TTS + mix + enforce duration
        # Replaces 3 separate FFmpeg calls (_prepare_tts + mix + enforce)
        # ──────────────────────────────────────────────────────────
        filter_complex = (
            f"[1:a]apad=whole_dur={expected_duration:.3f},atrim=duration={expected_duration:.3f}[tts]; "
            f"[0:a]volume={self._original_volume}[orig]; "
            f"[tts]volume={self._tts_volume}[ttsv]; "
            f"[orig][ttsv]amix=inputs=2:duration=first,"
            f"atrim=duration={expected_duration:.3f},asetpts=PTS-STARTPTS"
        )

        cmd = [
            self._ffmpeg_path, "-y",
            "-i", orig_audio,
            "-i", tts_audio,
            "-filter_complex", filter_complex,
            "-ac", "2", "-ar", "44100",
            "-c:a", "pcm_s16le",
            "-threads", "4",
            "-loglevel", "error",
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
                logger.error(f"FFmpeg audio mix error: {result.stderr[-300:]}")
                data.mixed_audio_path = orig_audio
                return data

            if os.path.exists(mix_wav) and os.path.getsize(mix_wav) > 44:
                data.duration = expected_duration
                data.mixed_audio_path = mix_wav
                logger.debug(f"[AudioMixer] Created mix: {mix_wav}")
            else:
                logger.error(f"[AudioMixer] Mix file missing or empty: {mix_wav}")
                data.mixed_audio_path = orig_audio

        except Exception as e:
            logger.error(f"FFmpeg audio mixing exception: {e}")
            data.mixed_audio_path = orig_audio

        return data

        mix_wav = os.path.join(self._mixer_dir, f"mix_{data.chunk_index:06d}.wav")

        orig_duration = self._get_audio_duration(orig_audio)
        tts_duration = self._get_audio_duration(tts_audio)
        
        if orig_duration <= 0:
            logger.warning(f"[AudioMixer] Cannot get duration for orig: {orig_audio}")
        if tts_duration <= 0:
            logger.warning(f"[AudioMixer] Cannot get duration for tts: {tts_audio}")
        
        expected_duration = getattr(data, "duration", None) or orig_duration

        # Clamp expected duration to reasonable bounds
        expected_duration = max(0.1, min(expected_duration, 60.0))

        logger.debug(
            f"[AudioMixer] chunk={data.chunk_index}, orig_dur={orig_duration:.3f}s, "
            f"tts_dur={tts_duration:.3f}s, expected={expected_duration:.3f}s"
        )

        # Prepare TTS audio: pad or truncate to exact expected duration
        processed_tts = self._prepare_tts_audio(tts_audio, expected_duration)
        if not processed_tts:
            logger.warning("[AudioMixer] Failed to process TTS audio, using original")
            data.mixed_audio_path = orig_audio
            return data

        tts_audio = processed_tts

        # Mix original (ducked) with TTS using exact duration
        # Note: amix can reduce volume, so we apply volume filter after
        filter_complex = (
            f"[0:a]volume={self._original_volume}[orig]; "
            f"[1:a]volume={self._tts_volume}[tts]; "
            f"[orig][tts]amix=inputs=2:duration=first,"
            f"atrim=duration={expected_duration:.3f},asetpts=PTS-STARTPTS"
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
            # Debug: Write to file
            debug_path = os.path.join(self._mixer_dir, "debug.log")
            with open(debug_path, "a") as f:
                f.write(f"Chunk {data.chunk_index}: orig={orig_audio}, tts={tts_audio}, mix={mix_wav}\n")
            
            print(f"[DEBUG] AudioMixer: Running FFmpeg for chunk {data.chunk_index}")
            print(f"[DEBUG] AudioMixer: mix_wav path = {mix_wav}")
            print(f"[DEBUG] AudioMixer: orig_audio = {orig_audio}")
            print(f"[DEBUG] AudioMixer: tts_audio = {tts_audio}")
            print(f"[DEBUG] AudioMixer: FFmpeg cmd = {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            print(f"[DEBUG] AudioMixer: FFmpeg returncode = {result.returncode}")
            print(f"[DEBUG] AudioMixer: FFmpeg stdout length = {len(result.stdout)}")
            print(f"[DEBUG] AudioMixer: FFmpeg stderr length = {len(result.stderr)}")
            if result.returncode != 0:
                print(f"[DEBUG] AudioMixer: FFmpeg error: {result.stderr[-500:]}")
                logger.error(f"FFmpeg audio mix error: {result.stderr[-500:]}")
                data.mixed_audio_path = orig_audio
                return data

            print(f"[DEBUG] AudioMixer: Checking if mix_wav exists: {os.path.exists(mix_wav)}")
            if os.path.exists(mix_wav):
                print(f"[DEBUG] AudioMixer: mix_wav size = {os.path.getsize(mix_wav) if os.path.exists(mix_wav) else 0} bytes")
                # CRITICAL: Measure actual output duration
                actual_duration = self._get_audio_duration(mix_wav)

                # If actual duration differs from expected, trim/enforce it
                if abs(actual_duration - expected_duration) > 0.01:
                    logger.warning(
                        f"[AudioMixer] Duration mismatch: got {actual_duration:.3f}s, "
                        f"expected {expected_duration:.3f}s, enforcing..."
                    )
                    self._enforce_duration(mix_wav, expected_duration)
                    actual_duration = self._get_audio_duration(mix_wav)

                # Update data.duration with MEASURED duration (critical for sync)
                data.duration = actual_duration
                self._last_measured_duration = actual_duration

                logger.debug(
                    f"[AudioMixer] Output duration: {actual_duration:.3f}s "
                    f"(drift from original: {actual_duration - orig_duration:+.3f}s)"
                )

                data.mixed_audio_path = mix_wav

                # TEMPORARILY DISABLED: Cleanup to debug issue
                # self._cleanup_temp_file(tts_audio)
                # if data.dubbed_audio_path:
                #     self._cleanup_temp_file(data.dubbed_audio_path)
                
                logger.info(f"[AudioMixer] Created mix file: {mix_wav}")

        except Exception as e:
            logger.error(f"FFmpeg audio mixing exception: {e}")
            data.mixed_audio_path = orig_audio

        return data

    def _prepare_tts_audio(
        self, tts_audio: str, target_duration: float
    ) -> Optional[str]:
        """
        Prepare TTS audio to exactly match target duration.

        - Pads with silence if too short
        - Truncates if too long
        Returns path to processed audio, or None on failure.
        """
        current_duration = self._get_audio_duration(tts_audio)
        if current_duration <= 0:
            return None

        diff = target_duration - current_duration
        tolerance = 0.01  # 10ms tolerance

        # If within tolerance, no processing needed
        if abs(diff) <= tolerance:
            return tts_audio

        processed_path = tts_audio.replace(".wav", "_prep.wav")

        if diff > 0:
            # Need to pad: add silence
            return self._pad_audio(tts_audio, target_duration, processed_path)
        else:
            # Need to truncate: cut excess
            return self._truncate_audio(tts_audio, target_duration, processed_path)

    def _pad_audio(
        self, audio_path: str, target_duration: float, output_path: Optional[str] = None
    ) -> Optional[str]:
        """Pad audio with silence to reach target duration."""
        current_duration = self._get_audio_duration(audio_path)
        if current_duration <= 0:
            return None

        padding_needed = target_duration - current_duration
        if padding_needed <= 0:
            return audio_path

        if output_path is None:
            output_path = audio_path.replace(".wav", "_padded.wav")

        ffmpeg_bin = self._ffmpeg_path or ensure_ffmpeg()

        # Use apad filter for seamless padding, then trim to exact duration
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
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                logger.warning(f"Audio padding failed: {result.stderr[-200:]}")
        except Exception as e:
            logger.error(f"Audio padding error: {e}")

        return None

    def _truncate_audio(
        self, audio_path: str, target_duration: float, output_path: Optional[str] = None
    ) -> Optional[str]:
        """Truncate audio to target duration."""
        if output_path is None:
            output_path = audio_path.replace(".wav", "_trunc.wav")

        ffmpeg_bin = self._ffmpeg_path or ensure_ffmpeg()

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            audio_path,
            "-t",
            f"{target_duration:.3f}",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                logger.warning(f"Audio truncation failed: {result.stderr[-200:]}")
        except Exception as e:
            logger.error(f"Audio truncation error: {e}")

        return None

    def _enforce_duration(self, audio_path: str, target_duration: float) -> bool:
        """Force audio to exact duration using trim/pad."""
        temp_path = audio_path.replace(".wav", "_enforce.wav")

        ffmpeg_bin = self._ffmpeg_path or ensure_ffmpeg()

        # Trim or pad to exact duration
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            audio_path,
            "-af",
            f"apad=whole_dur={target_duration:.3f}",
            "-t",
            f"{target_duration:.3f}",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            temp_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            if result.returncode == 0 and os.path.exists(temp_path):
                # Replace original with enforced version
                os.replace(temp_path, audio_path)
                return True
        except Exception as e:
            logger.error(f"Duration enforcement error: {e}")

        return False

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
