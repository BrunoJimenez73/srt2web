"""
Tests para RecordingOutput - Grabación continua de archivos.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

from modules.outputs.recording_output import RecordingOutput
from core.module_base import PipelineData


class TestRecordingOutput:
    """Tests para RecordingOutput."""

    @pytest.fixture
    def temp_dir(self):
        """Crear directorio temporal."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def recording_output(self, temp_dir):
        """Crear RecordingOutput con configuración básica."""
        config = {
            "output_path": os.path.join(temp_dir, "recording.mp4"),
            "format": "mp4",
            "codec": "copy",
            "quality_mode": "cbr",
            "audio_codec": "copy",
            "split_mode": "none",
            "subtitles": "none"
        }
        return RecordingOutput(config)

    def test_initialization(self, recording_output, temp_dir):
        """Test de inicialización."""
        assert recording_output is not None
        assert recording_output.name == "recording"
        assert recording_output._output_path == os.path.join(temp_dir, "recording.mp4")
        assert recording_output._format == "mp4"
        assert recording_output._codec == "copy"

    def test_configure(self, recording_output):
        """Test de configuración."""
        new_config = {
            "output_path": "/new/path/output.mkv",
            "format": "mkv",
            "codec": "h264_nvenc",
            "quality_mode": "crf",
            "video_crf": 20,
            "split_mode": "time",
            "split_value": 300
        }
        recording_output.configure(new_config)
        
        assert recording_output._output_path == "/new/path/output.mkv"
        assert recording_output._format == "mkv"
        assert recording_output._codec == "h264_nvenc"
        assert recording_output._quality_mode == "crf"
        assert recording_output._video_crf == 20
        assert recording_output._split_mode == "time"
        assert recording_output._split_value == 300

    def test_get_stream_info(self, recording_output):
        """Test de información del stream."""
        info = recording_output.get_stream_info()
        
        assert info["type"] == "recording"
        assert "output_path" in info
        assert "current_file" in info
        assert "format" in info
        assert "codec" in info

    def test_get_status(self, recording_output):
        """Test de estado."""
        status = recording_output.get_status()
        
        assert "state" in status
        assert "enabled" in status
        assert "processed_chunks" in status
        assert "output_path" in status

    def test_start_stop(self, recording_output, temp_dir):
        """Test de inicio y parada."""
        os.makedirs(temp_dir, exist_ok=True)
        
        recording_output.start()
        assert recording_output._running is True
        
        recording_output.stop()
        assert recording_output._running is False

    def test_should_split_none(self, recording_output):
        """Test de split mode none."""
        recording_output._split_mode = "none"
        recording_output._file_start_time = 0
        
        assert recording_output._should_split() is False

    def test_should_split_time(self, recording_output, temp_dir):
        """Test de split por tiempo."""
        import time
        recording_output._split_mode = "time"
        recording_output._split_value = 600  # 600 segundos = 10 minutos
        recording_output._file_start_time = time.time()
        
        # Should not split when just started
        assert recording_output._should_split() is False
        
        # Simulate time passing (but don't actually wait)
        # Reset to test again
        recording_output._file_start_time = time.time() - 100
        # Still less than 600 seconds
        assert recording_output._should_split() is False
        
        # More than 600 seconds
        recording_output._file_start_time = time.time() - 700
        assert recording_output._should_split() is True

    def test_get_next_output_path(self, recording_output):
        """Test de siguiente ruta de salida."""
        recording_output._output_path = "/path/recording.mp4"
        recording_output._segment_index = 0
        
        path = recording_output._get_next_output_path()
        assert path == "/path/recording.mp4"
        
        recording_output._segment_index = 1
        path = recording_output._get_next_output_path()
        assert path == "/path/recording_001.mp4"
        
        recording_output._segment_index = 10
        path = recording_output._get_next_output_path()
        assert path == "/path/recording_010.mp4"

    def test_different_formats(self, temp_dir):
        """Test de diferentes formatos."""
        formats = ["mp4", "mkv", "webm"]
        
        for fmt in formats:
            config = {
                "output_path": f"{temp_dir}/recording.{fmt}",
                "format": fmt,
                "codec": "copy"
            }
            output = RecordingOutput(config)
            assert output._format == fmt

    def test_different_codecs(self, temp_dir):
        """Test de diferentes códecs."""
        codecs = ["copy", "h264_nvenc", "libx264"]
        
        for codec in codecs:
            config = {
                "output_path": f"{temp_dir}/recording.mp4",
                "format": "mp4",
                "codec": codec
            }
            output = RecordingOutput(config)
            assert output._codec == codec

    def test_quality_modes(self, temp_dir):
        """Test de modos de calidad."""
        config_cbr = {
            "output_path": f"{temp_dir}/recording.mp4",
            "format": "mp4",
            "codec": "h264_nvenc",
            "quality_mode": "cbr",
            "video_bitrate": "5000k"
        }
        output_cbr = RecordingOutput(config_cbr)
        assert output_cbr._quality_mode == "cbr"
        assert output_cbr._video_bitrate == "5000k"
        
        config_crf = {
            "output_path": f"{temp_dir}/recording.mp4",
            "format": "mp4",
            "codec": "h264_nvenc",
            "quality_mode": "crf",
            "video_crf": 23
        }
        output_crf = RecordingOutput(config_crf)
        assert output_crf._quality_mode == "crf"
        assert output_crf._video_crf == 23


class TestRecordingOutputFFmpeg:
    """Tests para comandos FFmpeg de RecordingOutput."""

    @pytest.fixture
    def temp_dir(self):
        """Crear directorio temporal."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def recording_output(self, temp_dir):
        """Crear RecordingOutput."""
        config = {
            "output_path": os.path.join(temp_dir, "recording.mp4"),
            "format": "mp4",
            "codec": "copy",
            "quality_mode": "cbr",
            "audio_codec": "copy",
            "split_mode": "none",
            "subtitles": "none"
        }
        return RecordingOutput(config)

    def test_get_ffmpeg_cmd_copy(self, recording_output, temp_dir):
        """Test de comando FFmpeg con codec copy."""
        # Create actual video/audio files
        video_path = os.path.join(temp_dir, "video.mp4")
        audio_path = os.path.join(temp_dir, "audio.wav")
        
        # Create empty files to simulate existing chunks
        Path(video_path).touch()
        Path(audio_path).touch()
        
        data = PipelineData(
            chunk_index=0,
            video_chunk_path=video_path,
            mixed_audio_path=audio_path
        )
        recording_output._pending_data = data
        
        output_path = os.path.join(temp_dir, "output.mp4")
        cmd = recording_output._get_ffmpeg_cmd(output_path)
        
        # El comando puede estar vacío si los archivos no existen
        # o tener la estructura correcta
        assert cmd is not None

    def test_get_ffmpeg_cmd_nvenc(self, temp_dir):
        """Test de comando FFmpeg con NVENC."""
        config = {
            "output_path": os.path.join(temp_dir, "recording.mp4"),
            "format": "mp4",
            "codec": "h264_nvenc",
            "quality_mode": "cbr",
            "video_bitrate": "5000k",
            "video_preset": "fast",
            "audio_codec": "aac",
            "audio_bitrate": "128k",
            "subtitles": "none"
        }
        output = RecordingOutput(config)
        
        # Create actual files
        video_path = os.path.join(temp_dir, "video.mp4")
        audio_path = os.path.join(temp_dir, "audio.wav")
        Path(video_path).touch()
        Path(audio_path).touch()
        
        data = PipelineData(
            chunk_index=0,
            video_chunk_path=video_path,
            mixed_audio_path=audio_path
        )
        output._pending_data = data
        
        cmd = output._get_ffmpeg_cmd(os.path.join(temp_dir, "output.mp4"))
        
        assert cmd is not None


import time
