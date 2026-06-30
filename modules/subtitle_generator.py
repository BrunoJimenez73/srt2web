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
        self._subtitles_dir = Path()
        self._vtt_path = Path()
        self._vtt_alt_path = Path()  # Dual track: original if using translated, vice versa
        self._chunk_duration = 5  # Default, will be overridden by config
        self._lock = threading.Lock()

        # F108 — HLS-native subtitle path
        self._hls_playlist_path = Path()  # output/subtitles/subs.m3u8
        self._hls_list_size = 1000  # Safety limit only — playlist must NOT trim
        # so the player always finds cues for its current position
        self._hls_fragments: list[dict[str, Any]] = []  # [{chunk_index, start, duration, path}]

        self._last_chunk_index = -1
        self._last_cumulative = 0.0  # Track last cumulative for validation
        self._drift_monitor: Any = None  # Optional SubtitleSyncMonitor (set by app_context)
        self._pipeline_start_wall: float = 0.0  # Wall clock when first subtitle is generated
        self._pipeline_delay_smoothed: float = 0.0  # Smoothed pipeline latency (seconds)
        self._smoothing_factor: float = 0.1  # Conservative EMA — low factor prevents oscillation
        self._dead_zone: float = 1.0  # Ignore delay changes smaller than this (seconds)
        self._max_delay_increase: float = 2.0  # Cap per-chunk delay increase (seconds)

        # Rolling window for VTT entries (prevent unbounded growth)
        self._vtt_entries: list[dict[str, Any]] = []
        self._max_vtt_entries = 2000  # Keep last 2000 subtitle entries (~200 chunks)
        self._vtt_max_age_seconds = 7200.0  # Remove entries older than 2 hours
        self._in_configure = False  # Flag to prevent configure from overriding init defaults

        # Cache for timestamp formatting to avoid recomputation
        self.timestamp_format_cache = LRUCache(maxsize=500, ttl_seconds=60)

        self._history: list[dict[str, Any]] = []
        self._max_history = 10
        self._previous_chunk_duration = 5
        super().__init__("subtitle_generator", config)

    def configure(self, config: dict[str, Any]) -> None:
        super().configure(config)
        self._use_translated = config.get("use_translated", self._use_translated)
        self._format = config.get("format", self._format)
        self._dual_track = config.get("dual_track", False)
        new_chunk_duration = config.get("chunk_duration", self._chunk_duration)
        if new_chunk_duration != self._previous_chunk_duration and hasattr(self, "_vtt_entries"):
            logger.info(
                f"[SubtitleGen] chunk_duration changed: {self._previous_chunk_duration}s → {new_chunk_duration}s"
            )
            self._last_chunk_index = -1
            self._last_cumulative = 0.0
            with self._lock:
                self._vtt_entries.clear()
                self._hls_fragments.clear()
            if self._vtt_path and str(self._vtt_path) != ".":
                self._rewrite_vtt_file()
            if self._hls_playlist_path and str(self._hls_playlist_path) != ".":
                self._rewrite_hls_playlist()
        self._chunk_duration = new_chunk_duration
        self._previous_chunk_duration = new_chunk_duration
        self._hls_list_size = int(config.get("hls_list_size", self._hls_list_size))
        # Pipeline delay stabilization settings from config
        self._smoothing_factor = config.get("smoothing_factor", self._smoothing_factor)
        self._dead_zone = config.get("dead_zone", self._dead_zone)
        self._max_delay_increase = config.get("max_delay_increase", self._max_delay_increase)

        # Rolling window settings - use config values or sensible defaults
        # Increased defaults to prevent subtitles from disappearing prematurely
        self._max_vtt_entries = config.get("max_vtt_entries", 1000)
        self._vtt_max_age_seconds = config.get("vtt_max_age_seconds", 1800.0)
        logger.debug(
            f"[SubtitleGen] Rolling window: max_entries={self._max_vtt_entries}, max_age={self._vtt_max_age_seconds}s"
        )

    def start(self) -> None:
        """Initialize subtitle files."""
        self._state = ModuleState.STARTING

        # Record pipeline start wall-clock so the first _do_process call
        # already has a meaningful wall_elapsed (= pipeline latency).
        self._pipeline_start_wall = time.time()

        self._subtitles_dir = Path(self._output_dir) / "subtitles"
        os.makedirs(self._subtitles_dir, exist_ok=True)
        self._subtitles_dir.mkdir(parents=True, exist_ok=True)

        self._vtt_path = self._subtitles_dir / "subs.vtt"
        vtt_open_path = os.path.join(self._output_dir, "subtitles", "subs.vtt")
        self._vtt_alt_path = self._subtitles_dir / "subs_original.vtt"
        # F108 — HLS-native subtitle path
        self._hls_playlist_path = self._subtitles_dir / "subs.m3u8"

        # Clean old chunk SRT files and stale HLS subtitle fragments from previous sessions
        for old_chunk in Path(self._output_dir, "subtitles").glob("chunk_*.srt"):
            with contextlib.suppress(OSError):
                old_chunk.unlink()
        for old_vtt in Path(self._output_dir, "subtitles").glob("subs_seg_*.vtt"):
            with contextlib.suppress(OSError):
                old_vtt.unlink()
        # Pre-create empty subs.m3u8 so HLS.js never gets a 404 during startup.
        # HLS.js entering a subtitle retry loop on 404 causes levelEmptyError
        # and buffer stalls. _rewrite_hls_playlist will update it with real fragments.
        # Always rewrite even if a stale playlist exists — the previous session's
        # fragment references are now invalid.
        self._rewrite_hls_playlist()

        # Reset files with WebVTT header
        with self._lock:
            try:
                with open(vtt_open_path, "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n")
            except Exception as e:
                logger.error(f"Failed to initialize VTT {vtt_open_path}: {e}")

            # Initialize dual track file if enabled
            if self._dual_track:
                alt_path = str(self._vtt_alt_path)
                try:
                    with open(alt_path, "w", encoding="utf-8") as f:
                        f.write("WEBVTT\n\n")
                except Exception as e:
                    logger.error(f"Failed to initialize alt VTT: {e}")

        self._last_chunk_index = -1
        self._last_cumulative = 0.0
        self._history = []
        self._vtt_entries = []  # Clear rolling window
        self._hls_fragments = []  # F108: clear HLS fragment registry
        self._state = ModuleState.RUNNING
        logger.info(
            f"SubtitleGenerator ready. Format: {self._format}, "
            f"Output: {self._vtt_path}, HLS playlist: {self._hls_playlist_path}"
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

    def _trim_vtt_entries(self) -> None:
        """Trim VTT entries to keep only recent ones (rolling window)."""
        if not self._vtt_entries:
            return

        # Use absolute timestamp: chunk_start + relative end (for entries that have it)
        latest_abs = 0.0
        for entry in self._vtt_entries:
            cs = entry.get("chunk_start", 0.0)
            latest_abs = max(latest_abs, cs + entry["end"])

        cutoff_abs = latest_abs - self._vtt_max_age_seconds

        # Remove entries older than cutoff (absolute time)
        self._vtt_entries = [
            entry for entry in self._vtt_entries if (entry.get("chunk_start", 0.0) + entry["end"]) > cutoff_abs
        ]

        # Also limit by count
        if len(self._vtt_entries) > self._max_vtt_entries:
            self._vtt_entries = self._vtt_entries[-self._max_vtt_entries :]

    def _rewrite_vtt_file(self) -> None:
        """Rewrite VTT file with current rolling window entries (atomic write)."""
        tmp_path = Path(self._subtitles_dir) / ".subs.vtt.tmp"

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n\n")
                for entry in self._vtt_entries:
                    start_str = self._format_timestamp(entry["start"], "vtt")
                    end_str = self._format_timestamp(entry["end"], "vtt")
                    chunk_start = entry.get("chunk_start", 0)
                    f.write(f"NOTE chunk_start: {chunk_start:.3f}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{entry['text']}\n\n")
            tmp_path.replace(self._vtt_path)
        except Exception as e:
            logger.error(f"Error rewriting VTT file: {e}")

    def _write_hls_fragment(self, chunk_index: int, segments: list[dict[str, Any]], duration: float) -> str:
        """
        Write a per-chunk HLS subtitle fragment with MEDIA-RELATIVE timestamps.

        F108: HLS.js expects subtitle cues inside a media playlist fragment to be
        timed from the start of the fragment (not absolute media time). The player
        maps cue.start to absolute media time = sum(EXTINF preceding) + cue.start.

        IMPORTANT: No time_shift is applied here. Cues MUST start from 0 within
        each fragment. Pipeline delay is already accounted for by the EXTINF
        durations in the subtitle playlist (each fragment's EXTINF matches the
        video segment's duration, so HLS.js aligns them correctly).

        Returns the absolute path of the written fragment.
        """
        fragment_name = f"subs_seg_{chunk_index:06d}.vtt"
        fragment_path = self._subtitles_dir / fragment_name

        try:
            with open(fragment_path, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n\n")
                cue_index = 0
                for seg in segments:
                    rel_start = float(seg.get("start", 0.0))
                    rel_start = max(0.0, rel_start)
                    rel_end = float(seg.get("end", duration))
                    rel_end = min(max(rel_end, rel_start), duration)
                    clean_text = seg.get("text", "").replace("\n", " ").strip()
                    if not clean_text:
                        continue
                    start_str = self._format_timestamp(rel_start, "vtt")
                    end_str = self._format_timestamp(rel_end, "vtt")
                    cue_index += 1
                    f.write(f"{cue_index}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{clean_text}\n\n")
        except Exception as e:
            logger.error(f"Error writing HLS fragment {fragment_name}: {e}")
            return ""

        return str(fragment_path)

    def _rewrite_hls_playlist(self) -> None:
        """
        Write the HLS subtitle media playlist (subs.m3u8) referencing the
        per-chunk fragments. Atomic write.

        F108: this is what HLS.js loads natively via the EXT-X-MEDIA URI
        declared in the video master playlist. Each #EXTINF equals the
        chunk's duration so the player can compute absolute media time
        from sum(EXTINF preceding) + cue.start (which is media-relative).
        """
        if not self._hls_playlist_path or str(self._hls_playlist_path) == ".":
            return

        if not self._hls_fragments:
            # No fragments yet — write a minimal valid empty playlist
            tmp_path = self._hls_playlist_path.with_suffix(self._hls_playlist_path.suffix + ".tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write("#EXTM3U\n")
                    f.write("#EXT-X-VERSION:3\n")
                    f.write("#EXT-X-TARGETDURATION:10\n")
                    f.write("#EXT-X-MEDIA-SEQUENCE:0\n")
                tmp_path.replace(self._hls_playlist_path)
            except Exception as e:
                logger.error(f"Error writing empty HLS playlist: {e}")
            return

        if not self._hls_fragments:
            return

        # Compute target duration: max EXTINF rounded up
        target_duration = max(1, int(max(f["duration"] for f in self._hls_fragments)) + 1)

        tmp_path = self._hls_playlist_path.with_suffix(self._hls_playlist_path.suffix + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write("#EXT-X-VERSION:3\n")
                f.write(f"#EXT-X-TARGETDURATION:{target_duration}\n")
                # CRITICAL: media_seq MUST be 0. HLS.js maps VTT cue timestamps
                # to absolute media time by summing EXTINF durations from the
                # start of THIS playlist. If we trim fragments and advance the
                # sequence, cues get mapped to times far in the past and HLS.js
                # drops them. The rolling window (_trim_hls_fragments) handles
                # cleanup; the playlist always starts from chunk 0.
                f.write("#EXT-X-MEDIA-SEQUENCE:0\n")
                for frag in self._hls_fragments:
                    frag_chunk_index = frag["chunk_index"]
                    frag_duration = frag["duration"]
                    f.write(f"#EXTINF:{frag_duration:.3f},\n")
                    f.write(f"subs_seg_{frag_chunk_index:06d}.vtt\n")
            tmp_path.replace(self._hls_playlist_path)
        except Exception as e:
            logger.error(f"Error rewriting HLS subtitle playlist: {e}")

    def _trim_hls_fragments(self) -> None:
        """
        Apply rolling window to HLS fragments: keep only the most recent
            `hls_list_size` fragments in the playlist.

            IMPORTANT: We do NOT delete old fragment files from disk.
            HLS.js may still have pending requests for recently-removed fragments.
            Deleting files causes 404 errors which make HLS.js disable the
            entire subtitle track. The VTT files are tiny (~1-5KB each) so
            keeping them is negligible cost for reliability.
        """
        if len(self._hls_fragments) <= self._hls_list_size:
            return
        to_drop = self._hls_fragments[: -self._hls_list_size]
        self._hls_fragments = self._hls_fragments[-self._hls_list_size :]

    def set_drift_monitor(self, monitor: Any) -> None:
        """
        Attach a SubtitleSyncMonitor so the generator can call check_sync()
        on each processed chunk. The monitor's correction factor is then
        applied to subsequent cues.

        F108: this wires the previously dead drift-detection path into
        the live subtitle pipeline.
        """
        self._drift_monitor = monitor

    def get_playlist_path(self) -> Path | None:
        """Return the HLS subtitle media playlist path, or None if not initialized."""
        if not self._hls_playlist_path or str(self._hls_playlist_path) == ".":
            return None
        return self._hls_playlist_path

    def get_playlist_url(self) -> str:
        """Return the URL the HLS master playlist should reference for subtitles."""
        return "/subtitles/subs.m3u8"

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Append new text to the WebVTT file and create a per-chunk SRT for burn-in.

        CRITICAL: Uses data.cumulative_duration from PipelineData for sync,
        NOT internal tracking, to prevent drift.
        """
        text = data.translated_text if self._use_translated else data.transcript

        if not text:
            data.subtitles_path = str(self._vtt_path)
            return data

        # Use actual chunk duration for EXTINF — this must match the video segment's
        # real duration to prevent cumulative drift. data.duration comes from the input
        # source and reflects the actual chunk length (not the nominal config value).
        data_duration = getattr(data, "duration", None)
        duration = data_duration if data_duration and data_duration > 0 else self._chunk_duration

        # CRITICAL FIX: Use cumulative_duration from PipelineData for sync
        # This comes from InputSource and is validated there
        chunk_start_time = getattr(data, "cumulative_duration", 0.0)

        # Pipeline delay compensation: shift subtitles forward to match actual playback
        # position. The subtitle generator runs behind the live video because whisper
        # + translate take several seconds per chunk. Without this shift, subtitle cues
        # appear at cumulative time but the video is already ahead.
        #
        # FIX: Use a monotonic, damped estimator instead of oscillating EMA.
        # The old EMA (factor=0.4 + reactive reset) caused the estimated delay
        # to jump between chunks, shifting subtitle absolute positions and producing
        # visible jitter. The new estimator:
        #   - Uses a low EMA factor (0.1) for slow convergence
        #   - Applies a dead zone (1s) to ignore minor fluctuations
        #   - Is monotonically non-decreasing (delay only grows or stays constant)
        #   - Caps per-chunk increase to prevent runaway
        wall_elapsed = time.time() - self._pipeline_start_wall
        raw_delay = wall_elapsed - chunk_start_time
        if raw_delay >= 0:
            if self._pipeline_delay_smoothed == 0:
                self._pipeline_delay_smoothed = raw_delay
            else:
                diff = raw_delay - self._pipeline_delay_smoothed
                # Dead zone: ignore small fluctuations
                if abs(diff) < self._dead_zone:
                    pass  # Keep current smoothed value
                elif diff > 0:
                    # Delay increased — apply conservative EMA then cap
                    self._pipeline_delay_smoothed = (
                        1 - self._smoothing_factor
                    ) * self._pipeline_delay_smoothed + self._smoothing_factor * raw_delay
                    # Monotonic cap: limit how fast delay can grow per chunk
                    max_allowed = self._pipeline_delay_smoothed + self._max_delay_increase
                    if raw_delay > max_allowed:
                        self._pipeline_delay_smoothed = max_allowed
                # Never decrease — delay is monotonically non-decreasing
        pipeline_delay = self._pipeline_delay_smoothed
        shifted_start = chunk_start_time + pipeline_delay

        # F168 — Apply drift correction from SubtitleSyncMonitor
        # Feed the monitor with current positions, then read the smoothed drift.
        if self._drift_monitor is not None:
            audio_wall_ms = wall_elapsed * 1000
            sub_media_ms = shifted_start * 1000
            try:
                # Feed data into the monitor (updates smoothed_drift internally)
                self._drift_monitor.check_sync(audio_wall_ms, sub_media_ms)
                drift_ms = self._drift_monitor.get_drift_ms()
                if abs(drift_ms) > 100:
                    # Negative drift = subtitles behind audio → shift forward
                    correction_s = drift_ms / 1000.0
                    correction_s = max(-3.0, min(3.0, correction_s))
                    shifted_start += correction_s
                    logger.info(
                        f"[SubtitleGen] Drift correction: drift={drift_ms:.0f}ms, "
                        f"shift=+{correction_s:.2f}s -> shifted={shifted_start:.1f}s"
                    )
            except Exception as e:
                logger.error(f"[SubtitleGen] Drift monitor error: {e}")

        # FIX: Validate cumulative_duration is monotonically increasing to prevent drift
        if chunk_start_time < self._last_cumulative:
            logger.warning(
                f"[SubtitleGen] Cumulative duration decreased! "
                f"{chunk_start_time:.3f} < {self._last_cumulative:.3f} - "
                f"using last cumulative to prevent drift"
            )
            chunk_start_time = self._last_cumulative

        # Validate sequential processing (detect out-of-order chunks)
        # Handle pause loop: same chunk_index is OK, just skip subtitle re-add
        is_loop = data.metadata.get("is_loop", False)
        if is_loop:
            # This is a pause loop - same chunk being replayed
            # Don't re-add subtitles, just pass through existing ones
            logger.debug(
                f"[SubtitleGen] Pause loop detected - chunk {data.chunk_index} replaying, skipping subtitle re-add"
            )
            data.subtitles_path = str(self._vtt_path)
            return data
        elif data.chunk_index == self._last_chunk_index and self._last_chunk_index >= 0:
            # Duplicate chunk but not marked as loop - skip subtitle re-add
            data.subtitles_path = str(self._vtt_path)
            return data
        elif data.chunk_index != self._last_chunk_index + 1 and self._last_chunk_index >= 0:
            logger.warning(
                f"[SubtitleGen] Chunk sequence break: expected {self._last_chunk_index + 1}, " f"got {data.chunk_index}"
            )

        # Validate cumulative duration is monotonically increasing
        if chunk_start_time <= self._last_cumulative and self._last_cumulative > 0:
            logger.warning(
                f"[SubtitleGen] Cumulative duration not increasing: "
                f"last={self._last_cumulative:.3f}, current={chunk_start_time:.3f}"
            )

        self._last_chunk_index = data.chunk_index
        self._last_cumulative = chunk_start_time

        logger.debug(
            f"[SubtitleGen] chunk={data.chunk_index}, duration={duration:.3f}, " f"cumulative={chunk_start_time:.3f}"
        )

        # Determine segments to use
        segments = []
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

        # 1. Update rolling VTT for the HLS player (absolute timestamps!)
        try:
            with self._lock:
                # Store ABSOLUTE timestamps: chunk_start + relative offset
                for seg in segments:
                    # Relative timestamps from transcript
                    rel_start = seg.get("start", 0)
                    rel_end = seg.get("end", duration)

                    clean_text = seg.get("text", "").replace("\n", " ").strip()
                    if clean_text:
                        with contextlib.suppress(BaseException):
                            clean_text = clean_text.encode("utf-8").decode("utf-8")

                        # ABSOLUTE timestamps: shifted_start + relative offset
                        # (shifted_start = cumulative + pipeline_delay, to compensate for
                        #  processing latency so subtitles match actual playback position)
                        abs_start = shifted_start + rel_start
                        abs_end = shifted_start + rel_end

                        self._vtt_entries.append(
                            {
                                "start": abs_start,
                                "end": abs_end,
                                "text": clean_text,
                                "chunk_start": shifted_start,
                            }
                        )

                        logger.info(f"[SUB] {clean_text}")

                # Dual track entries (separate list for alternate language)
                alt_entries: list[dict[str, Any]] = []
                if alt_text and alt_segments:
                    for seg in alt_segments:
                        rel_start = seg.get("start", 0)
                        rel_end = seg.get("end", duration)
                        clean_alt = seg.get("text", "").replace("\n", " ").strip()
                        if clean_alt:
                            abs_start = shifted_start + rel_start
                            abs_end = shifted_start + rel_end
                            alt_entries.append(
                                {
                                    "start": abs_start,
                                    "end": abs_end,
                                    "text": clean_alt,
                                    "chunk_start": shifted_start,
                                }
                            )

                # Trim old entries (keep only recent ones)
                self._trim_vtt_entries()

                # Rewrite VTT file with rolling entries
                self._rewrite_vtt_file()

                # F108 — Write per-chunk HLS subtitle fragment with media-relative cues.
                # This is what the HLS.js native subtitle track consumes.
                fragment_path = self._write_hls_fragment(data.chunk_index, segments, duration)
                if fragment_path:
                    self._hls_fragments.append(
                        {
                            "chunk_index": data.chunk_index,
                            "duration": duration,
                            "start": chunk_start_time,
                            "path": fragment_path,
                        }
                    )
                    self._rewrite_hls_playlist()

                # Write dual track file if enabled and has content
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
            logger.debug(f"VTT file size: {file_size} bytes, entries: {len(self._vtt_entries)}")

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

        # 3. F108 — Drift sync hook: log the remaining drift after pipeline delay compensation
        if segments and pipeline_delay > 0:
            logger.info(
                f"[SubtitleGen] Pipeline delay={pipeline_delay:.1f}s, "
                f"cumulative={chunk_start_time:.1f}s, shifted={shifted_start:.1f}s"
            )

        return data
