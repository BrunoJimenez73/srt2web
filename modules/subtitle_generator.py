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
        self._hls_list_size = 6  # Mirrors video list_size; rolling window
        self._hls_fragments: list[dict[str, Any]] = []  # [{chunk_index, start, duration, path}]

        self._last_chunk_index = -1
        self._last_cumulative = 0.0  # Track last cumulative for validation
        self._last_wall_clock = 0.0  # Track wall clock time for drift detection
        self._drift_monitor: Any = None  # Optional SubtitleSyncMonitor (set by app_context)

        # Rolling window for VTT entries (prevent unbounded growth)
        self._vtt_entries: list[dict[str, Any]] = []
        self._max_vtt_entries = 2000  # Keep last 2000 subtitle entries (~200 chunks)
        self._vtt_max_age_seconds = 7200.0  # Remove entries older than 2 hours
        self._in_configure = False  # Flag to prevent configure from overriding init defaults

        # Cache for timestamp formatting to avoid recomputation
        self.timestamp_format_cache = LRUCache(maxsize=500, ttl_seconds=60)
        # Cache for calculated timestamps (text, start_ms) -> timestamp
        self.timestamp_cache = LRUCache(maxsize=500, ttl_seconds=60)
        # Sync correction factor for drift compensation (1.0 = no correction)
        self.sync_correction_factor = 1.0

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
        # Remove stale subs.m3u8 so the HLS player doesn't fetch a leftover playlist
        if self._hls_playlist_path.exists():
            with contextlib.suppress(OSError):
                self._hls_playlist_path.unlink()

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
        import sys as _sys

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
            if _sys.platform == "win32":
                if self._vtt_path.exists():
                    self._vtt_path.unlink()
                tmp_path.rename(self._vtt_path)
            else:
                tmp_path.replace(self._vtt_path)
        except Exception as e:
            logger.error(f"Error rewriting VTT file: {e}")

    def _write_hls_fragment(self, chunk_index: int, segments: list[dict[str, Any]], duration: float) -> str:
        """
        Write a per-chunk HLS subtitle fragment with MEDIA-RELATIVE timestamps.

        F108: HLS.js expects subtitle cues inside a media playlist fragment to be
        timed from the start of the fragment (not absolute media time). The player
        maps cue.start to absolute media time = sum(EXTINF preceding) + cue.start.

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
                    # Clamp negative starts to 0; HLS cues must be >= 0
                    rel_start = max(0.0, rel_start)
                    rel_end = float(seg.get("end", duration))
                    # Clamp end to duration so cues never extend past the fragment
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
        import sys as _sys

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
                if _sys.platform == "win32":
                    if self._hls_playlist_path.exists():
                        self._hls_playlist_path.unlink()
                    tmp_path.rename(self._hls_playlist_path)
                else:
                    tmp_path.replace(self._hls_playlist_path)
            except Exception as e:
                logger.error(f"Error writing empty HLS playlist: {e}")
            return

        # Compute target duration: max EXTINF rounded up
        target_duration = max(1, int(max(f["duration"] for f in self._hls_fragments)) + 1)
        media_seq = self._hls_fragments[0]["chunk_index"]

        tmp_path = self._hls_playlist_path.with_suffix(self._hls_playlist_path.suffix + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write("#EXT-X-VERSION:3\n")
                f.write(f"#EXT-X-TARGETDURATION:{target_duration}\n")
                f.write(f"#EXT-X-MEDIA-SEQUENCE:{media_seq}\n")
                for frag in self._hls_fragments:
                    frag_chunk_index = frag["chunk_index"]
                    frag_duration = frag["duration"]
                    f.write(f"#EXTINF:{frag_duration:.3f},\n")
                    f.write(f"subs_seg_{frag_chunk_index:06d}.vtt\n")
            if _sys.platform == "win32":
                if self._hls_playlist_path.exists():
                    self._hls_playlist_path.unlink()
                tmp_path.rename(self._hls_playlist_path)
            else:
                tmp_path.replace(self._hls_playlist_path)
        except Exception as e:
            logger.error(f"Error rewriting HLS subtitle playlist: {e}")

    def _trim_hls_fragments(self) -> None:
        """
        Apply rolling window to HLS fragments: keep only the most recent
        `hls_list_size` fragments, deleting their files from disk.
        """
        if len(self._hls_fragments) <= self._hls_list_size:
            return
        to_drop = self._hls_fragments[: -self._hls_list_size]
        self._hls_fragments = self._hls_fragments[-self._hls_list_size :]
        for frag in to_drop:
            frag_path = frag.get("path")
            if not frag_path:
                continue
            with contextlib.suppress(OSError):
                Path(frag_path).unlink()

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

                        # ABSOLUTE timestamps: chunk_start + relative offset
                        abs_start = chunk_start_time + rel_start
                        abs_end = chunk_start_time + rel_end

                        # Apply timestamp caching with sync correction
                        cache_key = (clean_text, int(abs_start * 1000))  # text, start_ms
                        cached_timestamp = self.timestamp_cache.get(cache_key)

                        if cached_timestamp is not None:
                            # Cache hit: use cached timestamp with sync correction
                            corrected_start = cached_timestamp + (self.sync_correction_factor - 1.0) * abs_start
                            corrected_end = (
                                cached_timestamp + (self.sync_correction_factor - 1.0) * abs_end + (abs_end - abs_start)
                            )
                            logger.debug(f"Cache hit for subtitle: {clean_text[:20]}...")
                        else:
                            # Cache miss: calculate and store
                            self.timestamp_cache.set(cache_key, abs_start)
                            corrected_start = abs_start
                            corrected_end = abs_end
                            logger.debug(f"Cache miss for subtitle: {clean_text[:20]}...")

                        self._vtt_entries.append(
                            {
                                "start": corrected_start,  # ABSOLUTE timestamp with sync correction!
                                "end": corrected_end,  # ABSOLUTE timestamp with sync correction!
                                "text": clean_text,
                                "chunk_start": chunk_start_time,
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
                    self._trim_hls_fragments()
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

        # 3. F108 — Drift sync hook: actually call the monitor on every chunk
        # so the previously-dead `enable_drift_detection` flag does something useful.
        if self._drift_monitor is not None and segments:
            try:
                import time as _time

                first_cue = segments[0]
                cue_first_media_ms = chunk_start_time * 1000.0
                wall_clock_ms = _time.time() * 1000.0
                # The monitor compares an "expected audio wall clock" against
                # the "subtitle first-cue media time". We approximate audio
                # wall clock as `now` and subtitle time as the chunk start.
                # If the chunk started N seconds ago, the cue should be N
                # seconds in the past, so we shift the comparison to keep
                # the drift signal stable across long sessions.
                chunk_age_ms = max(0.0, wall_clock_ms - (wall_clock_ms - (chunk_start_time * 1000.0)))
                # Simpler & correct: compare wall clock now vs (chunk_start + current chunk position).
                # We use the chunk start as the subtitle's authoritative time anchor.
                drift_factor = self._drift_monitor.check_sync(
                    audio_timestamp_ms=wall_clock_ms,
                    subtitle_timestamp_ms=int(cue_first_media_ms),
                )
                # Apply smoothing: only update if drift is meaningful
                if drift_factor != 1.0 and abs(drift_factor - 1.0) < 0.5:
                    # Smooth blend to avoid jitter
                    new_factor = 0.7 * self.sync_correction_factor + 0.3 * drift_factor
                    self.sync_correction_factor = new_factor
            except Exception as e:
                logger.debug(f"[SubtitleGen] drift monitor check failed: {e}")

        return data
