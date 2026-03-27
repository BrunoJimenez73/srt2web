"""
Audio Extractor Module — extracts audio from MPEG-TS chunks.

Uses FFmpeg to extract a 16kHz mono WAV file from the video chunk,
which is the required format for Whisper transcription.
"""

import os
import sys
import logging
import subprocess
from typing import Optional

from core.module_base import BaseModule, PipelineData, ModuleState
from core.ffmpeg_utils import ensure_ffmpeg

logger = logging.getLogger("srt2web.module.audio_extractor")


class AudioExtractor(BaseModule):
    """
    Extracts the audio track from the incoming video chunk
    and converts it to a format suitable for speech recognition
    (16kHz, mono, PCM WAV).
    """

    def __init__(self, config: Optional[dict] = None, output_dir: str = "./output"):
        self._ffmpeg_path: Optional[str] = None
        self._output_dir = output_dir
        self._audio_dir = ""
        super().__init__("audio_extractor", config)

    def configure(self, config: dict) -> None:
        super().configure(config)

    def start(self) -> None:
        """Initialize the audio extraction directory."""
        self._state = ModuleState.STARTING
        self._ffmpeg_path = ensure_ffmpeg()

        # Create temporary audio directory
        self._audio_dir = os.path.join(self._output_dir, "temp_audio")
        os.makedirs(self._audio_dir, exist_ok=True)

        self._state = ModuleState.RUNNING
        logger.info(f"AudioExtractor ready. Temp dir: {self._audio_dir}")

    def stop(self) -> None:
        """Cleanup temporary files."""
        self._state = ModuleState.STOPPING
        # Try to clean up the temporary directory
        try:
            for f in os.listdir(self._audio_dir):
                if f.endswith(".wav"):
                    try:
                        os.remove(os.path.join(self._audio_dir, f))
                    except OSError:
                        pass
        except OSError:
            pass
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Extract audio from data.video_chunk_path.
        Sets data.audio_chunk_path to the resulting WAV file.
        """
        input_path = data.video_chunk_path
        if not input_path or not os.path.exists(input_path):
            return data

        # Output WAV filename
        wav_name = f"audio_{data.chunk_index:06d}.wav"
        output_path = os.path.join(self._audio_dir, wav_name)

        # FFmpeg command: extract audio, 16kHz, mono, 16-bit PCM
        cmd = [
            self._ffmpeg_path,
            "-y",
            "-i", input_path,
            "-vn",                      # No video
            "-ar", "16000",             # 16kHz sample rate
            "-ac", "1",                 # Mono
            "-c:a", "pcm_s16le",        # 16-bit PCM
            "-threads", "4",            # Limit threads for CPU efficiency
            "-f", "wav",
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            if result.returncode != 0:
                logger.error(f"FFmpeg audio extraction error: {result.stderr[-500:]}")
                return data
                
            if os.path.exists(output_path):
                data.audio_chunk_path = output_path
                self.logger.debug(f"Extracted audio for chunk {data.chunk_index}")

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg audio extraction timed out")
        except Exception as e:
            logger.error(f"FFmpeg audio extraction exception: {e}")

        return data
