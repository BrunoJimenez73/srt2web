"""
Unit tests for FFmpeg utilities.
"""

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestFFmpegUtils:
    """Test FFmpeg utility functions."""

    def test_find_ffmpeg_returns_valid_result(self) -> None:
        """Test find_ffmpeg returns string or None."""
        from core.ffmpeg_utils import find_ffmpeg

        result = find_ffmpeg()
        assert result is None or (isinstance(result, str) and result)

    def test_find_ffprobe_returns_valid_result(self) -> None:
        """Test find_ffprobe returns string or None."""
        from core.ffmpeg_utils import find_ffprobe

        result = find_ffprobe()
        assert result is None or (isinstance(result, str) and result)

    def test_check_gpu_support_returns_dict(self) -> None:
        """Test check_gpu_support returns dict."""
        from core.ffmpeg_utils import check_gpu_support

        with patch("core.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = b"h264_nvenc"
            result = check_gpu_support("/bin/ffmpeg")
            assert isinstance(result, dict)
            assert "nvenc" in result

    def test_get_video_duration_returns_number(self) -> None:
        """Test get_video_duration returns number."""
        from core.ffmpeg_utils import get_video_duration

        with patch("core.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = b"10.5"
            result = get_video_duration("test.mp4")
            assert isinstance(result, (int, float))

    def test_check_srt_support_returns_bool(self) -> None:
        """Test check_srt_support returns bool."""
        from core.ffmpeg_utils import check_srt_support

        with patch("core.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = b"srt"
            result = check_srt_support("/bin/ffmpeg")
            assert isinstance(result, bool)

    def test_run_ffmpeg_decodes_bytes(self) -> None:
        """Test run_ffmpeg function handles bytes output."""
        from core.ffmpeg_utils import run_ffmpeg

        with (
            patch("core.ffmpeg_utils.ensure_ffmpeg", return_value="ffmpeg"),
            patch("core.ffmpeg_utils.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = b"test"
            mock_run.return_value.stderr = b""
            result = run_ffmpeg(["-version"])
            assert result.returncode == 0

    def test_start_ffmpeg_process(self) -> None:
        """Test start_ffmpeg_process function."""
        from core.ffmpeg_utils import start_ffmpeg_process

        with (
            patch("core.ffmpeg_utils.ensure_ffmpeg", return_value="ffmpeg"),
            patch("core.ffmpeg_utils.subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value.pid = 1234
            process = start_ffmpeg_process(["-version"])
            assert process is not None
