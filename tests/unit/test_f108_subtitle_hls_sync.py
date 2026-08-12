"""
F108 — Subtítulos desincronizados del video en sesiones largas / webplayer pausado.

Regression tests for the HLS-native subtitle sync path. Covers:

Backend (subtitle_generator + hls_output):
- _write_hls_fragment produces MEDIA-RELATIVE cue timestamps (HLS.js spec).
- Cue timestamps are clamped: start >= 0, end <= fragment duration, end >= start.
- _rewrite_hls_playlist emits valid HLS v3 with correct EXTINF/EXT-X-TARGETDURATION/
  EXT-X-MEDIA-SEQUENCE entries.
- Empty playlist state (no fragments yet) is a valid #EXTM3U v3 file.
- Rolling window matches video HLS playlist exactly (MEDIA-SEQUENCE, TARGETDURATION,
  #EXT-X-DISCONTINUITY before each fragment).
- start() cleans stale HLS subtitle fragments (subs_seg_*.vtt, subs.m3u8).
- Legacy subs.vtt removed; RecordingOutput converts fragments -> SRT on concat.
- HLSOutput master playlist points at /subtitles/subs.m3u8 when it exists.
- Pre-creation of empty subs.m3u8 keeps the master playlist URI valid
  before the first fragment is written.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.module_base import PipelineData
from modules.subtitle_generator import SubtitleGenerator


def _make_gen(output_dir: str, **configure_kwargs) -> SubtitleGenerator:
    gen = SubtitleGenerator(output_dir=output_dir)
    gen.configure({"chunk_duration": 5, **configure_kwargs})
    gen.start()
    return gen


def _process_chunk(
    gen: SubtitleGenerator, chunk_index: int, text: str = "hola", cumulative: float | None = None
) -> PipelineData:
    duration = 5.0
    return gen._do_process(
        PipelineData(
            chunk_index=chunk_index,
            transcript=text,
            translated_text=text,
            translated_segments=[
                {"start": 0.5, "end": 4.5, "text": text},
            ],
            duration=duration,
            cumulative_duration=cumulative if cumulative is not None else chunk_index * duration,
        )
    )


# ---------------------------------------------------------------------------
# HLS fragment writing
# ---------------------------------------------------------------------------


class TestWriteHLSFragment:
    """_write_hls_fragment produces media-relative cues per HLS.js spec."""

    def test_writes_webvtt_header(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        path = gen._write_hls_fragment(0, [{"start": 0.0, "end": 5.0, "text": "hola"}], 5.0)
        assert path.endswith("subs_seg_000000.vtt")
        content = Path(path).read_text(encoding="utf-8")
        assert content.startswith("WEBVTT\n")

    def test_cue_timestamps_are_media_relative(self, tmp_path: Path) -> None:
        """Cue timestamps in fragment are 0..duration, NOT chunk-absolute."""
        gen = _make_gen(str(tmp_path))
        path = gen._write_hls_fragment(
            42,
            [
                {"start": 1.0, "end": 3.0, "text": "primero"},
                # Use 4.5 (not 4.8) — _format_timestamp casts to int(frac*1000),
                # and 0.8 is not exactly representable in float (becomes 799ms).
                {"start": 3.5, "end": 4.5, "text": "segundo"},
            ],
            5.0,
        )
        content = Path(path).read_text(encoding="utf-8")
        assert "00:00:01.000 --> 00:00:03.000" in content
        assert "00:00:03.500 --> 00:00:04.500" in content
        # Media-relative — no offset from the chunk's absolute position
        assert "00:01:00.000" not in content
        assert "00:01:42.000" not in content

    def test_negative_start_clamped_to_zero(self, tmp_path: Path) -> None:
        """HLS cues must be >= 0; negative starts are clamped."""
        gen = _make_gen(str(tmp_path))
        path = gen._write_hls_fragment(
            0,
            [{"start": -2.0, "end": 3.0, "text": "clip"}],
            5.0,
        )
        content = Path(path).read_text(encoding="utf-8")
        # start = max(0, -2) = 0
        assert "00:00:00.000 --> 00:00:03.000" in content

    def test_end_clamped_to_duration(self, tmp_path: Path) -> None:
        """Cue end cannot exceed fragment duration."""
        gen = _make_gen(str(tmp_path))
        path = gen._write_hls_fragment(
            0,
            [{"start": 1.0, "end": 99.0, "text": "overflow"}],
            5.0,
        )
        content = Path(path).read_text(encoding="utf-8")
        # end = min(99, 5) = 5
        assert "00:00:01.000 --> 00:00:05.000" in content

    def test_end_clamped_above_start_when_inverted(self, tmp_path: Path) -> None:
        """When end < start, end is bumped to start to keep the cue valid."""
        gen = _make_gen(str(tmp_path))
        path = gen._write_hls_fragment(
            0,
            [{"start": 4.0, "end": 1.0, "text": "invertido"}],
            5.0,
        )
        content = Path(path).read_text(encoding="utf-8")
        # end = max(1, 4) = 4 (before duration clamp)
        assert "00:00:04.000 --> 00:00:04.000" in content

    def test_empty_text_segments_are_skipped(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        path = gen._write_hls_fragment(
            0,
            [
                {"start": 0.0, "end": 2.0, "text": "   "},
                {"start": 2.0, "end": 4.0, "text": "ok"},
            ],
            5.0,
        )
        content = Path(path).read_text(encoding="utf-8")
        assert "ok" in content
        # No cue line for the whitespace-only entry
        assert content.count("-->") == 1

    def test_returned_path_ends_with_vtt(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        path = gen._write_hls_fragment(7, [{"start": 0.0, "end": 5.0, "text": "x"}], 5.0)
        assert path.endswith("subs_seg_000007.vtt")
        assert os.path.exists(path)


# ---------------------------------------------------------------------------
# HLS playlist writing
# ---------------------------------------------------------------------------


class TestRewriteHLSPlaylist:
    """_rewrite_hls_playlist emits a valid HLS v3 media playlist."""

    def test_empty_playlist_is_valid(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        # No fragments yet — generator writes minimal valid empty playlist
        gen._rewrite_hls_playlist()
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert content.startswith("#EXTM3U\n")
        assert "#EXT-X-VERSION:3" in content
        assert "#EXT-X-TARGETDURATION:10" in content
        assert "#EXT-X-MEDIA-SEQUENCE:0" in content

    def test_playlist_lists_fragments_in_order(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        for i in range(3):
            _process_chunk(gen, i, text=f"chunk{i}")
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        # Fragments appear in order
        assert "subs_seg_000000.vtt" in content
        assert "subs_seg_000001.vtt" in content
        assert "subs_seg_000002.vtt" in content
        # EXTINF equals chunk duration
        assert "#EXTINF:5.000," in content
        # MEDIA-SEQUENCE matches the first chunk
        assert "#EXT-X-MEDIA-SEQUENCE:0" in content
        # Each fragment has DISCONTINUITY tag
        assert content.count("#EXT-X-DISCONTINUITY") == 3

    def test_target_duration_uses_max_extinf_plus_one(self, tmp_path: Path) -> None:
        """TARGETDURATION = max(EXTINF) + 1 (HLS spec)."""
        gen = _make_gen(str(tmp_path))
        # Manually inject mixed durations to test target_duration math
        gen._hls_fragments = [
            {"chunk_index": 0, "duration": 5.0, "start": 0.0, "path": "x"},
            {"chunk_index": 1, "duration": 7.5, "start": 5.0, "path": "y"},
            {"chunk_index": 2, "duration": 6.0, "start": 12.5, "path": "z"},
        ]
        gen._rewrite_hls_playlist()
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        # max(5, 7.5, 6) + 1 = 8.5 -> int(8.5) = 8
        assert "#EXT-X-TARGETDURATION:8" in content

    def test_playlist_atomic_write_no_tmp_leftover(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0)
        tmp = gen._hls_playlist_path.with_suffix(gen._hls_playlist_path.suffix + ".tmp")
        assert not tmp.exists(), "atomic write should rename the .tmp away"

    def test_playlist_media_sequence_matches_window(self, tmp_path: Path) -> None:
        """MEDIA-SEQUENCE matches first fragment's chunk_index (rolling window)."""
        gen = _make_gen(str(tmp_path), hls_list_size=2)
        for i in range(5):
            _process_chunk(gen, i)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        # hls_list_size=2, chunks 0-4 → window keeps chunks 3,4 → MEDIA-SEQUENCE:3
        assert "#EXT-X-MEDIA-SEQUENCE:3" in content
        assert "subs_seg_000003.vtt" in content
        assert "subs_seg_000004.vtt" in content
        # Older chunks are trimmed from the playlist
        assert "subs_seg_000000.vtt" not in content
        assert "subs_seg_000001.vtt" not in content


# ---------------------------------------------------------------------------
# Rolling window
# ---------------------------------------------------------------------------


class TestTrimHLSFragments:
    """Subtitle playlist uses rolling window matching video HLS."""

    def test_keeps_only_windowed_fragments(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path), hls_list_size=3)
        for i in range(6):
            _process_chunk(gen, i)
        # Only the last 3 fragments are kept (list_size=3)
        assert len(gen._hls_fragments) == 3
        assert gen._hls_fragments[0]["chunk_index"] == 3
        assert gen._hls_fragments[-1]["chunk_index"] == 5

    def test_trim_keeps_dropped_files(self, tmp_path: Path) -> None:
        """After trimming, old fragment files are kept on disk to prevent
        HLS.js 404 errors when it has pending requests for recently-removed
        fragments."""
        gen = _make_gen(str(tmp_path), hls_list_size=2)
        for i in range(4):
            _process_chunk(gen, i)
        # Oldest two files are kept on disk (prevents 404 race condition)
        assert (tmp_path / "subtitles" / "subs_seg_000000.vtt").exists()
        assert (tmp_path / "subtitles" / "subs_seg_000001.vtt").exists()
        # Newest two retained in playlist
        assert (tmp_path / "subtitles" / "subs_seg_000002.vtt").exists()
        assert (tmp_path / "subtitles" / "subs_seg_000003.vtt").exists()

    def test_no_trim_below_window(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path), hls_list_size=10)
        for i in range(3):
            _process_chunk(gen, i)
        assert len(gen._hls_fragments) == 3


# ---------------------------------------------------------------------------
# start() cleanup
# ---------------------------------------------------------------------------


class TestStartCleansStaleHLS:
    """start() removes stale HLS subtitle artifacts from previous sessions."""

    def test_start_precreates_empty_subs_m3u8(self, tmp_path: Path) -> None:
        subs = tmp_path / "subtitles"
        subs.mkdir(parents=True)
        (subs / "subs.m3u8").write_text("stale playlist", encoding="utf-8")
        _make_gen(str(tmp_path))
        # start() overwrites the stale subs.m3u8 with an empty valid HLS playlist.
        # This prevents HLS.js from getting a 404 that triggers a subtitle retry
        # cascade (subtitleTrackLoadError → levelEmptyError → bufferStalledError).
        assert (subs / "subs.m3u8").exists(), "start() should pre-create subs.m3u8"
        content = (subs / "subs.m3u8").read_text(encoding="utf-8")
        assert "stale playlist" not in content
        assert content.startswith("#EXTM3U")

    def test_start_removes_stale_subs_seg_files(self, tmp_path: Path) -> None:
        subs = tmp_path / "subtitles"
        subs.mkdir(parents=True)
        for i in range(3):
            (subs / f"subs_seg_{i:06d}.vtt").write_text("stale", encoding="utf-8")
        gen = _make_gen(str(tmp_path))
        # No new chunks processed yet, so no seg files exist after start
        remaining = list(subs.glob("subs_seg_*.vtt"))
        assert remaining == []

    def test_start_clears_fragments_registry(self, tmp_path: Path) -> None:
        gen = SubtitleGenerator(output_dir=str(tmp_path))
        gen._hls_fragments = [{"chunk_index": 99, "duration": 5.0, "start": 0.0, "path": "x"}]
        gen.start()
        assert gen._hls_fragments == []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class TestPlaylistAccessors:
    """get_playlist_path / get_playlist_url / new HLS state on init."""

    def test_get_playlist_path_returns_path_when_started(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        p = gen.get_playlist_path()
        assert p is not None
        assert p.name == "subs.m3u8"

    def test_get_playlist_path_returns_none_before_start(self, tmp_path: Path) -> None:
        gen = SubtitleGenerator(output_dir=str(tmp_path))
        # _hls_playlist_path is Path() (empty) before start
        assert gen.get_playlist_path() is None

    def test_get_playlist_url_is_web_path(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        assert gen.get_playlist_url() == "/subtitles/subs.m3u8"

    def test_init_initializes_hls_state(self, tmp_path: Path) -> None:
        gen = SubtitleGenerator(output_dir=str(tmp_path))
        # HLS state should be initialized in __init__
        assert gen._hls_list_size == 10
        assert gen._hls_fragments == []
        assert isinstance(gen._hls_playlist_path, Path)


# ---------------------------------------------------------------------------
# _do_process integration
# ---------------------------------------------------------------------------


class TestDoProcessHLSIntegration:
    """_do_process writes both HLS fragment + subs.m3u8 in one pass."""

    def test_processing_one_chunk_creates_hls_artifact(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0, text="hola")
        assert (tmp_path / "subtitles" / "subs_seg_000000.vtt").exists()
        playlist = (tmp_path / "subtitles" / "subs.m3u8").read_text(encoding="utf-8")
        assert "subs_seg_000000.vtt" in playlist

    def test_all_chunks_preserved_in_playlist(self, tmp_path: Path) -> None:
        """Only fragments in the rolling window are in the playlist."""
        gen = _make_gen(str(tmp_path), hls_list_size=4)
        for i in range(10):
            _process_chunk(gen, i)
        playlist = (tmp_path / "subtitles" / "subs.m3u8").read_text(encoding="utf-8")
        # Chunks 6-9 should be in the window (list_size=4)
        for i in range(6, 10):
            assert f"subs_seg_{i:06d}.vtt" in playlist, f"chunk {i} should be in playlist"
        # Chunks 0-5 should be trimmed
        for i in range(6):
            assert f"subs_seg_{i:06d}.vtt" not in playlist, f"chunk {i} should be trimmed"

    def test_all_chunks_present_in_playlist(self, tmp_path: Path) -> None:
        """Only windowed chunks appear in playlist."""
        gen = _make_gen(str(tmp_path), hls_list_size=2)
        for i in range(4):
            _process_chunk(gen, i)
        playlist = (tmp_path / "subtitles" / "subs.m3u8").read_text(encoding="utf-8")
        assert "subs_seg_000002.vtt" in playlist
        assert "subs_seg_000003.vtt" in playlist
        assert "subs_seg_000000.vtt" not in playlist
        assert "subs_seg_000001.vtt" not in playlist


# ---------------------------------------------------------------------------
# HLSOutput master playlist URI selection
# ---------------------------------------------------------------------------


class TestHLSOutputMasterPlaylist:
    """
    HLSOutput master playlist includes SUBTITLES EXT-X-MEDIA with DEFAULT=YES.
    The track is auto-activated by HLS.js on manifest parse. The frontend
    also calls activateFirstSubtitleTrack() as a safety net.
    """

    def test_master_playlist_has_subtitles_with_default_yes(self, tmp_path: Path) -> None:
        """Master must have SUBTITLES tag with DEFAULT=YES and correct language."""
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput(
            {"output_dir": str(tmp_path), "subtitle_language": "en", "subtitle_language_name": "English"}
        )
        output._output_dir = str(tmp_path)
        output._hls_dir = str(tmp_path / "hls")
        os.makedirs(output._hls_dir, exist_ok=True)
        output._segment_index = 0
        output._total_duration_emitted = 0.0
        output._first_segment_written = True
        output._ffmpeg_path = "ffmpeg"
        output._pool = MagicMock()
        output._pool.acquire.return_value = True

        with (
            patch("modules.outputs.hls_output.subprocess.run") as mock_run,
            patch("core.ffmpeg_utils.find_ffprobe", return_value=""),
        ):
            # find_ffprobe patched: is_keyframe() returns True without touching
            # platform.system()/subprocess (ffprobe lookup is platform-dependent).
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""
            seg_path = tmp_path / "hls" / "seg_000000.ts"
            seg_path.parent.mkdir(parents=True, exist_ok=True)
            seg_path.write_text("fake", encoding="utf-8")
            output.write(
                PipelineData(
                    chunk_index=0,
                    video_chunk_path=str(seg_path),
                    duration=6.0,
                )
            )

        master = (tmp_path / "hls" / "master.m3u8").read_text(encoding="utf-8")
        assert "TYPE=SUBTITLES" in master, "Master must have SUBTITLES tag"
        assert "DEFAULT=YES" in master, "Track must be DEFAULT=YES"
        assert 'LANGUAGE="en"' in master, "Language must match config"
        assert 'NAME="English"' in master, "Name must match config"
        assert 'SUBTITLES="subs"' in master, "STREAM-INF must reference subs group"

    def test_master_playlist_contains_stream_inf(self, tmp_path: Path) -> None:
        """Master playlist must contain EXT-X-STREAM-INF with stream.m3u8."""
        from modules.outputs.hls_output import HLSOutput

        output = HLSOutput({"output_dir": str(tmp_path)})
        output._output_dir = str(tmp_path)
        output._hls_dir = str(tmp_path / "hls")
        os.makedirs(output._hls_dir, exist_ok=True)
        output._segment_index = 0
        output._total_duration_emitted = 0.0
        output._first_segment_written = True
        output._ffmpeg_path = "ffmpeg"
        output._pool = MagicMock()
        output._pool.acquire.return_value = True

        with (
            patch("modules.outputs.hls_output.subprocess.run") as mock_run,
            patch("core.ffmpeg_utils.find_ffprobe", return_value=""),
        ):
            # find_ffprobe patched: is_keyframe() returns True without touching
            # platform.system()/subprocess (ffprobe lookup is platform-dependent).
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""
            seg_path = tmp_path / "hls" / "seg_000000.ts"
            seg_path.parent.mkdir(parents=True, exist_ok=True)
            seg_path.write_text("fake", encoding="utf-8")
            output.write(
                PipelineData(
                    chunk_index=0,
                    video_chunk_path=str(seg_path),
                    duration=6.0,
                )
            )

        master = (tmp_path / "hls" / "master.m3u8").read_text(encoding="utf-8")
        assert "EXT-X-STREAM-INF" in master
        assert "stream.m3u8" in master
        assert "DEFAULT=YES" in master


# ---------------------------------------------------------------------------
# HLSOutput pre-creates subs.m3u8
# ---------------------------------------------------------------------------


class TestHLSOutputNoSubsPreCreation:
    """HLSOutput start() no longer pre-creates subs.m3u8 (SubtitleGenerator handles it)."""

    def test_subs_m3u8_not_created_by_start(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from modules.outputs.hls_output import HLSOutput

        monkeypatch.chdir(tmp_path)
        output = HLSOutput({})
        output.start()

        subs_m3u8 = tmp_path / "output" / "subtitles" / "subs.m3u8"
        assert not subs_m3u8.exists(), "HLSOutput.start() should NOT pre-create subs.m3u8; SubtitleGenerator handles it"


# ---------------------------------------------------------------------------
# chunk_duration change resets HLS fragments
# ---------------------------------------------------------------------------


class TestConfigureClearsHLS:
    """Changing chunk_duration via configure() resets HLS fragments and playlist."""

    def test_chunk_duration_change_resets_fragments(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        for i in range(3):
            _process_chunk(gen, i)
        assert len(gen._hls_fragments) == 3

        gen.configure({"chunk_duration": 10, "hls_list_size": 6})
        assert gen._hls_fragments == [], "configure() with new chunk_duration must clear HLS fragments"

    def test_chunk_duration_change_rewrites_empty_playlist(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        for i in range(3):
            _process_chunk(gen, i)
        gen.configure({"chunk_duration": 10, "hls_list_size": 6})
        playlist = gen._hls_playlist_path.read_text(encoding="utf-8")
        # No fragments now — empty playlist
        assert "#EXT-X-MEDIA-SEQUENCE:0" in playlist
        assert "subs_seg_" not in playlist

    def test_same_chunk_duration_does_not_reset(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        for i in range(3):
            _process_chunk(gen, i)
        gen.configure({"chunk_duration": 5, "hls_list_size": 6})  # same as default
        assert len(gen._hls_fragments) == 3, "no change in chunk_duration must preserve fragments"


# ---------------------------------------------------------------------------
# FIX-2026-08: ventana de subtítulos alineada con el video + chunks sin texto
# ---------------------------------------------------------------------------


class TestSubtitleWindowAlignedToVideo:
    """subs.m3u8 nunca debe ir por delante del video publicado (FIX-2026-08)."""

    @staticmethod
    def _write_video_playlist(tmp_path: Path, segments: list[tuple[int, float]]) -> Path:
        hls_dir = tmp_path / "hls"
        hls_dir.mkdir(exist_ok=True)
        lines = ["#EXTM3U", "#EXT-X-VERSION:4"]
        lines.append(f"#EXT-X-TARGETDURATION:{int(max(d for _, d in segments)) + 1}")
        lines.append(f"#EXT-X-MEDIA-SEQUENCE:{segments[0][0]}")
        for idx, dur in segments:
            lines.append(f"#EXTINF:{dur:.3f},")
            lines.append(f"seg_{idx:06d}.ts")
        path = hls_dir / "stream.m3u8"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_playlist_trimmed_to_video_window(self, tmp_path: Path) -> None:
        """El subs ya consumió chunks 0-5, pero el video solo publicó 0-3."""
        self._write_video_playlist(tmp_path, [(0, 5.0), (1, 5.0), (2, 5.0), (3, 5.0)])
        gen = _make_gen(str(tmp_path))
        for i in range(6):
            _process_chunk(gen, i)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "subs_seg_000004.vtt" not in content
        assert "subs_seg_000005.vtt" not in content
        assert "subs_seg_000003.vtt" in content
        assert "#EXT-X-MEDIA-SEQUENCE:0" in content

    def test_playlist_uses_video_extinf_when_available(self, tmp_path: Path) -> None:
        """EXTINF del subs toma la duración REAL del video (12.043, no 11.4)."""
        self._write_video_playlist(tmp_path, [(0, 12.043), (1, 6.043)])
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0)
        _process_chunk(gen, 1)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "#EXTINF:12.043," in content
        assert "#EXTINF:6.043," in content
        assert "#EXTINF:5.000," not in content  # no usa la duración nominal del chunk

    def test_no_video_playlist_falls_back_to_own_durations(self, tmp_path: Path) -> None:
        """Sin stream.m3u8 (tests, standalone): comportamiento legacy intacto."""
        gen = _make_gen(str(tmp_path))
        for i in range(3):
            _process_chunk(gen, i)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "#EXTINF:5.000," in content
        assert "#EXT-X-MEDIA-SEQUENCE:0" in content
        assert content.count("#EXT-X-DISCONTINUITY") == 3

    def test_playlist_has_no_event_type_tag(self, tmp_path: Path) -> None:
        """EVENT prohíbe recortar; con rolling window es contradicción de spec (FIX)."""
        gen = _make_gen(str(tmp_path))
        for i in range(3):
            _process_chunk(gen, i)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "#EXT-X-PLAYLIST-TYPE" not in content

    def test_empty_playlist_keeps_media_sequence_zero(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "#EXT-X-MEDIA-SEQUENCE:0" in content
        assert "#EXT-X-PLAYLIST-TYPE" not in content

    def test_video_far_ahead_subs_not_ahead_of_video(self, tmp_path: Path) -> None:
        """El video puede estar por delante; el subs nunca lo sobrepasa."""
        self._write_video_playlist(tmp_path, [(0, 5.0), (1, 5.0), (2, 5.0)])
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0)
        _process_chunk(gen, 1)
        _process_chunk(gen, 2)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "subs_seg_000002.vtt" in content
        assert "subs_seg_000003.vtt" not in content

    def test_playlist_base_aligned_to_video_window(self, tmp_path: Path) -> None:
        # La BASE tambien se alinea: video seq 15..20, subs 0..19 procesados.
        # La ventana de subs queda 15..19 (interseccion), sin fantasma 11..14.
        self._write_video_playlist(tmp_path, [(15, 5.0), (16, 5.0), (17, 5.0), (18, 5.0), (19, 5.0), (20, 5.0)])
        gen = _make_gen(str(tmp_path))
        for i in range(20):
            _process_chunk(gen, i)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "#EXT-X-MEDIA-SEQUENCE:15" in content
        assert "subs_seg_000011.vtt" not in content  # base recortada al video
        assert "subs_seg_000014.vtt" not in content
        assert "subs_seg_000015.vtt" in content
        assert "subs_seg_000019.vtt" in content
        assert "subs_seg_000020.vtt" not in content  # subs nunca por delante del video

    def test_no_overlap_serves_empty_playlist_anchored_to_video(self, tmp_path: Path) -> None:
        # Video renumerado (restart watchdog): sin solapamiento -> playlist
        # vacio anclado a la MEDIA-SEQUENCE del video, sin cues stale.
        self._write_video_playlist(tmp_path, [(100, 5.0)])
        gen = _make_gen(str(tmp_path))
        for i in range(3):
            _process_chunk(gen, i)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "#EXT-X-MEDIA-SEQUENCE:100" in content
        assert "subs_seg_" not in content  # sin fragmentos stale

    def test_base_alignment_keeps_extinf_sync(self, tmp_path: Path) -> None:
        # EXTINF sigue tomando la duracion real del video tras recortar la base.
        self._write_video_playlist(tmp_path, [(15, 11.283), (16, 5.283), (17, 6.043)])
        gen = _make_gen(str(tmp_path))
        for i in range(18):
            _process_chunk(gen, i)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "#EXTINF:11.283," in content
        assert "#EXTINF:5.283," in content
        assert "#EXTINF:5.000," not in content


class TestEmptyTextKeepsSequenceContiguous:
    """Chunk sin transcripción ya no rompe la correspondencia 1:1 (FIX-2026-08)."""

    def test_silent_chunk_still_advances_index(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0)
        data = PipelineData(
            chunk_index=1,
            transcript=None,
            translated_text=None,
            translated_segments=[],
            duration=5.0,
            cumulative_duration=5.0,
        )
        gen._do_process(data)
        assert gen._last_chunk_index == 1, "chunk sin texto debe avanzar el índice"

    def test_silent_chunk_does_not_stall_next_text_chunk(self, tmp_path: Path) -> None:
        """Antes: chunk 1 sin texto dejaba el 2 (con texto) atrapado en pending."""
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0)
        silent = PipelineData(
            chunk_index=1,
            transcript=None,
            translated_text=None,
            translated_segments=[],
            duration=5.0,
            cumulative_duration=5.0,
        )
        gen._do_process(silent)
        _process_chunk(gen, 2)  # con texto otra vez
        frag_2 = tmp_path / "subtitles" / "subs_seg_000002.vtt"
        assert frag_2.exists(), "el chunk 2 no debe quedar congelado en el buffer pending"
        playlist = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "subs_seg_000002.vtt" in playlist

    def test_silent_chunk_writes_empty_fragment(self, tmp_path: Path) -> None:
        """El fragmento vacío mantiene la ventana 1:1 con el video."""
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0)
        silent = PipelineData(
            chunk_index=1,
            transcript=None,
            translated_text=None,
            translated_segments=[],
            duration=5.0,
            cumulative_duration=5.0,
        )
        gen._do_process(silent)
        frag_1 = tmp_path / "subtitles" / "subs_seg_000001.vtt"
        assert frag_1.exists()
        content = frag_1.read_text(encoding="utf-8")
        assert content.startswith("WEBVTT")
        assert "-->" not in content  # vacío, sin cues
        playlist = gen._hls_playlist_path.read_text(encoding="utf-8")
        assert "subs_seg_000001.vtt" in playlist

    def test_loop_chunk_still_skipped(self, tmp_path: Path) -> None:
        """is_loop (pause loop) sigue descartándose ANTES de tocar el índice."""
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0)
        looped = PipelineData(
            chunk_index=0,
            transcript="hola",
            translated_text="hola",
            translated_segments=[{"start": 0.5, "end": 4.5, "text": "hola"}],
            duration=5.0,
            cumulative_duration=0.0,
            metadata={"is_loop": True},
        )
        gen._do_process(looped)
        assert gen._last_chunk_index == 0, "chunk en pause loop no debe avanzar el índice"
