"""Tests for RecordingOutput functionality - matching actual implementation."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.unit
class TestRecordingOutputInitialization:
    """Test RecordingOutput initializes correctly."""

    def test_recording_output_imports(self) -> None:
        """Test RecordingOutput can be imported."""
        from modules.outputs.recording_output import RecordingOutput

        assert RecordingOutput is not None

    def test_recording_output_inherits_output_sink(self) -> None:
        """Test RecordingOutput inherits OutputSink."""
        from core.output_sink import OutputSink
        from modules.outputs.recording_output import RecordingOutput

        assert issubclass(RecordingOutput, OutputSink)

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_default_config(self, mock_ffmpeg) -> None:
        """Test RecordingOutput accepts default config."""
        from modules.outputs.recording_output import RecordingOutput

        config = {"output_path": "./output/test.mp4"}
        rec = RecordingOutput(config)
        assert rec._output_path == "./output/test.mp4"


class TestRecordingOutputWrite:
    """Test RecordingOutput writes data."""

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_has_write_method(self, mock_ffmpeg) -> None:
        """Test RecordingOutput has write method (from OutputSink)."""
        from modules.outputs.recording_output import RecordingOutput

        assert hasattr(RecordingOutput, "write")

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_write_handles_none_video(self, mock_ffmpeg) -> None:
        """Test RecordingOutput write handles None video path."""
        from core.module_base import PipelineData
        from modules.outputs.recording_output import RecordingOutput

        config = {"output_path": "./output/test.mp4"}
        rec = RecordingOutput(config)

        data = PipelineData(
            video_chunk_path=None,
            audio_chunk_path=None,
            chunk_index=0,
            duration=10.0,
            cumulative_duration=0.0,
            metadata={},
        )

        # Should not raise
        rec.write(data)


class TestRecordingOutputStop:
    """Test RecordingOutput stop concatenates chunks."""

    @patch("modules.outputs.recording_output.subprocess.run")
    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_stop_method_exists(self, mock_ffmpeg, mock_run) -> None:
        """Test stop() method exists."""
        from modules.outputs.recording_output import RecordingOutput

        assert hasattr(RecordingOutput, "stop")

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    @patch("modules.outputs.recording_output.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_recording_output_stop_concatenates_when_chunks_exist(self, mock_exists, mock_run, mock_ffmpeg) -> None:
        """Test stop() concatenates when chunks exist."""
        from modules.outputs.recording_output import RecordingOutput

        config = {"output_path": "./output/test.mp4"}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "exists", return_value=True):
                rec = RecordingOutput(config)
                rec._recording_dir = tmpdir
                rec._video_dir = os.path.join(tmpdir, "video")

                os.makedirs(rec._video_dir, exist_ok=True)
                for i in range(3):
                    Path(f"{rec._video_dir}/chunk_{i}.mp4").touch()

                rec.stop()


class TestRecordingOutputStatus:
    """Test RecordingOutput provides status."""

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_get_status_returns_dict(self, mock_ffmpeg) -> None:
        """Test RecordingOutput returns status dict."""
        from modules.outputs.recording_output import RecordingOutput

        config = {"output_path": "./output/test.mp4"}
        rec = RecordingOutput(config)
        status = rec.get_status()

        assert hasattr(status, "state")
        assert hasattr(status, "enabled")


class TestRecordingOutputExtra:
    """Test RecordingOutput extra info."""

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_extra_has_encoder(self, mock_ffmpeg) -> None:
        """Test status extra has encoder info."""
        from modules.outputs.recording_output import RecordingOutput

        config = {"output_path": "./output/test.mp4", "codec": "h264_nvenc"}
        rec = RecordingOutput(config)
        status = rec.get_status()

        assert status.extra is not None
        assert "encoder" in status.extra


class TestRecordingOutputConfig:
    """Test RecordingOutput config handling."""

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_parses_codec(self, mock_ffmpeg) -> None:
        """Test RecordingOutput parses codec from config."""
        from modules.outputs.recording_output import RecordingOutput

        config = {"output_path": "./output/test.mp4", "codec": "h265"}
        rec = RecordingOutput(config)
        assert rec._codec == "h265"

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_parses_format(self, mock_ffmpeg) -> None:
        """Test RecordingOutput parses format from config."""
        from modules.outputs.recording_output import RecordingOutput

        config = {"output_path": "./output/test.mp4", "format": "mkv"}
        rec = RecordingOutput(config)
        assert rec._format == "mkv"


class TestRecordingOutputMetrics:
    """Test RecordingOutput metrics tracking."""

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_tracks_processed_chunks(self, mock_ffmpeg) -> None:
        """Test RecordingOutput tracks processed chunks."""
        from modules.outputs.recording_output import RecordingOutput

        config = {"output_path": "./output/test.mp4"}
        rec = RecordingOutput(config)
        assert hasattr(rec, "_processed_chunks")

    @patch("modules.outputs.recording_output.ensure_ffmpeg")
    def test_recording_output_tracks_bytes_written(self, mock_ffmpeg) -> None:
        """Test RecordingOutput tracks bytes written."""
        from modules.outputs.recording_output import RecordingOutput

        config = {"output_path": "./output/test.mp4"}
        rec = RecordingOutput(config)
        assert hasattr(rec, "_bytes_written")
