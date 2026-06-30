"""
Subtitle Generator Module — creates WebVTT files.

Formats transcripts or translations into a rolling WebVTT file
that can be displayed in the HLS video player.

CRITICAL: Uses data.cumulative_duration from PipelineData for accurate sync,
not internal tracking, to prevent drift from VideoMuxer.
"""

import contextlib
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from core.cache import LRUCache
from core.module_base import BaseModule, ModuleState, PipelineData
from core.subtitle_sync_monitor import SubtitleSyncMonitor

from ._delay import DelayCompensator
from ._hls_manager import HLSManager
from ._types import HLSFragment, SubtitleEntry
from ._vtt_buffer import VTTBuffer

logger = logging.getLogger("srt2web.module.subtitle_generator")


class SubtitleGenerator(BaseModule):
    """
    Generates WebVTT subtitles synchronized with the video segments.
    Maintains a rolling subtitle file.

    CRITICAL: Uses data.cumulative_duration from PipelineData for synchronization
    to prevent drift accumulation across modules.
    """

    def __init__(self, config: dict[str, Any] | None = None, output_dir: str = "./output") -> None:
        self._output_dir = output_dir
        self._format = "webvtt"
        self._use_translated = True
        self._dual_track = False
        self._vtt_alt_path = Path()
        self._chunk_duration = 5
        self._lock = threading.Lock()
        self._previous_chunk_duration = 5

        self._last_chunk_index = -1
        self._last_cumulative = 0.0

        self._vtt_buffer = VTTBuffer(
            max_entries=2000,
            max_age_seconds=7200.0,
        )
        self._hls_manager = HLSManager(list_size=10)
        self._delay = DelayCompensator()

        self._subtitles_dir: Path = Path()
        self._vtt_path: Path = Path()

        self.timestamp_format_cache = LRUCache(maxsize=500, ttl_seconds=60)
        self._in_configure = False

        super().__init__("subtitle_generator", config)

    def configure(self, config: dict[str, Any]) -> None:
        super().configure(config)
        self._use_translated = config.get("use_translated", self._use_translated)
        self._format = config.get("format", self._format)
        self._dual_track = config.get("dual_track", False)
        new_chunk_duration = config.get("chunk_duration", self._chunk_duration)

        if new_chunk_duration != self._previous_chunk_duration and hasattr(self, "_vtt_buffer"):
            logger.info(
                f"[SubtitleGen] chunk_duration changed: {self._previous_chunk_duration}s → {new_chunk_duration}s"
            )
            self._last_chunk_index = -1
            self._last_cumulative = 0.0
            with self._lock:
                self._vtt_buffer.clear()
                self._hls_manager.clear()
            if self._vtt_path and str(self._vtt_path) != ".":
                self._vtt_buffer.rewrite()
            if self._hls_manager.playlist_path and str(self._hls_manager.playlist_path) != ".":
                self._hls_manager.rewrite_playlist()

        self._chunk_duration = new_chunk_duration
        self._previous_chunk_duration = new_chunk_duration
        self._hls_manager.configure(int(config.get("hls_list_size", 10)))
        self._delay.configure(
            smoothing_factor=config.get("smoothing_factor"),
            dead_zone=config.get("dead_zone"),
            max_delay_increase=config.get("max_delay_increase"),
        )
        self._vtt_buffer.configure(
            max_entries=config.get("max_vtt_entries", 1000),
            max_age_seconds=config.get("vtt_max_age_seconds", 7200.0),
        )

    def start(self) -> None:
        """Initialize subtitle files."""
        self._state = ModuleState.STARTING
        self._delay.reset()

        self._subtitles_dir = Path(self._output_dir) / "subtitles"
        os.makedirs(self._subtitles_dir, exist_ok=True)
        self._subtitles_dir.mkdir(parents=True, exist_ok=True)

        self._vtt_path = self._subtitles_dir / "subs.vtt"
        vtt_open_path = os.path.join(self._output_dir, "subtitles", "subs.vtt")
        self._vtt_alt_path = self._subtitles_dir / "subs_original.vtt"

        hls_playlist_path = self._subtitles_dir / "subs.m3u8"
        self._hls_manager.set_paths(hls_playlist_path, self._subtitles_dir)
        self._vtt_buffer.set_paths(self._subtitles_dir, self._vtt_path)

        for old_chunk in Path(self._output_dir, "subtitles").glob("chunk_*.srt"):
            with contextlib.suppress(OSError):
                old_chunk.unlink()
        for old_vtt in Path(self._output_dir, "subtitles").glob("subs_seg_*.vtt"):
            with contextlib.suppress(OSError):
                old_vtt.unlink()

        self._hls_manager.rewrite_playlist()

        with self._lock:
            try:
                with open(vtt_open_path, "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n")
            except Exception as e:
                logger.error(f"Failed to initialize VTT {vtt_open_path}: {e}")

            if self._dual_track:
                alt_path = str(self._vtt_alt_path)
                try:
                    with open(alt_path, "w", encoding="utf-8") as f:
                        f.write("WEBVTT\n\n")
                except Exception as e:
                    logger.error(f"Failed to initialize alt VTT: {e}")

        self._last_chunk_index = -1
        self._last_cumulative = 0.0
        self._vtt_buffer.clear()
        self._hls_manager.clear()
        self._state = ModuleState.RUNNING
        logger.info(
            f"SubtitleGenerator ready. Format: {self._format}, "
            f"Output: {self._vtt_path}, HLS playlist: {hls_playlist_path}"
        )

    def stop(self) -> None:
        self._state = ModuleState.IDLE

    def set_drift_monitor(self, monitor: SubtitleSyncMonitor | None) -> None:
        self._delay.set_drift_monitor(monitor)

    def get_playlist_path(self) -> Path | None:
        hls_path = self._hls_manager.playlist_path
        if not hls_path or str(hls_path) == ".":
            return None
        return hls_path

    def get_playlist_url(self) -> str:
        return "/subtitles/subs.m3u8"

    # ------------------------------------------------------------------ #
    # Backward-compatible shim properties (tests access internals)
    # ------------------------------------------------------------------ #

    @property
    def _hls_fragments(self) -> list[HLSFragment]:
        return self._hls_manager._fragments

    @_hls_fragments.setter
    def _hls_fragments(self, value: list[HLSFragment]) -> None:
        self._hls_manager._fragments = value

    @property
    def _hls_playlist_path(self) -> Path:
        return self._hls_manager.playlist_path

    @_hls_playlist_path.setter
    def _hls_playlist_path(self, value: Path) -> None:
        self._hls_manager.set_paths(value, self._subtitles_dir)

    @property
    def _hls_list_size(self) -> int:
        return self._hls_manager._list_size

    @_hls_list_size.setter
    def _hls_list_size(self, value: int) -> None:
        self._hls_manager._list_size = value

    @property
    def _vtt_entries(self) -> list[SubtitleEntry]:
        return self._vtt_buffer._entries

    @_vtt_entries.setter
    def _vtt_entries(self, value: list[SubtitleEntry]) -> None:
        self._vtt_buffer._entries = value

    @property
    def _max_vtt_entries(self) -> int:
        return self._vtt_buffer._max_vtt_entries

    @_max_vtt_entries.setter
    def _max_vtt_entries(self, value: int) -> None:
        self._vtt_buffer._max_vtt_entries = value

    @property
    def _vtt_max_age_seconds(self) -> float:
        return self._vtt_buffer._vtt_max_age_seconds

    @_vtt_max_age_seconds.setter
    def _vtt_max_age_seconds(self, value: float) -> None:
        self._vtt_buffer._vtt_max_age_seconds = value

    @property
    def _drift_monitor(self) -> SubtitleSyncMonitor | None:
        return self._delay._drift_monitor

    @_drift_monitor.setter
    def _drift_monitor(self, value: SubtitleSyncMonitor | None) -> None:
        self._delay._drift_monitor = value

    @property
    def _pipeline_start_wall(self) -> float:
        return self._delay._pipeline_start_wall

    @_pipeline_start_wall.setter
    def _pipeline_start_wall(self, value: float) -> None:
        self._delay._pipeline_start_wall = value

    @property
    def _pipeline_delay_smoothed(self) -> float:
        return self._delay._pipeline_delay_smoothed

    @_pipeline_delay_smoothed.setter
    def _pipeline_delay_smoothed(self, value: float) -> None:
        self._delay._pipeline_delay_smoothed = value

    def _write_hls_fragment(
        self, chunk_index: int, segments: list[dict[str, Any]], duration: float, abs_start: float = 0.0
    ) -> str:
        self._hls_manager.set_paths(self._hls_manager._playlist_path, Path(self._subtitles_dir))
        return self._hls_manager.write_fragment(chunk_index, segments, duration, abs_start)

    def _rewrite_hls_playlist(self) -> None:
        self._hls_manager.set_paths(self._hls_manager._playlist_path, Path(self._subtitles_dir))
        self._hls_manager.rewrite_playlist()

    def _rewrite_vtt_file(self) -> None:
        self._vtt_buffer.set_paths(Path(self._subtitles_dir), Path(self._vtt_path))
        self._vtt_buffer.rewrite()

    def _trim_vtt_entries(self) -> None:
        self._vtt_buffer.trim()

    def _do_process(self, data: PipelineData) -> PipelineData:
        """Append new text to the WebVTT file and create a per-chunk SRT for burn-in."""
        text = data.translated_text if self._use_translated else data.transcript

        if not text:
            data.subtitles_path = str(self._vtt_path)
            return data

        data_duration = getattr(data, "duration", None)
        duration = data_duration if data_duration and data_duration > 0 else self._chunk_duration

        chunk_start_time = getattr(data, "cumulative_duration", 0.0)

        # Pipeline delay compensation
        pipeline_delay = self._delay.estimate_delay(chunk_start_time)
        shifted_start = chunk_start_time + pipeline_delay

        # Drift correction
        wall_elapsed = time.time() - self._delay._pipeline_start_wall
        shifted_start = self._delay.apply_drift_correction(shifted_start, wall_elapsed)

        # Validate cumulative_duration is monotonically increasing
        if chunk_start_time < self._last_cumulative:
            logger.warning(
                f"[SubtitleGen] Cumulative duration decreased! "
                f"{chunk_start_time:.3f} < {self._last_cumulative:.3f} - "
                f"using last cumulative to prevent drift"
            )
            chunk_start_time = self._last_cumulative

        # Handle pause loop / duplicate chunks
        is_loop = data.metadata.get("is_loop", False)
        if is_loop:
            logger.debug(
                f"[SubtitleGen] Pause loop detected - chunk {data.chunk_index} replaying, skipping subtitle re-add"
            )
            data.subtitles_path = str(self._vtt_path)
            return data
        elif data.chunk_index == self._last_chunk_index and self._last_chunk_index >= 0:
            data.subtitles_path = str(self._vtt_path)
            return data
        elif data.chunk_index != self._last_chunk_index + 1 and self._last_chunk_index >= 0:
            logger.warning(
                f"[SubtitleGen] Chunk sequence break: expected {self._last_chunk_index + 1}, got {data.chunk_index}"
            )

        if chunk_start_time <= self._last_cumulative and self._last_cumulative > 0:
            logger.warning(
                f"[SubtitleGen] Cumulative duration not increasing: "
                f"last={self._last_cumulative:.3f}, current={chunk_start_time:.3f}"
            )

        self._last_chunk_index = data.chunk_index
        self._last_cumulative = chunk_start_time

        logger.debug(
            f"[SubtitleGen] chunk={data.chunk_index}, duration={duration:.3f}, cumulative={chunk_start_time:.3f}"
        )

        # Determine segments to use
        segments: list[dict[str, Any]] = []
        if self._use_translated and data.translated_segments:
            segments = data.translated_segments
        elif not self._use_translated and data.transcript_segments:
            segments = data.transcript_segments

        if not segments and text:
            segments = [{"start": 0.0, "end": duration * 0.9, "text": text}]

        # Determine alternative text for dual track
        alt_text = None
        alt_segments = None
        if self._dual_track:
            if self._use_translated:
                alt_text = data.transcript
                alt_segments = data.transcript_segments
            else:
                alt_text = data.translated_text
                alt_segments = data.translated_segments

        # 1. Update rolling VTT for the HLS player
        try:
            with self._lock:
                for seg in segments:
                    rel_start = seg.get("start", 0)
                    rel_end = seg.get("end", duration)
                    clean_text = seg.get("text", "").replace("\n", " ").strip()
                    if clean_text:
                        abs_start = chunk_start_time + rel_start
                        abs_end = chunk_start_time + rel_end
                        self._vtt_buffer.add(
                            {
                                "start": abs_start,
                                "end": abs_end,
                                "text": clean_text,
                                "chunk_start": chunk_start_time,
                            }
                        )
                        logger.info(f"[SUB] {clean_text}")

                alt_entries: list[dict[str, Any]] = []
                if alt_text and alt_segments:
                    for seg in alt_segments:
                        rel_start = seg.get("start", 0)
                        rel_end = seg.get("end", duration)
                        clean_alt = seg.get("text", "").replace("\n", " ").strip()
                        if clean_alt:
                            abs_start = chunk_start_time + rel_start
                            abs_end = chunk_start_time + rel_end
                            alt_entries.append(
                                {
                                    "start": abs_start,
                                    "end": abs_end,
                                    "text": clean_alt,
                                    "chunk_start": chunk_start_time,
                                }
                            )

                self._vtt_buffer.trim()
                self._vtt_buffer.rewrite()

                fragment_path = self._hls_manager.write_fragment(
                    data.chunk_index,
                    segments,
                    duration,
                    abs_start=chunk_start_time,
                )
                if fragment_path:
                    self._hls_manager.fragments.append(
                        {
                            "chunk_index": data.chunk_index,
                            "duration": duration,
                            "start": chunk_start_time,
                            "path": fragment_path,
                        }
                    )
                    self._hls_manager.rewrite_playlist()

                if self._dual_track and alt_text and alt_segments:
                    try:
                        with open(self._vtt_alt_path, "w", encoding="utf-8") as f:
                            f.write("WEBVTT\n\n")
                            for i, seg in enumerate(alt_segments):
                                rel_start = seg.get("start", 0)
                                rel_end = seg.get("end", duration)
                                clean_alt = seg.get("text", "").replace("\n", " ").strip()
                                if not clean_alt:
                                    continue
                                abs_start = chunk_start_time + rel_start
                                abs_end = chunk_start_time + rel_end
                                start_str = self._format_timestamp(abs_start, "vtt")
                                end_str = self._format_timestamp(abs_end, "vtt")
                                f.write(f"{i + 1}\n")
                                f.write(f"{start_str} --> {end_str}\n")
                                f.write(f"{clean_alt}\n\n")
                    except Exception as e:
                        logger.error(f"Error writing alt VTT: {e}")

            file_size = self._vtt_path.stat().st_size
            logger.debug(f"VTT file size: {file_size} bytes, entries: {len(self._vtt_buffer.entries)}")
            data.subtitles_path = str(self._vtt_path)
        except Exception as e:
            logger.error(f"Error writing global VTT: {e}")

        # 2. Create per-chunk SRT for Video Muxer burn-in
        chunk_srt_path = self._subtitles_dir / f"chunk_{data.chunk_index:06d}.srt"
        try:
            with open(chunk_srt_path, "w", encoding="utf-8") as f:
                for i, seg in enumerate(segments):
                    start_str = self._format_timestamp(seg.get("start", 0), "srt")
                    end_str = self._format_timestamp(seg.get("end", duration), "srt")
                    clean_text = seg.get("text", "").replace("\n", " ").strip()
                    if clean_text:
                        f.write(f"{i + 1}\n")
                        f.write(f"{start_str} --> {end_str}\n")
                        f.write(f"{clean_text}\n\n")

            if self._format == "srt":
                data.subtitles_path = str(chunk_srt_path)
        except Exception as e:
            logger.error(f"Error writing chunk SRT: {e}")

        # 3. Log delay info
        if segments and pipeline_delay > 0:
            logger.info(
                f"[SubtitleGen] Pipeline delay={pipeline_delay:.1f}s, "
                f"cumulative={chunk_start_time:.1f}s, shifted={shifted_start:.1f}s"
            )

        return data

    def _format_timestamp(self, seconds: float, format_type: str = "vtt") -> str:
        from ._format import format_timestamp as _fmt

        return _fmt(seconds, format_type)
