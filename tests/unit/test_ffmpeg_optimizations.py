"""
Tests for FFmpeg optimizations.
"""

import pytest
from unittest.mock import patch


class TestFFmpegUtilsOptimizations:
    """Test FFmpeg utils optimizations."""

    def test_get_creation_flags_windows(self):
        """Test Windows creation flags."""
        from core.ffmpeg_utils import _get_creation_flags
        import subprocess

        with patch("sys.platform", "win32"):
            flags = _get_creation_flags()
            assert flags == subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS

    def test_get_creation_flags_non_windows(self):
        """Test creation flags are 0 on non-Windows."""
        from core.ffmpeg_utils import _get_creation_flags

        with patch("sys.platform", "linux"):
            flags = _get_creation_flags()
            assert flags == 0

    def test_find_ffmpeg_returns_path(self):
        """Test find_ffmpeg returns a valid path or None."""
        from core.ffmpeg_utils import find_ffmpeg

        result = find_ffmpeg()
        assert result is None or isinstance(result, str)

    def test_find_ffprobe_returns_path(self):
        """Test find_ffprobe returns a valid path or None."""
        from core.ffmpeg_utils import find_ffprobe

        result = find_ffprobe()
        assert result is None or isinstance(result, str)

    def test_get_video_duration_returns_number(self):
        """Test get_video_duration returns a number."""
        from core.ffmpeg_utils import get_video_duration

        with patch("core.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value.stdout = b"10.5"
            result = get_video_duration("test.mp4")
            assert isinstance(result, (int, float))