"""
Unit tests for SRTIngest module.
"""

import os
import sys
import glob
import subprocess
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.srt_ingest import SRTIngest
from core.module_base import PipelineData, ModuleState

class TestSRTIngest:
    """Tests for SRTIngest class."""

    @patch("modules.srt_ingest.ensure_ffmpeg")
    @patch("os.makedirs")
    @patch("subprocess.Popen")
    @patch("glob.glob")
    def test_start(self, mock_glob, mock_popen, mock_makedirs, mock_ensure) -> None:
        """Test starting the SRT ingest process."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_glob.return_value = [] # No old chunks
        mock_popen.return_value = MagicMock()
        
        ingest = SRTIngest(output_dir="/tmp")
        ingest.start()
        
        assert ingest.state == ModuleState.RUNNING
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "/bin/ffmpeg"
        assert "-segment_time" in cmd
        assert "srt://" in str(cmd)

    @patch("sys.platform", "win32")
    @patch("subprocess.run")
    def test_stop_windows(self, mock_run) -> None:
        """Test stopping the process on Windows using taskkill."""
        ingest = SRTIngest()
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        ingest._ffmpeg_proc = mock_proc
        
        ingest.stop()
        
        mock_run.assert_called_with(
            ["taskkill", "/F", "/T", "/PID", "1234"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        assert ingest.state == ModuleState.IDLE

    @patch("glob.glob")
    @patch("core.ffmpeg_utils.get_video_duration")
    @patch("os.path.basename")
    def test_get_next_chunk_success(self, mock_basename, mock_duration, mock_glob) -> None:
        """Test successfully retrieving the next available chunk."""
        ingest = SRTIngest(output_dir="/tmp")
        ingest._chunks_dir = "/tmp/chunks"
        ingest._last_chunk_index = -1
        
        # Two chunks found, 000000 is ready, 000001 is in-progress
        mock_glob.return_value = [
            "/tmp/chunks/chunk_000000.ts",
            "/tmp/chunks/chunk_000001.ts"
        ]
        mock_basename.side_effect = lambda p: os.path.split(p)[1]
        mock_duration.return_value = 4.2
        
        chunk = ingest.get_next_chunk()
        
        assert chunk is not None
        assert chunk.chunk_index == 0
        assert chunk.duration == 4.2
        assert chunk.video_chunk_path == "/tmp/chunks/chunk_000000.ts"
        assert ingest._last_chunk_index == 0

    @patch("glob.glob")
    def test_get_next_chunk_none_available(self, mock_glob) -> None:
        """Test when no new chunks are available."""
        ingest = SRTIngest(output_dir="/tmp")
        ingest._chunks_dir = "/tmp/chunks"
        ingest._last_chunk_index = 0
        
        # Only one chunk found, it's considered in-progress
        mock_glob.return_value = ["/tmp/chunks/chunk_000001.ts"]
        
        chunk = ingest.get_next_chunk()
        assert chunk is None

    def test_get_srt_url(self) -> None:
        """Test generating the SRT URL."""
        ingest = SRTIngest()
        ingest._srt_port = 5000
        url = ingest.get_srt_url()
        assert "srt://127.0.0.1:5000" in url
        assert "mode=caller" in url
