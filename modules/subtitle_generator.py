"""
Subtitle Generator Module — creates WebVTT files.

Formats transcripts or translations into a rolling WebVTT file
that can be displayed in the HLS video player.
"""

import os
import logging
import threading
from typing import Optional

from core.module_base import BaseModule, PipelineData, ModuleState

logger = logging.getLogger("srt2web.module.subtitle_generator")


class SubtitleGenerator(BaseModule):
    """
    Generates WebVTT subtitles synchronized with the video segments.
    Maintains a rolling subtitle file.
    """

    def __init__(self, config: Optional[dict] = None, output_dir: str = "./output"):
        self._output_dir = output_dir
        self._format = "webvtt"
        self._use_translated = True
        self._subtitles_dir = ""
        self._vtt_path = ""
        self._chunk_duration = 4
        self._lock = threading.Lock()
        
        # Keep track of recent subtitle text to avoid duplicates
        self._history = []
        self._max_history = 10
        super().__init__("subtitle_generator", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._use_translated = config.get("use_translated", self._use_translated)
        self._format = config.get("format", self._format)
        self._chunk_duration = config.get("chunk_duration", 4)

    def start(self) -> None:
        """Initialize subtitle files."""
        self._state = ModuleState.STARTING
        
        self._subtitles_dir = os.path.join(self._output_dir, "hls")
        os.makedirs(self._subtitles_dir, exist_ok=True)
        
        self._vtt_path = os.path.join(self._subtitles_dir, "subs.vtt")
        
        # Reset file with WebVTT header
        with self._lock:
            try:
                with open(self._vtt_path, "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n")
            except Exception as e:
                logger.error(f"Failed to initialize VTT: {e}")
                
        self._history = []
        self._state = ModuleState.RUNNING
        logger.info(f"SubtitleGenerator ready. Format: {self._format}, Output: {self._vtt_path}")

    def stop(self) -> None:
        self._state = ModuleState.IDLE

    def _format_timestamp(self, seconds: float, format_type: str = "vtt") -> str:
        """Convert float seconds to VTT (HH:MM:SS.mmm) or SRT (HH:MM:SS,mmm) timestamp."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        
        if format_type == "srt":
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Append new text to the WebVTT file and create a per-chunk SRT for burn-in.
        """
        text = data.translated_text if self._use_translated else data.transcript
        
        if not text:
            data.subtitles_path = self._vtt_path
            return data

        duration = getattr(data, 'duration', None) or self._chunk_duration
        if not duration or duration <= 0:
            duration = 4.0
        
        chunk_start_time = data.chunk_index * duration
        
        # Determine segments to use
        segments = []
        if self._use_translated and data.translated_segments:
            segments = data.translated_segments
        elif not self._use_translated and data.transcript_segments:
            segments = data.transcript_segments
        
        if not segments and text:
            segments = [{"start": 0.0, "end": duration * 0.9, "text": text}]
            
        # 1. Update rolling VTT for the HLS player (absolute timing)
        try:
            with self._lock:
                with open(self._vtt_path, "a", encoding="utf-8") as f:
                    for seg in segments:
                        abs_start = chunk_start_time + seg.get("start", 0)
                        abs_end = chunk_start_time + seg.get("end", duration)
                        
                        start_str = self._format_timestamp(abs_start, "vtt")
                        end_str = self._format_timestamp(abs_end, "vtt")
                        
                        clean_text = seg.get("text", "").replace("\n", " ").strip()
                        if clean_text:
                            f.write(f"{start_str} --> {end_str}\n")
                            f.write(f"{clean_text}\n\n")
                            # Provide feedback in the log
                            logger.info(f"[SUB] {clean_text}")
                            
            data.subtitles_path = self._vtt_path
        except Exception as e:
            logger.error(f"Error writing global VTT: {e}")

        # 2. Create per-chunk SRT for Video Muxer burn-in
        chunk_srt_path = os.path.join(self._subtitles_dir, f"chunk_{data.chunk_index:06d}.srt")
        try:
            with open(chunk_srt_path, "w", encoding="utf-8") as f:
                for i, seg in enumerate(segments):
                    start_str = self._format_timestamp(seg.get("start", 0), "srt")
                    end_str = self._format_timestamp(seg.get("end", duration), "srt")
                    clean_text = seg.get("text", "").replace("\n", " ").strip()
                    if clean_text:
                        f.write(f"{i+1}\n")
                        f.write(f"{start_str} --> {end_str}\n")
                        f.write(f"{clean_text}\n\n")
            
            if self._format == "srt":
                data.subtitles_path = chunk_srt_path
            
        except Exception as e:
            logger.error(f"Error writing chunk SRT: {e}")

        return data
