import logging
from pathlib import Path
from typing import Any

from core.paths import atomic_replace

from ._format import format_timestamp

logger = logging.getLogger("srt2web.module.subtitle_generator")


class FragmentWriter:
    """
    Writes HLS subtitle fragments and manages the media playlist.

    Each fragment contains cues with media-relative timestamps (0 to duration).
    The playlist uses #EXT-X-DISCONTINUITY before each fragment to match
    the video HLS segments where FFmpeg resets PTS to ~0 per segment.
    MEDIA-SEQUENCE and rolling window match the video HLS playlist exactly.
    """

    def __init__(
        self,
        playlist_path: Path = Path(),
        list_size: int = 10,
        subtitles_dir: Path = Path(),
    ) -> None:
        self._playlist_path = playlist_path
        self._list_size = list_size
        self._subtitles_dir = subtitles_dir
        self._fragments: list[dict[str, Any]] = []
        self._video_playlist_path: Path | None = None

    def configure(self, list_size: int) -> None:
        self._list_size = list_size

    def set_paths(self, playlist_path: Path, subtitles_dir: Path) -> None:
        self._playlist_path = playlist_path
        self._subtitles_dir = subtitles_dir

    def set_video_playlist_path(self, video_playlist_path: Path | None) -> None:
        """Point at the video HLS playlist (stream.m3u8) for window alignment.

        When available, the subtitle playlist is trimmed to the video window
        (never ahead of the video) and reuses the video EXTINF durations so
        both playlists accumulate identical timelines (no cue drift).
        """
        self._video_playlist_path = video_playlist_path

    def _write_empty_playlist(self, media_sequence: int, target_duration: int | None = None) -> None:
        """Write a minimal empty media playlist anchored at a sequence number."""
        tmp_path = self._playlist_path.with_suffix(self._playlist_path.suffix + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write("#EXT-X-VERSION:3\n")
                td = target_duration if target_duration is not None else 10
                f.write(f"#EXT-X-TARGETDURATION:{td}\n")
                f.write(f"#EXT-X-MEDIA-SEQUENCE:{media_sequence}\n")
            atomic_replace(tmp_path, self._playlist_path)
        except Exception as e:
            logger.error(f"Error writing empty HLS playlist: {e}")

    def _read_video_durations(self) -> dict[int, float] | None:
        """Read {segment_index: EXTINF} from the video stream.m3u8, if present."""
        if not self._video_playlist_path or not self._video_playlist_path.exists():
            return None
        try:
            durations: dict[int, float] = {}
            last_dur = 0.0
            for line in self._video_playlist_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    val = line[len("#EXTINF:") :]
                    if val.endswith(","):
                        val = val[:-1]
                    try:
                        last_dur = float(val)
                    except ValueError:
                        last_dur = 0.0
                elif line.startswith("seg_") and line.endswith(".ts"):
                    try:
                        idx = int(line[4:-3])
                    except ValueError:
                        continue
                    durations[idx] = last_dur
            return durations or None
        except OSError:
            return None

    def clear(self) -> None:
        self._fragments.clear()

    @property
    def fragments(self) -> list[dict[str, Any]]:
        return self._fragments

    @property
    def playlist_path(self) -> Path:
        return self._playlist_path

    def write_fragment(
        self,
        chunk_index: int,
        segments: list[dict[str, Any]],
        duration: float,
        pts_start: float = 0.0,
    ) -> str:
        """
        Write a per-chunk HLS subtitle fragment with MEDIA-RELATIVE timestamps.

        Args:
            chunk_index: Sequential chunk index
            segments: List of segment dicts with 'start', 'end', 'text'
            duration: Fragment duration in seconds
            pts_start: PTS timestamp from ChunkClock (cumulative_duration)

        Returns:
            Absolute path of written fragment, or empty string on failure.
        """
        fragment_name = f"subs_seg_{chunk_index:06d}.vtt"
        fragment_path = self._subtitles_dir / fragment_name

        try:
            with open(fragment_path, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n\n")
                cue_index = 0
                for seg in segments:
                    rel_start = max(0.0, float(seg.get("start", 0.0)))
                    rel_end = float(seg.get("end", duration))
                    rel_end = min(max(rel_end, rel_start), duration)
                    clean_text = seg.get("text", "").replace("\n", " ").strip()
                    if not clean_text:
                        continue
                    # MEDIA-RELATIVE timestamps (0 to duration)
                    start_str = format_timestamp(rel_start, "vtt")
                    end_str = format_timestamp(rel_end, "vtt")
                    cue_index += 1
                    f.write(f"{cue_index}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{clean_text}\n\n")
        except Exception as e:
            logger.error(f"Error writing HLS fragment {fragment_name}: {e}")
            return ""

        return str(fragment_path)

    def rewrite_playlist(self) -> None:
        """
        Write the HLS subtitle media playlist (subs.m3u8) with rolling window
        matching the video HLS playlist. Uses #EXT-X-DISCONTINUITY before each
        fragment. MEDIA-SEQUENCE matches the first fragment's chunk_index. Atomic write.

        FIX-2026-08: this playlist must *never* run ahead of the video. The
        writer consumes chunks before HLSOutput does (it sits earlier in the
        pipeline), so its window can expose fragments whose video segment does
        not exist yet — HLS.js then drops those cues (subtitles appear briefly
        and vanish). We therefore trim the playlist to the video window and
        reuse the video EXTINF durations when stream.m3u8 is available, so both
        playlists accumulate identical timelines (no progressive cue drift).
        #EXT-X-PLAYLIST-TYPE:EVENT is NOT emitted: EVENT forbids trimming,
        contradicting our rolling window and the advancing MEDIA-SEQUENCE.
        """
        if not self._playlist_path or str(self._playlist_path) == ".":
            return

        video_durations = self._read_video_durations()
        logger.debug(
            "[FragmentWriter] rewrite_playlist: fragments=%d, video_durations=%s",
            len(self._fragments),
            list(video_durations.keys()) if video_durations else None,
        )

        if not self._fragments and not video_durations:
            self._write_empty_playlist(0)
            return

        # Align the FULL window with the video: the subs playlist mirrors the
        # video playlist indices EXACTLY (same MEDIA-SEQUENCE, same EXTINF,
        # same window). A per-index intersection of the trimmed sub window
        # (F193 v1/v2) still diverged because the internal rolling window
        # (hls_list_size=10) is smaller than the video window (12): the sub
        # base ran 2-3 fragments ahead of the video base, and HLS.js placed
        # every cue ~2-3 fragments early (subtitles appear once at startup,
        # then vanish from the correct cue onward).
        #
        # Indexes the generator has NOT written yet are NOT listed here and
        # get NO placeholder file: an earlier version created empty
        # placeholders for them, but HLS.js downloads a fragment once and
        # never re-parses it, so the real cues written seconds later were
        # permanently "burned" (subtitles frozen until the window rolled).
        # The re-sync callback rewrites the playlist as each fragment
        # materializes, so the window self-heals within one chunk.
        frags: list[dict[str, Any]] = list(self._fragments)
        if video_durations:
            frags = []
            min_video_idx = min(video_durations)
            for idx in sorted(video_durations):
                frag = next(
                    (f for f in self._fragments if f["chunk_index"] == idx),
                    None,
                )
                if frag is not None:
                    frags.append(frag)
                    continue
                # Outside the in-memory window but already written to disk by
                # the generator (legitimate rolled-out fragments). Files on
                # disk always carry real content — placeholders no longer
                # exist by construction.
                if (self._subtitles_dir / f"subs_seg_{idx:06d}.vtt").exists():
                    frags.append(
                        {
                            "chunk_index": idx,
                            "duration": float(video_durations[idx]),
                            "pts_start": 0.0,
                            "path": "",
                        }
                    )
            if not frags:
                # Video playlist has segments but no subtitle fragment is
                # written yet (generator warming up). Anchor the empty
                # playlist to the video sequence so hls.js does not treat
                # the track as a fresh timeline.
                td = max(1, int(max(video_durations.values())) + 1) if video_durations else 10
                self._write_empty_playlist(min_video_idx, td)
                return

        if video_durations:
            target_duration = max(1, int(max(video_durations.values())) + 1)
        else:
            target_duration = max(1, int(max(f["duration"] for f in frags)) + 1)
        first_sn = frags[0]["chunk_index"]
        media_sequence = first_sn

        def _extinf_duration(frag: dict[str, Any]) -> float:
            if video_durations:
                return float(video_durations.get(frag["chunk_index"], frag["duration"]))
            return float(frag["duration"])

        tmp_path = self._playlist_path.with_suffix(self._playlist_path.suffix + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write("#EXT-X-VERSION:3\n")
                f.write(f"#EXT-X-TARGETDURATION:{target_duration}\n")
                f.write(f"#EXT-X-MEDIA-SEQUENCE:{media_sequence}\n")
                for frag in frags:
                    frag_chunk_index = frag["chunk_index"]
                    f.write(f"#EXTINF:{_extinf_duration(frag):.3f},\n")
                    f.write("#EXT-X-DISCONTINUITY\n")
                    f.write(f"subs_seg_{frag_chunk_index:06d}.vtt\n")
            atomic_replace(tmp_path, self._playlist_path)
        except Exception as e:
            logger.error(f"Error rewriting HLS subtitle playlist: {e}")

    def trim(self) -> None:
        """Apply rolling window: keep only most recent fragments."""
        if len(self._fragments) <= self._list_size:
            return
        self._fragments = self._fragments[-self._list_size :]

    def add_fragment(self, chunk_index: int, duration: float, pts_start: float, path: str) -> None:
        """Register a new fragment in the rolling window."""
        self._fragments.append(
            {
                "chunk_index": chunk_index,
                "duration": duration,
                "pts_start": pts_start,
                "path": path,
            }
        )
        self.trim()

    def get_window_info(self) -> dict[str, Any]:
        """Get current playlist window info for debugging/monitoring."""
        if not self._fragments:
            return {"count": 0, "first_index": None, "last_index": None}
        return {
            "count": len(self._fragments),
            "first_index": self._fragments[0]["chunk_index"],
            "last_index": self._fragments[-1]["chunk_index"],
            "media_sequence": self._fragments[0]["chunk_index"],
            "target_duration": max(1, int(max(f["duration"] for f in self._fragments)) + 1),
        }
