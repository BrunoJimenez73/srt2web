"""
Audio Extractor Module — extracts audio from MPEG-TS chunks.

Uses FFmpeg to extract a 24kHz mono WAV file from the video chunk,
matching the HLS output sample rate to avoid resampling artifacts.
Optimized for speed with GPU acceleration (NVDEC) when available.
"""

import contextlib
import logging
import subprocess
from pathlib import Path
from typing import Any

from core.ffmpeg_utils import check_gpu_support
from core.ffmpeg_wrapper import FFmpegModule
from core.module_base import ModuleState, PipelineData

logger = logging.getLogger("srt2web.module.audio_extractor")


class AudioExtractor(FFmpegModule):
    """
    Extracts the audio track from the incoming video chunk
    and converts it to a format suitable for speech recognition
    (24kHz, mono, PCM WAV), matching the HLS output sample rate.
    """

    def __init__(self, config: dict[str, Any] | None = None, output_dir: str = "./output", pool: Any = None) -> None:
        self._output_dir = Path(output_dir)
        self._audio_dir = Path()
        self._gpu_info = {"nvenc": False, "nvdec": False}
        super().__init__("audio_extractor", config, pool=pool)

    def configure(self, config: dict[str, Any]) -> None:
        super().configure(config)

    def start(self) -> None:
        """Initialize the audio extraction directory."""
        self._state = ModuleState.STARTING

        # Check GPU support for faster processing
        self._gpu_info = check_gpu_support(self.ffmpeg.ffmpeg_path)
        # Also check for NVDEC (decoder) support
        try:
            result = self.ffmpeg.run_command(["-decoders"], timeout=5)
            self._gpu_info["nvdec"] = "h264_cuvid" in result.stdout.lower()
        except Exception as e:
            # Non-critical: NVDEC check is best-effort
            self._gpu_info["nvdec"] = False
            logger.debug(f"Failed to check NVDEC support: {e}")

        # Create temporary audio directory
        self._audio_dir = Path(self._output_dir) / "temp_audio"
        self._audio_dir.mkdir(parents=True, exist_ok=True)

        self._state = ModuleState.RUNNING
        logger.info(f"AudioExtractor ready. Temp dir: {self._audio_dir}, GPU: {self._gpu_info}")

    def stop(self) -> None:
        """Cleanup temporary files."""
        self._state = ModuleState.STOPPING
        # Try to clean up the temporary directory
        try:
            for f in self._audio_dir.iterdir():
                if f.suffix == ".wav":
                    with contextlib.suppress(OSError):
                        f.unlink()
        except OSError:
            pass
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        input_path = data.video_chunk_path
        if not input_path or not Path(input_path).exists():
            return data

        wav_name = f"audio_{data.chunk_index:06d}.wav"
        output_path = str(self._audio_dir / wav_name)

        cmd = ["-y"]

        # Only use GPU for larger files; GPU context init overhead outweighs benefit for <10MB
        input_size = Path(input_path).stat().st_size if Path(input_path).exists() else 0
        if self._gpu_info.get("nvdec") and input_size > 10 * 1024 * 1024:
            cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])

        cmd.extend(
            [
                "-fflags",
                "+nobuffer",
                "-flags",
                "low_delay",
                "-probesize",
                "500000",
                "-analyzeduration",
                "200000",
                "-i",
                input_path,
                "-vn",
                "-map",
                "0:a:0?",
                "-ar",
                "24000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                "-f",
                "wav",
                output_path,
            ]
        )

        try:
            result = self.ffmpeg.run_command(cmd, timeout=5)
            if result.returncode != 0:
                logger.error(f"FFmpeg audio extraction error: {result.stderr[-500:]}")
                return data

            if Path(output_path).exists():
                data.audio_chunk_path = output_path
                self.logger.debug(f"Extracted audio for chunk {data.chunk_index}")

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg audio extraction timed out after 5s")
        except Exception as e:
            logger.error(f"FFmpeg audio extraction exception: {e}")

        return data
