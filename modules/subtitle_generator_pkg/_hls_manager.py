import logging
from pathlib import Path
from typing import Any

from ._format import format_timestamp
from ._types import HLSFragment

logger = logging.getLogger("srt2web.module.subtitle_generator")


class HLSManager:
    """Manages per-chunk HLS subtitle fragments + media playlist.

    Uses a rolling window matching the video HLS playlist so timeline
    alignment is consistent. VTT cues use fragment-relative timestamps
    (0 to duration) and each fragment carries #EXT-X-DISCONTINUITY to
    match the video segments. MEDIA-SEQUENCE increments with the window
    just like the video playlist.
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
        self._fragments: list[HLSFragment] = []
        self._base_sequence: int = 0

    def configure(self, list_size: int) -> None:
        self._list_size = list_size

    def set_paths(self, playlist_path: Path, subtitles_dir: Path) -> None:
        self._playlist_path = playlist_path
        self._subtitles_dir = subtitles_dir

    def clear(self) -> None:
        self._fragments.clear()

    @property
    def fragments(self) -> list[HLSFragment]:
        return self._fragments

    @property
    def playlist_path(self) -> Path:
        return self._playlist_path

    def write_fragment(
        self,
        chunk_index: int,
        segments: list[dict[str, Any]],
        duration: float,
        abs_start: float = 0.0,
    ) -> str:
        """
        Write a per-chunk HLS subtitle fragment with FRAGMENT-RELATIVE timestamps
        (0 to duration). This matches the video HLS segments where each TS segment
        has PTS starting from ~0 (FFmpeg mpegts muxer resets timestamps).
        The #EXT-X-DISCONTINUITY in the playlist tells HLS.js to compute the
        correct timeline offset from MEDIA-SEQUENCE.

        Returns the absolute path of the written fragment, or empty string on failure.
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
                    # FRAGMENT-RELATIVE timestamps (0 to duration) to match
                    # video segment PTS reset by FFmpeg mpegts muxer.
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
        fragment to match video segments. MEDIA-SEQUENCE matches the first
        fragment's chunk_index. Atomic write.
        """
        if not self._playlist_path or str(self._playlist_path) == ".":
            return

        if not self._fragments:
            tmp_path = self._playlist_path.with_suffix(self._playlist_path.suffix + ".tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write("#EXTM3U\n")
                    f.write("#EXT-X-VERSION:3\n")
                    f.write("#EXT-X-PLAYLIST-TYPE:EVENT\n")
                    f.write("#EXT-X-TARGETDURATION:10\n")
                    f.write("#EXT-X-MEDIA-SEQUENCE:0\n")
                tmp_path.replace(self._playlist_path)
            except Exception as e:
                logger.error(f"Error writing empty HLS playlist: {e}")
            return

        target_duration = max(1, int(max(f["duration"] for f in self._fragments)) + 1)
        # MEDIA-SEQUENCE matches the first fragment's chunk_index.
        # Only fragments within the rolling window are included.
        first_sn = self._fragments[0]["chunk_index"]
        media_sequence = first_sn

        tmp_path = self._playlist_path.with_suffix(self._playlist_path.suffix + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write("#EXT-X-VERSION:3\n")
                f.write("#EXT-X-PLAYLIST-TYPE:EVENT\n")
                f.write(f"#EXT-X-TARGETDURATION:{target_duration}\n")
                f.write(f"#EXT-X-MEDIA-SEQUENCE:{media_sequence}\n")
                for frag in self._fragments:
                    frag_chunk_index = frag["chunk_index"]
                    frag_duration = frag["duration"]
                    f.write(f"#EXTINF:{frag_duration:.3f},\n")
                    # Each subtitle fragment gets #EXT-X-DISCONTINUITY to
                    # match the video playlist, where FFmpeg mpegts muxer
                    # resets PTS to ~0 for every segment.
                    f.write("#EXT-X-DISCONTINUITY\n")
                    f.write(f"subs_seg_{frag_chunk_index:06d}.vtt\n")
            tmp_path.replace(self._playlist_path)
        except Exception as e:
            logger.error(f"Error rewriting HLS subtitle playlist: {e}")

    def trim(self) -> None:
        """Apply rolling window: keep only most recent fragments."""
        if len(self._fragments) <= self._list_size:
            return
        self._fragments = self._fragments[-self._list_size :]
