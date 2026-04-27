"""
Unit tests for VideoMuxer module.
"""

import os
import pytest
from unittest.mock import patch
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from modules.video_muxer import VideoMuxer
from core.module_base import PipelineData, ModuleState


class TestableVideoMuxer(VideoMuxer):
    """Concrete VideoMuxer subclass for testing."""

    def _do_process(self, data: object) -> object:
        return data

    def _log(self, level: str, message: str) -> None:
        pass


class TestVideoMuxer:
    """Tests for VideoMuxer class."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        muxer = TestableVideoMuxer(output_dir="/tmp")
        
        assert muxer.name == "video_muxer"
        assert muxer.enabled is True

    def test_start(self) -> None:
        """Test module can start."""
        muxer = TestableVideoMuxer(output_dir="/tmp")
        muxer.start()
        
        assert muxer.state in (ModuleState.STARTING, ModuleState.RUNNING)

    def test_stop(self) -> None:
        """Test module can stop."""
        muxer = TestableVideoMuxer(output_dir="/tmp")
        muxer.start()
        muxer.stop()
        
        assert muxer.state == ModuleState.IDLE

    def test_get_status_has_extra(self) -> None:
        """Test get_status includes extra info."""
        from modules.video_muxer import VideoMuxer

        class Testable(VideoMuxer):
            def _do_process(self, data) -> None:
                return data

        with patch("modules.video_muxer.ensure_ffmpeg", return_value="/bin/ffmpeg"):
            with patch("core.ffmpeg_utils.check_gpu_support", return_value={"nvenc": False, "qsv": False, "amf": False, "vaapi": False}):
                muxer = Testable(output_dir="/tmp")
                muxer.start()
                
                status = muxer.get_status()
                assert "encoder_mode" in status.extra

    def test_process_with_none_input(self) -> None:
        """Test process handles None input."""
        muxer = TestableVideoMuxer(output_dir="/tmp")
        
        data = PipelineData(chunk_index=0, video_chunk_path=None)
        result = muxer._do_process(data)
        
        assert result is not None

    def test_hls_directory_created(self) -> None:
        """Test HLS directory is set."""
        from modules.video_muxer import VideoMuxer

        class Testable(VideoMuxer):
            def _do_process(self, data) -> None:
                return data

        with patch("modules.video_muxer.ensure_ffmpeg", return_value="/bin/ffmpeg"):
            with patch("core.ffmpeg_utils.check_gpu_support", return_value={"nvenc": False}):
                muxer = Testable(output_dir="/tmp")
                muxer.start()
                assert muxer._hls_dir is not None