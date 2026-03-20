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
        self._audio_offset_ms = 0  # Audio delay offset for sync
        self._tts_speed = 1.0  # TTS speed multiplier for scaling subtitles
        self._lock = threading.Lock()

        # Track cumulative time for sync - same as VideoMuxer
        self._cumulative_time = 0.0
        self._last_chunk_index = -1

        # Keep track of recent subtitle text to avoid duplicates
        self._history = []
        self._max_history = 10
        super().__init__("subtitle_generator", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._use_translated = config.get("use_translated", self._use_translated)
        self._format = config.get("format", self._format)
        self._chunk_duration = config.get("chunk_duration", 4)
        self._audio_offset_ms = config.get("audio_offset_ms", self._audio_offset_ms)
        self._tts_speed = float(config.get("tts_speed", 1.0))
        logger.debug(
            f"SubtitleGenerator configured: audio_offset_ms={self._audio_offset_ms}, tts_speed={self._tts_speed}"
        )

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

        # Reset cumulative time - same as VideoMuxer
        self._cumulative_time = 0.0
        self._last_chunk_index = -1
        self._history = []
        self._state = ModuleState.RUNNING
        logger.info(
            f"SubtitleGenerator ready. Format: {self._format}, Audio Offset: {self._audio_offset_ms}ms, Output: {self._vtt_path}"
        )

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

        # Get actual duration from data (from ffprobe), not assumed duration
        duration = getattr(data, "duration", None) or self._chunk_duration
        if not duration or duration <= 0:
            duration = 4.0

        # Calculate real TTS duration based on speed (if TTS is faster, audio is shorter)
        tts_speed = self._tts_speed if self._tts_speed > 0 else 1.0
        tts_scale_factor = 1.0 / tts_speed  # 1.0 for speed=1.0, 0.5 for speed=2.0

        # Use cumulative timing - same logic as VideoMuxer
        # Track which chunks we've already processed
        if data.chunk_index > self._last_chunk_index:
            # New chunk, add its scaled duration to cumulative time
            # Skip chunks we already processed (for resume case)
            if self._last_chunk_index >= 0:
                self._cumulative_time += duration * tts_scale_factor
            self._last_chunk_index = data.chunk_index
        elif data.chunk_index < self._last_chunk_index:
            # Resume case - recalculate from scratch with scaling
            self._cumulative_time = data.chunk_index * duration * tts_scale_factor
            self._last_chunk_index = data.chunk_index

        # chunk_start_time is the current cumulative time (matches VideoMuxer's offset_sec)
        chunk_start_time = self._cumulative_time

        logger.debug(
            f"[SubtitleGen] chunk={data.chunk_index}, duration={duration}, tts_speed={tts_speed}, chunk_start_time={chunk_start_time}"
        )

        # Determine segments to use
        segments = []
        if self._use_translated and data.translated_segments:
            segments = data.translated_segments
        elif not self._use_translated and data.transcript_segments:
            segments = data.transcript_segments

        if not segments and text:
            segments = [{"start": 0.0, "end": duration * 0.9, "text": text}]

        # Apply audio offset and TTS speed scaling to subtitle timing
        audio_offset_sec = self._audio_offset_ms / 1000.0

        # 1. Update rolling VTT for the HLS player (absolute timing)
        try:
            with self._lock:
                with open(self._vtt_path, "a", encoding="utf-8") as f:
                    for seg in segments:
                        # Apply TTS speed scaling to relative timestamps
                        scaled_start = seg.get("start", 0) * tts_scale_factor
                        scaled_end = seg.get("end", duration) * tts_scale_factor
                        # Apply audio offset to sync with delayed audio
                        abs_start = chunk_start_time + scaled_start + audio_offset_sec
                        abs_end = chunk_start_time + scaled_end + audio_offset_sec

                        start_str = self._format_timestamp(abs_start, "vtt")
                        end_str = self._format_timestamp(abs_end, "vtt")

                        clean_text = seg.get("text", "").replace("\n", " ").strip()
                        if clean_text:
                            # Ensure text is properly encoded as UTF-8
                            try:
                                # Convert to UTF-8 if not already
                                clean_text = clean_text.encode("utf-8").decode("utf-8")
                            except:
                                pass
                            f.write(f"{start_str} --> {end_str}\n")
                            f.write(f"{clean_text}\n\n")
                            logger.info(f"[SUB] {clean_text}")

            # Also log the file size for debugging
            file_size = os.path.getsize(self._vtt_path)
            logger.debug(f"VTT file size: {file_size} bytes")

            data.subtitles_path = self._vtt_path
        except Exception as e:
            logger.error(f"Error writing global VTT: {e}")

        # 2. Create per-chunk SRT for Video Muxer burn-in
        chunk_srt_path = os.path.join(
            self._subtitles_dir, f"chunk_{data.chunk_index:06d}.srt"
        )
        try:
            with open(chunk_srt_path, "w", encoding="utf-8") as f:
                for i, seg in enumerate(segments):
                    # Apply TTS speed scaling and audio offset for SRT timing
                    scaled_start = seg.get("start", 0) * tts_scale_factor
                    scaled_end = seg.get("end", duration) * tts_scale_factor
                    seg_start = scaled_start + audio_offset_sec
                    seg_end = scaled_end + audio_offset_sec
                    start_str = self._format_timestamp(seg_start, "srt")
                    end_str = self._format_timestamp(seg_end, "srt")
                    clean_text = seg.get("text", "").replace("\n", " ").strip()
                    if clean_text:
                        f.write(f"{i + 1}\n")
                        f.write(f"{start_str} --> {end_str}\n")
                        f.write(f"{clean_text}\n\n")

            if self._format == "srt":
                data.subtitles_path = chunk_srt_path

        except Exception as e:
            logger.error(f"Error writing chunk SRT: {e}")

        return data
