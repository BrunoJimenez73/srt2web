"""
Subtitle Generator Module — creates WebVTT files for HLS native subtitle tracks.

Formats transcripts or translations into per-chunk HLS subtitle fragments
with MEDIA-RELATIVE timestamps (0..duration) and a rolling playlist
(subs.m3u8) that matches the video HLS playlist 1:1.

CRITICAL: Uses data.cumulative_duration from PipelineData (PTS-based via
ChunkClock) for accurate sync, not internal tracking.
"""

import contextlib
import logging
import os
import threading
from pathlib import Path
from typing import Any

from core.module_base import BaseModule, ModuleState, PipelineData

from ._format import format_timestamp
from ._fragment_writer import FragmentWriter

logger = logging.getLogger("srt2web.module.subtitle_generator")


class SubtitleGenerator(BaseModule):
    """
    Generates HLS-native WebVTT subtitle fragments synchronized with video.

    Architecture:
    - One HLS fragment per pipeline chunk (subs_seg_N.vtt)
    - Cue timestamps are MEDIA-RELATIVE (0 to fragment duration)
    - Rolling playlist (subs.m3u8) with #EXT-X-DISCONTINUITY before each fragment
    - MEDIA-SEQUENCE and TARGETDURATION match video HLS playlist exactly
    - Frontend uses HLS.js native subtitle track (activateFirstSubtitleTrack)
    - Legacy subs.vtt removed; RecordingOutput converts fragments -> SRT on concat

    Dual-track (original + translated) preserved as optional config.
    """

    def __init__(self, config: dict[str, Any] | None = None, output_dir: str = "./output") -> None:
        self._output_dir = output_dir
        self._format = "webvtt"
        self._use_translated = True
        self._dual_track = False
        self._chunk_duration = 5
        self._list_size = 12  # Default matches video HLS list_size
        self._lock = threading.Lock()

        self._fragment_writer = FragmentWriter(list_size=self._list_size)

        self._subtitles_dir: Path = Path()
        self._vtt_alt_path: Path = Path()

        self._last_chunk_index = -1
        self._last_cumulative = 0.0

        # F184: chunks from parallel workers can arrive out of order. Buffer
        # them and write strictly in chunk-index order so the rolling HLS
        # playlist never skips or reorders fragments.
        self._pending: dict[int, PipelineData] = {}
        self._MAX_PENDING = 128

        super().__init__("subtitle_generator", config)

    def configure(self, config: dict[str, Any]) -> None:
        super().configure(config)
        self._use_translated = config.get("use_translated", self._use_translated)
        self._format = config.get("format", self._format)
        self._dual_track = config.get("dual_track", self._dual_track)

        new_chunk_duration = config.get("chunk_duration", self._chunk_duration)
        if new_chunk_duration != self._chunk_duration and hasattr(self, "_fragment_writer"):
            logger.info(f"[SubtitleGen] chunk_duration changed: {self._chunk_duration}s → {new_chunk_duration}s")
            with self._lock:
                self._last_chunk_index = -1
                self._last_cumulative = 0.0
                self._pending.clear()
                self._fragment_writer.clear()
                self._fragment_writer.rewrite_playlist()
            self._chunk_duration = new_chunk_duration

        new_list_size = int(config.get("hls_list_size", self._list_size))
        if new_list_size != self._list_size:
            logger.info(f"[SubtitleGen] hls_list_size changed: {self._list_size} → {new_list_size}")
            self._list_size = new_list_size
            self._fragment_writer.configure(self._list_size)

    def start(self) -> None:
        """Initialize subtitle files and directories."""
        self._state = ModuleState.STARTING

        self._subtitles_dir = Path(self._output_dir) / "subtitles"
        os.makedirs(self._subtitles_dir, exist_ok=True)
        self._subtitles_dir.mkdir(parents=True, exist_ok=True)

        self._vtt_alt_path = self._subtitles_dir / "subs_original.vtt"

        hls_playlist_path = self._subtitles_dir / "subs.m3u8"
        self._fragment_writer.set_paths(hls_playlist_path, self._subtitles_dir)
        # Align the subtitle window with the video HLS playlist (stream.m3u8)
        # so subs.m3u8 never runs ahead of the published video segments.
        self._fragment_writer.set_video_playlist_path(Path(self._output_dir) / "hls" / "stream.m3u8")

        # Clean stale HLS subtitle artifacts from previous sessions
        for old_chunk in Path(self._output_dir, "subtitles").glob("chunk_*.srt"):
            with contextlib.suppress(OSError):
                old_chunk.unlink()
        for old_vtt in Path(self._output_dir, "subtitles").glob("subs_seg_*.vtt"):
            with contextlib.suppress(OSError):
                old_vtt.unlink()

        # Clear fragment registry and pre-create empty playlist
        self._fragment_writer.clear()
        self._fragment_writer.rewrite_playlist()

        self._last_chunk_index = -1
        self._last_cumulative = 0.0
        self._pending.clear()
        self._state = ModuleState.RUNNING
        logger.info(
            f"SubtitleGenerator ready. Format: {self._format}, "
            f"Output: {self._subtitles_dir}, HLS playlist: {hls_playlist_path}"
        )

    def stop(self) -> None:
        self._pending.clear()
        self._state = ModuleState.IDLE

    def get_playlist_path(self) -> Path | None:
        hls_path = self._fragment_writer.playlist_path
        if not hls_path or str(hls_path) == ".":
            return None
        return hls_path

    def get_playlist_url(self) -> str:
        return "/subtitles/subs.m3u8"

    def sync_playlist(self) -> None:
        """Re-align subs.m3u8 with the current video HLS window.

        Called by HLSOutput after each stream.m3u8 update: the generator
        writes its playlist before the video segment of the same chunk is
        published (it sits earlier in the pipeline), so without this
        re-sync the subtitle window lags the video by one fragment and the
        MEDIA-SEQUENCE values diverge, making HLS.js drop cues.
        """
        with self._lock:
            self._fragment_writer.rewrite_playlist()

    # ------------------------------------------------------------------ #
    # Backward-compatible shim properties (tests access internals)
    # ------------------------------------------------------------------ #

    @property
    def _hls_fragments(self) -> list[dict[str, Any]]:
        return self._fragment_writer.fragments

    @_hls_fragments.setter
    def _hls_fragments(self, value: list[dict[str, Any]]) -> None:
        self._fragment_writer._fragments = value

    @property
    def _hls_playlist_path(self) -> Path:
        return self._fragment_writer.playlist_path

    @_hls_playlist_path.setter
    def _hls_playlist_path(self, value: Path) -> None:
        self._fragment_writer.set_paths(value, self._subtitles_dir)

    @property
    def _hls_list_size(self) -> int:
        return self._fragment_writer._list_size

    @_hls_list_size.setter
    def _hls_list_size(self, value: int) -> None:
        self._fragment_writer.configure(value)

    # Backward-compatible shim for tests
    @property
    def _vtt_entries(self) -> list[dict[str, Any]]:
        """Legacy property for tests - returns entries from current fragments."""
        return []

    @_vtt_entries.setter
    def _vtt_entries(self, value: list[dict[str, Any]]) -> None:
        pass  # No-op for backward compatibility

    def _write_hls_fragment(
        self, chunk_index: int, segments: list[dict[str, Any]], duration: float, pts_start: float = 0.0
    ) -> str:
        return self._fragment_writer.write_fragment(chunk_index, segments, duration, pts_start)

    def _rewrite_hls_playlist(self) -> None:
        self._fragment_writer.rewrite_playlist()

    def _do_process(self, data: PipelineData) -> PipelineData:
        """Append new text to the HLS fragment and rewrite the playlist.

        F184: workers run in parallel, so chunks can arrive out of order.
        A pending buffer reserializes them — fragments and the rolling
        playlist stay in strictly ascending chunk order. Without this,
        a later chunk gets written first, the playlist shows subtitles
        that do not belong to the current video segment, and fragments
        get dropped from the rolling window (subtitles "disappear").
        """
        text = data.translated_text if self._use_translated else data.transcript

        data_duration = getattr(data, "duration", None)
        duration = data_duration if data_duration and data_duration > 0 else self._chunk_duration

        # Authoritative timeline from ChunkClock (PTS/PCR based)
        chunk_start_time = getattr(data, "cumulative_duration", 0.0)

        # Default subtitles_path to playlist even if no text
        data.subtitles_path = str(self._subtitles_dir / "subs.m3u8")

        # Handle pause loop / duplicate chunks FIRST: a replayed chunk must
        # never advance the index nor write a fragment.
        is_loop = data.metadata.get("is_loop", False)
        if is_loop:
            logger.debug(f"[SubtitleGen] Pause loop detected - chunk {data.chunk_index} replaying, skipping")
            return data

        # FIX-2026-08: chunks WITHOUT transcript were previously dropped here
        # without advancing _last_chunk_index. The video still produces its
        # segment for that chunk, so the 1:1 video<->subtitle correspondence
        # broke: every later chunk looked "out of order" (expected < actual),
        # got buffered in _pending, and subtitles froze until MAX_PENDING was
        # exceeded (~10 min at 5s chunks) — users saw subtitles vanish. Now a
        # silent chunk writes an EMPTY fragment (WEBVTT header only) to keep
        # the sequence contiguous and the windows aligned.
        with self._lock:
            expected = self._last_chunk_index + 1

            if data.chunk_index < expected:
                # Stale or duplicate — a fragment with this index was already written
                return data

            if data.chunk_index > expected:
                # Out-of-order: hold it until its predecessors arrive
                if data.chunk_index > expected + self._MAX_PENDING:
                    # Predecessors are lost (e.g. watchdog restart renumbered
                    # the source). Accept the jump instead of stalling forever.
                    logger.warning(
                        f"[SubtitleGen] Chunk gap too large: expected {expected}, "
                        f"got {data.chunk_index} — writing anyway"
                    )
                else:
                    self._pending[data.chunk_index] = data
                    logger.debug(f"[SubtitleGen] Buffered out-of-order chunk {data.chunk_index} (expected {expected})")
                    return data

            self._write_chunk_locked(data, text or "", duration, chunk_start_time)
            self._drain_pending_locked(duration)

        return data

    def _drain_pending_locked(self, default_duration: float) -> None:
        """Write buffered successors that are now contiguous. Caller holds ``self._lock``."""
        while True:
            nxt = self._pending.pop(self._last_chunk_index + 1, None)
            if nxt is None:
                break
            nxt_duration = getattr(nxt, "duration", None)
            if not nxt_duration or nxt_duration <= 0:
                nxt_duration = default_duration
            nxt_text = (nxt.translated_text if self._use_translated else nxt.transcript) or ""
            nxt_cumulative = getattr(nxt, "cumulative_duration", 0.0)
            self._write_chunk_locked(nxt, nxt_text, nxt_duration, nxt_cumulative)

    def _write_chunk_locked(self, data: PipelineData, text: str, duration: float, chunk_start_time: float) -> None:
        """Write one fragment + rewrite playlist. Caller must hold ``self._lock``."""
        # Validate cumulative_duration is monotonically increasing
        if chunk_start_time < self._last_cumulative:
            logger.warning(
                f"[SubtitleGen] Cumulative duration decreased! "
                f"{chunk_start_time:.3f} < {self._last_cumulative:.3f} - "
                f"using last cumulative to prevent drift"
            )
            chunk_start_time = self._last_cumulative

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
        alt_segments = None
        if self._dual_track:
            if self._use_translated and data.transcript_segments:
                alt_segments = data.transcript_segments
            elif not self._use_translated and data.translated_segments:
                alt_segments = data.translated_segments

        # Write HLS fragment (playlist rewrite deferred to sync_playlist
        # callback from HLSOutput when video playlist exists)
        try:
            # Write fragment with media-relative timestamps (0..duration)
            fragment_path = self._fragment_writer.write_fragment(
                data.chunk_index, segments, duration, pts_start=chunk_start_time
            )

            if fragment_path:
                self._fragment_writer.add_fragment(
                    data.chunk_index,
                    duration,
                    chunk_start_time,
                    fragment_path,
                    segments=segments,
                )
                # Only rewrite immediately if NO video playlist is configured (standalone mode).
                # In pipeline mode, HLSOutput calls sync_playlist() AFTER stream.m3u8 is updated,
                # which avoids a race where HLS.js loads subs.m3u8 before the corresponding
                # video segment exists in stream.m3u8.
                if self._fragment_writer._video_playlist_path is None:
                    self._fragment_writer.rewrite_playlist()

            # Dual track: write alt VTT with absolute timestamps (legacy path)
            if self._dual_track and alt_segments:
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
                            start_str = format_timestamp(abs_start, "vtt")
                            end_str = format_timestamp(abs_end, "vtt")
                            f.write(f"{i + 1}\n")
                            f.write(f"{start_str} --> {end_str}\n")
                            f.write(f"{clean_alt}\n\n")
                except Exception as e:
                    logger.error(f"Error writing alt VTT: {e}")

            data.subtitles_path = fragment_path or str(self._subtitles_dir / "subs.m3u8")
        except Exception as e:
            logger.error(f"Error writing HLS fragment/playlist: {e}")
