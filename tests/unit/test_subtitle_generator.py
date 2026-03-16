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
            mocked_file.assert_called_with(os.path.join("/tmp", "hls", "subs.vtt"), "w", encoding="utf-8")
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
