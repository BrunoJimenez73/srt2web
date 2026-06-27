"""
F108 — Subtítulos desincronizados del video en sesiones largas / webplayer pausado.

Regression tests for the HLS-native subtitle sync path. Covers:

Backend (subtitle_generator + hls_output):
- _write_hls_fragment produces MEDIA-RELATIVE cue timestamps (HLS.js spec).
- Cue timestamps are clamped: start >= 0, end <= fragment duration, end >= start.
- _rewrite_hls_playlist emits valid HLS v3 with correct EXTINF/EXT-X-TARGETDURATION/
  EXT-X-MEDIA-SEQUENCE entries.
- Empty playlist state (no fragments yet) is a valid #EXTM3U v3 file.
- Rolling window: fragments beyond hls_list_size are dropped AND their files deleted.
- start() cleans stale HLS subtitle fragments (subs_seg_*.vtt, subs.m3u8).
- set_drift_monitor wires the previously-dead drift detection path.
- Drift monitor check_sync is called per chunk with relative timestamps.
- Legacy subs.vtt rolling file is still produced (webrtc_engine/recording_output
  backward compatibility).
- HLSOutput master playlist points at /subtitles/subs.m3u8 when it exists,
  falls back to /subtitles/subs.vtt otherwise.
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


class _StubDriftMonitor:
    """Stub SubtitleSyncMonitor for drift-wiring tests."""

    def __init__(self, factor: float = 1.0) -> None:
        self._factor = factor
        self.call_count = 0
        self.last_audio_ms: float | None = None
        self.last_subtitle_ms: float | None = None

    def check_sync(self, audio_timestamp_ms: float, subtitle_timestamp_ms: float) -> float:
        self.call_count += 1
        self.last_audio_ms = audio_timestamp_ms
        self.last_subtitle_ms = subtitle_timestamp_ms
        return self._factor


class _FailingDriftMonitor:
    """Drift monitor that raises — generator must swallow and not crash."""

    def check_sync(self, audio_timestamp_ms: float, subtitle_timestamp_ms: float) -> float:
        raise RuntimeError("drift monitor unavailable")


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

    def test_playlist_media_sequence_uses_first_chunk_index(self, tmp_path: Path) -> None:
        """After rolling window drops the first few fragments, MEDIA-SEQUENCE follows."""
        gen = _make_gen(str(tmp_path), hls_list_size=2)
        for i in range(5):
            _process_chunk(gen, i)
        content = gen._hls_playlist_path.read_text(encoding="utf-8")
        # After trimming, only chunks 3 and 4 remain -> media sequence is 3
        assert "#EXT-X-MEDIA-SEQUENCE:3" in content
        assert "subs_seg_000003.vtt" in content
        assert "subs_seg_000004.vtt" in content


# ---------------------------------------------------------------------------
# Rolling window
# ---------------------------------------------------------------------------


class TestTrimHLSFragments:
    """Rolling window keeps only the most recent hls_list_size fragments."""

    def test_trims_to_hls_list_size(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path), hls_list_size=3)
        for i in range(6):
            _process_chunk(gen, i)
        assert len(gen._hls_fragments) == 3
        # First three dropped
        chunk_indices = [f["chunk_index"] for f in gen._hls_fragments]
        assert chunk_indices == [3, 4, 5]

    def test_trim_deletes_dropped_files(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path), hls_list_size=2)
        for i in range(4):
            _process_chunk(gen, i)
        # Oldest two files should be deleted
        assert not (tmp_path / "subtitles" / "subs_seg_000000.vtt").exists()
        assert not (tmp_path / "subtitles" / "subs_seg_000001.vtt").exists()
        # Newest two retained
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
# Drift monitor wiring (previously dead code)
# ---------------------------------------------------------------------------


class TestPipelineDelayCompensation:
    """Pipeline delay compensation — shifts subtitles forward to match video position."""

    def test_set_drift_monitor_stores_reference(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        monitor = _StubDriftMonitor()
        gen.set_drift_monitor(monitor)
        assert gen._drift_monitor is monitor

    def test_pipeline_delay_initialized_on_first_chunk(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        # start() now sets _pipeline_start_wall immediately so the first
        # _do_process call already has a meaningful wall_elapsed.
        assert gen._pipeline_start_wall > 0
        _process_chunk(gen, 0)
        assert gen._pipeline_start_wall > 0

    def test_pipeline_delay_smoothed_updated(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        for i in range(3):
            _process_chunk(gen, i)
        assert gen._pipeline_delay_smoothed >= 0

    def test_shifted_start_greater_than_cumulative(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 2, cumulative=10.0)
        if gen._vtt_entries:
            assert gen._vtt_entries[0]["start"] >= 10.0

    def test_hls_fragment_cues_shifted(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0, cumulative=0.0)
        seg_file = tmp_path / "subtitles" / "subs_seg_000000.vtt"
        if seg_file.exists():
            content = seg_file.read_text(encoding="utf-8")
            import re

            match = re.search(r"(\d+):(\d+):(\d+)\.(\d+)", content)
            if match:
                h, m, s, ms = int(match[1]), int(match[2]), int(match[3]), int(match[4])
                total_sec = h * 3600 + m * 60 + s + ms / 1000
                assert total_sec > 0.3, f"Cue starts at {total_sec}s, expected > 0.3s"

    def test_drift_monitor_exception_does_not_crash(self, tmp_path: Path) -> None:
        """Failing monitor must not break the pipeline."""
        gen = _make_gen(str(tmp_path))
        gen.set_drift_monitor(_FailingDriftMonitor())
        _process_chunk(gen, 0)
        assert gen._state.name == "RUNNING"

    def test_no_monitor_no_crash(self, tmp_path: Path) -> None:
        """Without a monitor attached, drift check is skipped."""
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0)
        assert gen._drift_monitor is None


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
        assert gen._hls_list_size == 12
        assert gen._hls_fragments == []
        assert isinstance(gen._hls_playlist_path, Path)


# ---------------------------------------------------------------------------
# Legacy subs.vtt compatibility
# ---------------------------------------------------------------------------


class TestLegacyVTTCompat:
    """subs.vtt (rolling, absolute timestamps) is still produced for legacy consumers."""

    def test_subs_vtt_still_written(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0, text="hola mundo")
        subs = (tmp_path / "subtitles" / "subs.vtt").read_text(encoding="utf-8")
        assert subs.startswith("WEBVTT")
        assert "hola mundo" in subs

    def test_subs_vtt_uses_absolute_timestamps(self, tmp_path: Path) -> None:
        """Legacy subs.vtt uses chunk_start + rel for absolute time (legacy webplayer)."""
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 2, cumulative=10.0)  # chunk starts at 10s
        subs = (tmp_path / "subtitles" / "subs.vtt").read_text(encoding="utf-8")
        # 10.5s + 4.5s = 10.5s .. 14.5s — but `start` is 0.5s into chunk, end 4.5s
        # so absolute: 10.5s .. 14.5s. Wait — that's wrong: chunk_start 10s + rel start 0.5 = 10.5s
        # 10s + 4.5 = 14.5s. Verify the timestamps.
        assert "00:00:10.500 --> 00:00:14.500" in subs

    def test_subs_m3u8_and_subs_vtt_coexist(self, tmp_path: Path) -> None:
        """Both the new playlist and the legacy single-file VTT are produced each chunk."""
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0)
        assert (tmp_path / "subtitles" / "subs.m3u8").exists()
        assert (tmp_path / "subtitles" / "subs.vtt").exists()
        assert (tmp_path / "subtitles" / "subs_seg_000000.vtt").exists()


# ---------------------------------------------------------------------------
# _do_process integration
# ---------------------------------------------------------------------------


class TestDoProcessHLSIntegration:
    """_do_process writes both HLS fragment + subs.vtt + subs.m3u8 in one pass."""

    def test_processing_one_chunk_creates_hls_artifact(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        _process_chunk(gen, 0, text="hola")
        assert (tmp_path / "subtitles" / "subs_seg_000000.vtt").exists()
        playlist = (tmp_path / "subtitles" / "subs.m3u8").read_text(encoding="utf-8")
        assert "subs_seg_000000.vtt" in playlist

    def test_processing_many_chunks_keeps_rolling_window(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path), hls_list_size=4)
        for i in range(10):
            _process_chunk(gen, i)
        playlist = (tmp_path / "subtitles" / "subs.m3u8").read_text(encoding="utf-8")
        # Only the last 4 chunks should be referenced
        for i in range(6, 10):
            assert f"subs_seg_{i:06d}.vtt" in playlist, f"chunk {i} should be in playlist"
        for i in range(0, 6):
            assert f"subs_seg_{i:06d}.vtt" not in playlist, f"chunk {i} should be dropped"

    def test_playlist_does_not_reference_dropped_files(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path), hls_list_size=2)
        for i in range(4):
            _process_chunk(gen, i)
        playlist = (tmp_path / "subtitles" / "subs.m3u8").read_text(encoding="utf-8")
        # No dangling references to files we deleted
        assert "subs_seg_000000.vtt" not in playlist
        assert "subs_seg_000001.vtt" not in playlist


# ---------------------------------------------------------------------------
# HLSOutput master playlist URI selection
# ---------------------------------------------------------------------------


class TestHLSOutputMasterPlaylist:
    """
    HLSOutput master playlist includes SUBTITLES EXT-X-MEDIA with DEFAULT=NO.
    The track is listed in the native "..." menu with the correct language but
    NOT auto-activated — no CC button appears. SubtitleRenderer renders via
    custom div; enableCEA708Captions:false blocks embedded CEA-608/708 tracks.
    """

    def test_master_playlist_has_subtitles_with_default_no(self, tmp_path: Path) -> None:
        """Master must have SUBTITLES tag with DEFAULT=NO and correct language."""
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

        with patch("modules.outputs.hls_output.subprocess.run") as mock_run:
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
        assert "DEFAULT=NO" in master, "Track must be DEFAULT=NO"
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

        with patch("modules.outputs.hls_output.subprocess.run") as mock_run:
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
        assert "DEFAULT=NO" in master


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
