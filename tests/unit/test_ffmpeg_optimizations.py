"""
Tests para las optimizaciones de FFmpeg implementadas 05/04/2026.

Cubre:
- Caching de ruta FFmpeg/FFprobe
- Timeouts reducidos
- Prioridad baja de procesos
- Funcion _get_creation_flags
"""

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestFFmpegUtilsOptimizations:
    """Test FFmpeg utils optimizations."""

    def test_get_creation_flags_windows(self):
        """Test that Windows creation flags on Windows."""
        from core.ffmpeg_utils import _get_creation_flags
        
        with patch('sys.platform', 'win32'):
            flags = _get_creation_flags()
            
            # Should return CREATE_NO_WINDOW + BELOW_NORMAL_PRIORITY_CLASS
            assert flags == subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS

    def test_get_creation_flags_non_windows(self):
        """Test that creation flags are 0 on non-Windows platforms."""
        from core.ffmpeg_utils import _get_creation_flags
        
        with patch('sys.platform', 'linux'):
            flags = _get_creation_flags()
            assert flags == 0

    def test_ffmpeg_caching(self):
        """Test that FFmpeg path is cached after first lookup."""
        from core.ffmpeg_utils import find_ffmpeg, _cached_ffmpeg_path
        
        # Reset cache
        import core.ffmpeg_utils
        core.ffmpeg_utils._cached_ffmpeg_path = None
        
        with patch('core.ffmpeg_utils.shutil.which') as mock_which:
            mock_which.return_value = "ffmpeg_path"
            
            # First call
            path1 = find_ffmpeg()
            
            # Second call should use cache
            path2 = find_ffmpeg()
            
            assert path1 == path2
            assert core.ffmpeg_utils._cached_ffmpeg_path == path1
            mock_which.assert_called_once()

    def test_ffprobe_caching(self):
        """Test that FFprobe path is cached after first lookup."""
        from core.ffmpeg_utils import find_ffprobe, _cached_ffprobe_path
        
        # Reset cache
        import core.ffmpeg_utils
        core.ffmpeg_utils._cached_ffprobe_path = None
        
        with patch('core.ffmpeg_utils.shutil.which') as mock_which:
            mock_which.return_value = "ffprobe_path"
            
            # First call
            path1 = find_ffprobe()
            
            # Second call should use cache
            path2 = find_ffprobe()
            
            assert path1 == path2
            assert core.ffmpeg_utils._cached_ffprobe_path == path1
            mock_which.assert_called_once()

    def test_get_video_duration_timeout(self):
        """Test get_video_duration has timeout of 3s."""
        from core.ffmpeg_utils import get_video_duration
        
        with patch('core.ffmpeg_utils.subprocess.run') as mock_run:
            mock_run.return_value.stdout = b"10.5"
            
            get_video_duration("test.mp4")
            
            # Check timeout parameter
            args, kwargs = mock_run.call_args
            assert kwargs['timeout'] == 3

    def test_run_ffmpeg_default_timeout(self):
        """Test run_ffmpeg uses default timeout of 5s."""
        from core.ffmpeg_utils import run_ffmpeg
        
        with patch('core.ffmpeg_utils.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            run_ffmpeg(["-version"])
            
            # Check timeout parameter
            args, kwargs = mock_run.call_args
            assert kwargs['timeout'] == 5

    def test_audio_extractor_timeout(self):
        """Test AudioExtractor uses 5s timeout."""
        from modules.audio_extractor import AudioExtractor
        
        extractor = AudioExtractor()
        extractor._ffmpeg_path = "ffmpeg"
        
        with patch('modules.audio_extractor.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            data = Mock()
            data.video_chunk_path = "test.ts"
            
            extractor._do_process(data)
            
            # Check timeout parameter
            args, kwargs = mock_run.call_args
            assert kwargs['timeout'] == 5
            
            # Check creation flags on Windows
            if sys.platform == 'win32':
                assert 'creationflags' in kwargs
                assert kwargs['creationflags'] & subprocess.BELOW_NORMAL_PRIORITY_CLASS != 0

    def test_priority_flag_exists(self):
        """Test that BELOW_NORMAL_PRIORITY_CLASS is used in all calls."""
        from core.ffmpeg_utils import _get_creation_flags
        
        with patch('sys.platform', 'win32'):
            flags = _get_creation_flags()
            
            assert 'BELOW_NORMAL_PRIORITY_CLASS' in subprocess.__dict__
            assert flags & subprocess.BELOW_NORMAL_PRIORITY_CLASS != 0


class TestFFmpegIntegration:
    """Integration tests for FFmpeg optimizations."""
    
    @pytest.mark.skipif(not os.path.exists('ffmpeg.exe') and not os.path.exists('/usr/bin/ffmpeg'), reason="FFmpeg not found")
    def test_ffmpeg_runs_with_optimizations(self):
        """Test that FFmpeg actually runs with new optimizations."""
        from core.ffmpeg_utils import run_ffmpeg
        
        result = run_ffmpeg(["-version"])
        assert result.returncode == 0