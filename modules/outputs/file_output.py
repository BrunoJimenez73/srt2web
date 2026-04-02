"""
File Output - Saves processed chunks to files.

Saves video, audio, and subtitle files to the output directory.
Useful for archiving or further processing.
"""

import os
import shutil
import logging
from typing import Optional

from core.module_base import PipelineData
from modules.outputs.base import BaseOutput

logger = logging.getLogger("srt2web.output.file")


class FileOutput(BaseOutput):
    """
    Saves processed chunks as files in the output directory.

    Creates organized structure:
    - video/chunk_000001.mp4
    - audio/chunk_000001.wav
    - subtitles/chunk_000001.vtt
    """

    def __init__(self, config: Optional[dict] = None):
        super().__init__("file", config or {})
        self._video_dir = ""
        self._audio_dir = ""
        self._subtitle_dir = ""
        self._counter = 0
        self._save_video = True
        self._save_audio = True
        self._save_subtitles = True

    def configure(self, config: dict) -> None:
        """Apply configuration."""
        super().configure(config)
        self._save_video = config.get("save_video", True)
        self._save_audio = config.get("save_audio", True)
        self._save_subtitles = config.get("save_subtitles", True)

    def start(self) -> None:
        """Initialize output directories."""
        base_dir = self._ensure_output_dir()
        
        self._video_dir = os.path.join(base_dir, "video")
        self._audio_dir = os.path.join(base_dir, "audio")
        self._subtitle_dir = os.path.join(base_dir, "subtitles")
        
        os.makedirs(self._video_dir, exist_ok=True)
        os.makedirs(self._audio_dir, exist_ok=True)
        os.makedirs(self._subtitle_dir, exist_ok=True)
        
        self._counter = 0
        logger.info(f"File output started: {base_dir}")

    def stop(self) -> None:
        """Cleanup if needed."""
        logger.info(f"File output stopped. Saved {self._counter} chunks.")

    def write(self, data: PipelineData) -> None:
        """
        Save chunk data to files.
        
        Args:
            data: PipelineData with paths to processed files
        """
        chunk_idx = data.chunk_index
        
        # Save video if available
        if self._save_video and data.video_chunk_path and os.path.exists(data.video_chunk_path):
            dest = os.path.join(self._video_dir, f"chunk_{chunk_idx:06d}.mp4")
            try:
                shutil.copy2(data.video_chunk_path, dest)
                logger.debug(f"Saved video: {dest}")
            except Exception as e:
                logger.error(f"Failed to save video: {e}")
        
        # Save mixed audio if available
        if self._save_audio and data.mixed_audio_path and os.path.exists(data.mixed_audio_path):
            dest = os.path.join(self._audio_dir, f"chunk_{chunk_idx:06d}.wav")
            try:
                shutil.copy2(data.mixed_audio_path, dest)
                logger.debug(f"Saved audio: {dest}")
            except Exception as e:
                logger.error(f"Failed to save audio: {e}")
        
        # Save subtitles if available
        if self._save_subtitles and data.subtitles_path and os.path.exists(data.subtitles_path):
            dest = os.path.join(self._subtitle_dir, f"chunk_{chunk_idx:06d}.vtt")
            try:
                shutil.copy2(data.subtitles_path, dest)
                logger.debug(f"Saved subtitles: {dest}")
            except Exception as e:
                logger.error(f"Failed to save subtitles: {e}")
        
        self._counter += 1

    def get_stream_info(self) -> dict:
        """Get file output information."""
        return {
            "type": "file",
            "output_dir": self._output_dir,
            "chunks_saved": self._counter,
            "save_video": self._save_video,
            "save_audio": self._save_audio,
            "save_subtitles": self._save_subtitles,
        }


# Auto-register
def _register():
    """Auto-register this output module."""
    try:
        from core.io_factory import OutputFactory
        OutputFactory.register("file", FileOutput)
    except ImportError:
        pass

_register()