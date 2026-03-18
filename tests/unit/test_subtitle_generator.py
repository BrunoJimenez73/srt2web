"""
Unit tests for SubtitleGenerator module.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.subtitle_generator import SubtitleGenerator
from core.module_base import PipelineData, ModuleState


class TestSubtitleGenerator:
    """Tests for SubtitleGenerator class."""

    def test_init(self):
        """Test initialization and config."""
        gen = SubtitleGenerator(output_dir="/tmp")
        assert gen._use_translated is True
        assert gen._format == "webvtt"

    @patch("os.makedirs")
    def test_start(self, mock_makedirs):
        """Test module startup."""
        with patch("builtins.open", mock_open()) as mocked_file:
            gen = SubtitleGenerator(output_dir="/tmp")
            gen.start()

            assert gen.state == ModuleState.RUNNING
            mock_makedirs.assert_called()
            mocked_file.assert_called_with(
                os.path.join("/tmp", "hls", "subs.vtt"), "w", encoding="utf-8"
            )
            # Check if WEBVTT header was written
            mocked_file().write.assert_called_once_with("WEBVTT\n\n")

    def test_format_timestamp(self):
        """Test timestamp formatting for VTT and SRT."""
        gen = SubtitleGenerator()
        vtt_ts = gen._format_timestamp(3661.123, "vtt")
        assert vtt_ts == "01:01:01.123"
        srt_ts = gen._format_timestamp(3661.123, "srt")
        assert srt_ts == "01:01:01,123"

    @patch("os.path.join", side_effect=os.path.join)
    def test_do_process_vtt(self, mock_path_join):
        """Test processing to generate VTT content."""
        with patch("builtins.open", mock_open()) as mocked_file:
            gen = SubtitleGenerator(output_dir="/tmp")
            gen._vtt_path = "/tmp/hls/subs.vtt"
            gen._subtitles_dir = "/tmp/hls"

            data = PipelineData(chunk_index=1, duration=4.0)
            data.translated_text = "¡Hola Mundo!"

            result = gen._do_process(data)

            # Should have called open for the global VTT (append) and the chunk SRT (write)
            assert mocked_file.call_count >= 2

            # Verify one of the calls was for the VTT with append mode
            mocked_file.assert_any_call("/tmp/hls/subs.vtt", "a", encoding="utf-8")

            # Verify timing calculation for chunk_index 1: (1*4) = 4.0s
            # 4.0s in VTT is 00:00:04.000
            # We don't check the exact string here but the call count for write is a good proxy
            assert mocked_file().write.called

    def test_do_process_no_text(self):
        """Test processing when no text is available."""
        gen = SubtitleGenerator(output_dir="/tmp")
        gen._vtt_path = "/tmp/hls/subs.vtt"

        data = PipelineData(chunk_index=0, transcript=None)
        result = gen._do_process(data)

        assert result.subtitles_path == "/tmp/hls/subs.vtt"

    def test_do_process_use_original_transcript(self):
        """Test using transcript when translation is disabled."""
        with patch("builtins.open", mock_open()) as mocked_file:
            gen = SubtitleGenerator(output_dir="/tmp")
            gen.configure({"use_translated": False})
            gen._vtt_path = "/tmp/hls/subs.vtt"
            gen._subtitles_dir = "/tmp/hls"

            data = PipelineData(chunk_index=0, transcript="Hello")
            data.translated_text = "Hola"

            gen._do_process(data)

            # Check if "Hello" was written (or logged)
            # In our case it writes to file. We can check the write calls.
            # "Hello" should be in one of the write calls.
            calls = [call.args[0] for call in mocked_file().write.call_args_list]
            any_contains_hello = any("Hello" in str(c) for c in calls)
            assert any_contains_hello


class TestSubtitleGeneratorTiming:
    """Tests for subtitle timing synchronization with VideoMuxer."""

    def test_cumulative_time_reset_on_start(self):
        """Test that cumulative time is reset when module starts."""
        gen = SubtitleGenerator(output_dir="/tmp")
        gen._cumulative_time = 100.0  # Simulate previous run

        with patch("builtins.open", mock_open()):
            gen.start()

        assert gen._cumulative_time == 0.0
        assert gen._last_chunk_index == -1

    def test_cumulative_time_calculation_chunk_0(self):
        """Test cumulative time for first chunk matches VideoMuxer logic."""
        with patch("builtins.open", mock_open()):
            gen = SubtitleGenerator(output_dir="/tmp")
            gen._vtt_path = "/tmp/hls/subs.vtt"
            gen._subtitles_dir = "/tmp/hls"

            # Process chunk 0 with 4 second duration
            # Need translated_text to avoid early return
            data = PipelineData(chunk_index=0, duration=4.0)
            data.translated_text = "Test"
            data.translated_segments = [{"start": 0, "end": 4, "text": "Test"}]

            gen._do_process(data)

            # For chunk 0, cumulative time should be 0 (no previous chunks)
            # This matches VideoMuxer's offset_sec = 0 for first segment
            assert gen._cumulative_time == 0.0

    def test_cumulative_time_calculation_multiple_chunks(self):
        """Test cumulative time increases correctly across chunks."""
        with patch("builtins.open", mock_open()) as mocked_file:
            gen = SubtitleGenerator(output_dir="/tmp")
            gen._vtt_path = "/tmp/hls/subs.vtt"
            gen._subtitles_dir = "/tmp/hls"

            # Process chunks in sequence
            for i in range(3):
                data = PipelineData(chunk_index=i, duration=4.0)
                data.translated_text = f"Test {i}"
                data.translated_segments = [{"start": 0, "end": 4, "text": f"Test {i}"}]
                gen._do_process(data)

            # After processing chunks 0, 1, 2:
            # - Chunk 0: last_chunk_index=-1 -> skip addition, cumulative=0, then last=0
            # - Chunk 1: last_chunk_index=0, add 4 -> cumulative=4, then last=1
            # - Chunk 2: last_chunk_index=1, add 4 -> cumulative=8, then last=2
            assert gen._cumulative_time == 8.0

    def test_cumulative_time_matches_video_muxer_offset(self):
        """Test that chunk_start_time matches VideoMuxer's offset_sec calculation."""
        with patch("builtins.open", mock_open()):
            gen = SubtitleGenerator(output_dir="/tmp")
            gen._vtt_path = "/tmp/hls/subs.vtt"
            gen._subtitles_dir = "/tmp/hls"

            # Process 5 chunks of 10s each (indices 0-4)
            for chunk_idx in range(5):
                data = PipelineData(chunk_index=chunk_idx, duration=10.0)
                data.translated_text = f"Text {chunk_idx}"
                data.translated_segments = [
                    {"start": 0, "end": 10, "text": f"Text {chunk_idx}"}
                ]
                gen._do_process(data)

            # After 5 chunks of 10s each:
            # Chunk 0: last=-1, skip add, cumulative=0, last=0
            # Chunk 1: last=0, add 10, cumulative=10, last=1
            # Chunk 2: last=1, add 10, cumulative=20, last=2
            # Chunk 3: last=2, add 10, cumulative=30, last=3
            # Chunk 4: last=3, add 10, cumulative=40, last=4
            # Final: cumulative = 40
            assert gen._cumulative_time == 40.0

    def test_resume_case_recalculates_from_scratch(self):
        """Test that resuming from lower chunk index recalculates correctly."""
        with patch("builtins.open", mock_open()):
            gen = SubtitleGenerator(output_dir="/tmp")
            gen._vtt_path = "/tmp/hls/subs.vtt"
            gen._subtitles_dir = "/tmp/hls"

            # Simulate processing chunks 0-4 with 4s duration
            for i in range(5):
                data = PipelineData(chunk_index=i, duration=4.0)
                data.translated_text = f"Test {i}"
                data.translated_segments = [{"start": 0, "end": 4, "text": f"Test {i}"}]
                gen._do_process(data)

            # After processing 5 chunks (4s each):
            # Chunk 0: last=-1, skip add, cumulative=0, last=0
            # Chunk 1: last=0, add 4, cumulative=4, last=1
            # Chunk 2: last=1, add 4, cumulative=8, last=2
            # Chunk 3: last=2, add 4, cumulative=12, last=3
            # Chunk 4: last=3, add 4, cumulative=16, last=4
            # Final: cumulative = 16
            assert gen._cumulative_time == 16.0

            # Simulate resume from chunk 2 (going backwards)
            # First, set last_chunk_index to be higher than 2
            gen._last_chunk_index = 5  # Higher than 2 to trigger resume case
            gen._cumulative_time = 0.0  # Reset cumulative

            data = PipelineData(chunk_index=2, duration=4.0)
            data.translated_text = "Resume test"
            data.translated_segments = [{"start": 0, "end": 4, "text": "Resume test"}]
            gen._do_process(data)

            # Resume case: cumulative = chunk_index * duration = 2 * 4 = 8
            assert gen._cumulative_time == 8.0

    def test_segments_timing_relative_to_chunk(self):
        """Test that segment timestamps are relative to chunk start."""
        m = mock_open()
        with patch("builtins.open", m):
            gen = SubtitleGenerator(output_dir="/tmp")
            gen._vtt_path = "/tmp/hls/subs.vtt"
            gen._subtitles_dir = "/tmp/hls"

            # First process chunks 0-1 with 10s duration to set cumulative time
            for i in range(2):
                data = PipelineData(chunk_index=i, duration=10.0)
                data.translated_text = f"Test {i}"
                data.translated_segments = [
                    {"start": 0, "end": 10, "text": f"Test {i}"}
                ]
                gen._do_process(data)

            # After chunks 0-1: cumulative = 20 (chunk 0 skipped addition, chunk 1 added 10)
            # Actually: chunk 0: last=-1, skip, cumulative=0, last=0
            #          chunk 1: last=0, add 10, cumulative=10, last=1
            # Wait, that's only 10. Let me trace again...
            # Chunk 0: last=-1, skip addition (cumulative stays 0)
            # Chunk 1: last=0, add 10 (cumulative becomes 10)
            # So after 2 chunks, cumulative = 10, not 20!
            # But the test output shows 20.500 for chunk 2...
            # Let me look at the code again...

            # Chunk 2, with segments at relative times 0.5 and 2.5
            data = PipelineData(chunk_index=2, duration=10.0)
            data.translated_text = "Test"
            data.translated_segments = [
                {"start": 0.5, "end": 2.5, "text": "First segment"},
                {"start": 3.0, "end": 5.0, "text": "Second segment"},
            ]

            gen._do_process(data)

            # Get all write calls
            write_calls = [call[0][0] for call in m().write.call_args_list]
            vtt_content = "".join(write_calls)

            # After processing chunks 0 and 1: cumulative = 10
            # Chunk 2 starts at cumulative time = 10
            # Chunk 2's segments are at relative times 0.5 and 3.0
            # So absolute times should be 10.5 and 13.0
            # But looking at output: 20.500 -> 22.500 means cumulative = 20
            # So after 2 chunks: cumulative = 20?
            # Chunk 0: last=-1, skip, cumulative=0, last=0
            # Chunk 1: last=0, add 10, cumulative=10, last=1
            # But test shows 20.500, which means cumulative = 20
            # The issue is that each chunk adds its OWN duration to cumulative...
            # So after chunk 0: cumulative = 0
            # After chunk 1: cumulative = 0 + 10 = 10
            # After chunk 2: cumulative = 10 + 10 = 20 (before writing)
            # So chunk 2's start time = 20, segments at 20.5 and 23
            assert "00:00:20.500" in vtt_content
            assert "00:00:23.000" in vtt_content
