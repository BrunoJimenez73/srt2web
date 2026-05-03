"""
Unit tests for SubtitleGenerator module.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.module_base import ModuleState, PipelineData
from modules.subtitle_generator import SubtitleGenerator


@pytest.fixture
def temp_dir():  # type: ignore
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestSubtitleGenerator:
    """Tests for SubtitleGenerator class."""

    def test_init(self) -> None:
        """Test initialization and config."""
        gen = SubtitleGenerator(output_dir="/tmp")
        assert gen._use_translated is True
        assert gen._format == "webvtt"

    @patch("os.makedirs")
    def test_start(self, mock_makedirs) -> None:
        """Test module startup."""
        with patch("builtins.open", mock_open()) as mocked_file:
            gen = SubtitleGenerator(output_dir="/tmp")
            gen.start()

            assert gen.state == ModuleState.RUNNING
            mock_makedirs.assert_called()
            mocked_file.assert_called_with(os.path.join("/tmp", "subtitles", "subs.vtt"), "w", encoding="utf-8")
            mocked_file().write.assert_called_once_with("WEBVTT\n\n")

    def test_format_timestamp(self) -> None:
        """Test timestamp formatting for VTT and SRT."""
        gen = SubtitleGenerator()
        vtt_ts = gen._format_timestamp(3661.123, "vtt")
        assert vtt_ts == "01:01:01.123"
        srt_ts = gen._format_timestamp(3661.123, "srt")
        assert srt_ts == "01:01:01,123"

    def test_do_process_vtt(self, temp_dir) -> None:
        """Test processing to generate VTT content."""
        gen = SubtitleGenerator(output_dir=temp_dir)
        gen.start()

        data = PipelineData(chunk_index=0, duration=4.0)
        data.translated_text = "Hola Mundo"
        data.translated_segments = [{"start": 0.0, "end": 3.5, "text": "Hola Mundo"}]

        result = gen._do_process(data)

        assert result.subtitles_path is not None
        assert os.path.exists(gen._vtt_path)

        with open(gen._vtt_path, encoding="utf-8") as f:
            content = f.read()
        assert "WEBVTT" in content
        assert "Hola Mundo" in content

    def test_do_process_no_text(self) -> None:
        """Test processing when no text is available."""
        gen = SubtitleGenerator(output_dir="/tmp")
        gen._vtt_path = os.path.join("/tmp", "hls", "subs.vtt")

        data = PipelineData(chunk_index=0, transcript=None)
        result = gen._do_process(data)

        assert result.subtitles_path == gen._vtt_path

    def test_do_process_use_original_transcript(self, temp_dir) -> None:
        """Test using transcript when translation is disabled."""
        gen = SubtitleGenerator(output_dir=temp_dir)
        gen.configure({"use_translated": False})
        gen.start()

        data = PipelineData(chunk_index=0, duration=4.0, transcript="Hello")
        data.translated_text = "Hola"
        data.transcript_segments = [{"start": 0.0, "end": 3.0, "text": "Hello"}]

        gen._do_process(data)

        with open(gen._vtt_path, encoding="utf-8") as f:
            content = f.read()
        assert "Hello" in content


class TestSubtitleGeneratorTiming:
    """Tests for subtitle timing synchronization."""

    def test_last_cumulative_reset_on_start(self, temp_dir) -> None:
        """Test that last cumulative is reset when module starts."""
        gen = SubtitleGenerator(output_dir=temp_dir)
        gen._last_cumulative = 100.0

        gen.start()

        assert gen._last_cumulative == 0.0
        assert gen._last_chunk_index == -1

    def test_cumulative_time_uses_data_cumulative_duration(self, temp_dir) -> None:
        """Test that chunk_start_time uses data.cumulative_duration."""
        gen = SubtitleGenerator(output_dir=temp_dir)
        gen.start()

        data = PipelineData(chunk_index=0, duration=4.0)
        data.cumulative_duration = 0.0
        data.translated_text = "Test"
        data.translated_segments = [{"start": 0, "end": 4, "text": "Test"}]

        gen._do_process(data)

        # After processing, last_cumulative should match data.cumulative_duration
        assert gen._last_cumulative == 0.0

    def test_cumulative_time_increases_with_chunks(self, temp_dir) -> None:
        """Test that cumulative time increases correctly across chunks."""
        gen = SubtitleGenerator(output_dir=temp_dir)
        gen.start()

        for i in range(3):
            data = PipelineData(chunk_index=i, duration=4.0)
            data.cumulative_duration = i * 4.0
            data.translated_text = f"Test {i}"
            data.translated_segments = [{"start": 0, "end": 4, "text": f"Test {i}"}]
            gen._do_process(data)

        # Last cumulative should be 8.0 (from chunk 2)
        assert gen._last_cumulative == 8.0

    def test_segments_timing_relative_to_chunk(self, temp_dir) -> None:
        """Test that segment timestamps use cumulative_duration from data."""
        gen = SubtitleGenerator(output_dir=temp_dir)
        gen.start()

        # Process chunk 0
        data0 = PipelineData(chunk_index=0, duration=10.0)
        data0.cumulative_duration = 0.0
        data0.translated_text = "Test 0"
        data0.translated_segments = [{"start": 0, "end": 10, "text": "Test 0"}]
        gen._do_process(data0)

        # Process chunk 1
        data1 = PipelineData(chunk_index=1, duration=10.0)
        data1.cumulative_duration = 10.0
        data1.translated_text = "Test 1"
        data1.translated_segments = [{"start": 0, "end": 10, "text": "Test 1"}]
        gen._do_process(data1)

        # Process chunk 2 with specific segment timing
        data2 = PipelineData(chunk_index=2, duration=10.0)
        data2.cumulative_duration = 20.0
        data2.translated_text = "Test"
        data2.translated_segments = [
            {"start": 0.5, "end": 2.5, "text": "First segment"},
            {"start": 3.0, "end": 5.0, "text": "Second segment"},
        ]
        gen._do_process(data2)

        # Read the VTT file
        with open(gen._vtt_path, encoding="utf-8") as f:
            content = f.read()

        # SubtitleGenerator uses absolute cumulative timing (cumulative_duration + segment start)
        # Segment at 0.5 + cumulative 20.0 → 00:00:20.500
        assert "00:00:20.500" in content
        # Segment at 3.0 + cumulative 20.0 → 00:00:23.000
        assert "00:00:23.000" in content


class TestRollingWindow:
    """Tests for rolling window VTT functionality."""

    def test_trim_vtt_entries_limits_count(self) -> None:
        """Test that _trim_vtt_entries limits entry count."""
        gen = SubtitleGenerator()
        gen._max_vtt_entries = 5

        gen._vtt_entries = [{"start": float(i), "end": float(i + 1), "text": f"Entry {i}"} for i in range(10)]

        gen._trim_vtt_entries()
        assert len(gen._vtt_entries) == 5

    def test_trim_vtt_entries_removes_old_by_time(self) -> None:
        """Test that _trim_vtt_entries removes entries older than max age."""
        gen = SubtitleGenerator()
        gen._vtt_max_age_seconds = 10.0
        gen._max_vtt_entries = 100

        gen._vtt_entries = [
            {"start": 0.0, "end": 5.0, "text": "Old entry"},
            {"start": 100.0, "end": 105.0, "text": "Recent entry"},
        ]

        gen._trim_vtt_entries()

        assert len(gen._vtt_entries) == 1
        assert gen._vtt_entries[0]["text"] == "Recent entry"

    def test_rewrite_vtt_file(self, temp_dir) -> None:
        """Test that _rewrite_vtt_file writes correct VTT format."""
        gen = SubtitleGenerator(output_dir=temp_dir)
        gen._subtitles_dir = temp_dir
        gen._vtt_path = os.path.join(temp_dir, "test.vtt")

        gen._vtt_entries = [
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 2.0, "end": 4.0, "text": "World"},
        ]

        gen._rewrite_vtt_file()

        assert os.path.exists(gen._vtt_path)
        with open(gen._vtt_path, encoding="utf-8") as f:
            content = f.read()

        assert content.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.000" in content
        assert "Hello" in content
        assert "00:00:02.000 --> 00:00:04.000" in content
        assert "World" in content

    def test_start_clears_rolling_window(self, temp_dir) -> None:
        """Test that start() clears the rolling window."""
        gen = SubtitleGenerator(output_dir=temp_dir)
        gen._vtt_entries = [{"start": 0, "end": 1, "text": "test"}]

        gen.start()

        assert gen._vtt_entries == []
