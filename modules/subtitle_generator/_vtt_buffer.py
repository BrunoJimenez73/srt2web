import logging
from pathlib import Path

from ._format import format_timestamp
from ._types import SubtitleEntry

logger = logging.getLogger("srt2web.module.subtitle_generator")


class VTTBuffer:
    """Rolling VTT buffer with trim and atomic rewrite."""

    def __init__(
        self,
        max_entries: int = 1000,
        max_age_seconds: float = 1800.0,
        subtitles_dir: Path = Path(),
        vtt_path: Path = Path(),
    ) -> None:
        self._max_vtt_entries = max_entries
        self._vtt_max_age_seconds = max_age_seconds
        self._subtitles_dir = subtitles_dir
        self._vtt_path = vtt_path
        self._entries: list[SubtitleEntry] = []

    def configure(self, max_entries: int, max_age_seconds: float) -> None:
        self._max_vtt_entries = max_entries
        self._vtt_max_age_seconds = max_age_seconds

    def set_paths(self, subtitles_dir: Path, vtt_path: Path) -> None:
        self._subtitles_dir = subtitles_dir
        self._vtt_path = vtt_path

    def clear(self) -> None:
        self._entries.clear()

    @property
    def entries(self) -> list[SubtitleEntry]:
        return self._entries

    def add(self, entry: SubtitleEntry) -> None:
        self._entries.append(entry)

    def trim(self) -> None:
        """Trim VTT entries to keep only recent ones (rolling window)."""
        if not self._entries:
            return

        latest_abs = 0.0
        for entry in self._entries:
            cs = entry.get("chunk_start", 0.0)
            latest_abs = max(latest_abs, cs + entry["end"])

        cutoff_abs = latest_abs - self._vtt_max_age_seconds

        self._entries = [
            entry for entry in self._entries if (entry.get("chunk_start", 0.0) + entry["end"]) > cutoff_abs
        ]

        if len(self._entries) > self._max_vtt_entries:
            self._entries = self._entries[-self._max_vtt_entries :]

    def rewrite(self) -> None:
        """Rewrite VTT file with current rolling window entries (atomic write)."""
        tmp_path = self._subtitles_dir / ".subs.vtt.tmp"

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n\n")
                for entry in self._entries:
                    start_str = format_timestamp(entry["start"], "vtt")
                    end_str = format_timestamp(entry["end"], "vtt")
                    chunk_start = entry.get("chunk_start", 0)
                    f.write(f"NOTE chunk_start: {chunk_start:.3f}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{entry['text']}\n\n")
            tmp_path.replace(self._vtt_path)
        except Exception as e:
            logger.error(f"Error rewriting VTT file: {e}")
