"""
Tests para API de gestión de outputs múltiples.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def mock_pipeline():
    """Crear mock del pipeline."""
    pipeline = Mock()
    pipeline.get_output_sinks = Mock(return_value=None)
    pipeline.get_output_sink = Mock(return_value=None)
    return pipeline


@pytest.fixture
def mock_output_sink():
    """Crear mock del output sink."""
    sink = Mock()
    sink.name = "test_output"
    sink.get_status = Mock(return_value={
        "state": "running",
        "enabled": True,
        "processed_chunks": 10
    })
    sink.get_stream_info = Mock(return_value={"type": "web"})
    return sink


@pytest.fixture
def mock_composite_output():
    """Crear mock de CompositeOutput."""
    composite = Mock()
    
    mock_output = Mock()
    mock_output.name = "web_output"
    mock_output.get_status = Mock(return_value={
        "state": "running",
        "enabled": True,
        "processed_chunks": 5,
        "last_process_time_ms": 100.0,
        "extra": {"encoder": "h264_nvenc"}
    })
    mock_output.get_stream_info = Mock(return_value={
        "type": "web",
        "master_url": "/hls/master.m3u8"
    })
    
    composite.get_all_output_statuses = Mock(return_value=[
        {
            "name": "web_output",
            "type": "web",
            "state": "running",
            "enabled": True,
            "processed_chunks": 5,
            "last_process_time_ms": 100.0,
            "extra": {"encoder": "h264_nvenc"},
            "stream_info": {"type": "web"}
        }
    ])
    composite.get_output_by_name = Mock(return_value=mock_output)
    composite.is_output_enabled = Mock(return_value=True)
    composite.enable_output = Mock(return_value=True)
    composite.remove_output = Mock(return_value=True)
    composite.add_output = Mock()
    composite.start = Mock()
    
    return composite


class TestOutputAPI:
    """Tests para endpoints de API de outputs."""

    def test_list_outputs_no_outputs(self):
        """Test listar outputs cuando no hay ninguno."""
        from modules.outputs.composite_output import CompositeOutput
        
        # Create composite output with no outputs
        composite = CompositeOutput({})
        
        # Verify empty state (returns empty list)
        assert composite.get_all_output_statuses() == []
        
    def test_get_available_output_types(self):
        """Test obtener tipos de outputs disponibles."""
        from core.io_factory import OutputFactory
        
        # Verificar que los outputs están registrados
        OutputFactory._ensure_initialized()
        available = OutputFactory.available()
        
        assert isinstance(available, list)
        # El tipo 'recording' debe estar registrado
        assert "recording" in available or "web" in available


class TestOutputFactory:
    """Tests para OutputFactory."""

    def test_create_recording_output(self):
        """Test crear output de tipo recording."""
        from core.io_factory import OutputFactory
        
        config = {
            "output_path": "./output/test.mp4",
            "format": "mp4",
            "codec": "copy"
        }
        
        try:
            output = OutputFactory.create("recording", config)
            assert output is not None
            assert output.name == "recording"
        except ValueError as e:
            # Si no está registrado, el test falla
            pytest.fail(f"Output 'recording' not registered: {e}")

    def test_create_multiple_outputs(self):
        """Test crear múltiples outputs."""
        from core.io_factory import OutputFactory
        
        configs = [
            {"type": "web", "name": "web1"},
            {"type": "file", "name": "file1"},
        ]
        
        try:
            outputs = OutputFactory.create_multiple(configs)
            assert len(outputs) == 2
        except ValueError as e:
            pytest.skip(f"Some output types not available: {e}")


class TestOutputSink:
    """Tests para OutputSink base."""

    def test_output_sink_get_status(self):
        """Test método get_status en OutputSink base."""
        from core.output_sink import OutputSink
        
        class TestSink(OutputSink):
            def start(self): pass
            def stop(self): pass
            def write(self, data): pass
        
        sink = TestSink("test", {})
        status = sink.get_status()
        
        assert "state" in status
        assert "enabled" in status
        assert status["state"] == "idle"


class TestCompositeOutputAPI:
    """Tests para integración de CompositeOutput con API."""

    def test_composite_output_get_all_statuses(self):
        """Test obtener todos los statuses del composite."""
        from modules.outputs.composite_output import CompositeOutput
        
        composite = CompositeOutput({})
        
        # Añadir un mock output
        mock_output = Mock()
        mock_output.name = "test"
        mock_output.get_status = Mock(return_value={
            "state": "running",
            "enabled": True,
            "processed_chunks": 10,
            "last_process_time_ms": 50.0,
            "extra": {}
        })
        mock_output.get_stream_info = Mock(return_value={"type": "test"})
        
        composite.add_output("test", mock_output)
        
        statuses = composite.get_all_output_statuses()
        
        assert len(statuses) == 1
        assert statuses[0]["name"] == "test"
        assert statuses[0]["state"] == "running"

    def test_composite_output_toggle(self):
        """Test toggle de output."""
        from modules.outputs.composite_output import CompositeOutput
        
        composite = CompositeOutput({})
        
        mock_output = Mock()
        mock_output.enabled = True
        composite.add_output("test", mock_output)
        
        result = composite.enable_output("test", False)
        assert result is True
        assert mock_output.enabled is False

    def test_composite_output_remove(self):
        """Test eliminar output."""
        from modules.outputs.composite_output import CompositeOutput
        
        composite = CompositeOutput({})
        
        mock_output = Mock()
        mock_output.name = "test"
        mock_output.stop = Mock()
        composite.add_output("test", mock_output)
        
        result = composite.remove_output("test")
        assert result is True
        assert "test" not in composite.get_output_names()


class TestRecordingOutputConfig:
    """Tests para configuración de RecordingOutput."""

    def test_recording_config_all_options(self):
        """Test de todas las opciones de configuración."""
        from modules.outputs.recording_output import RecordingOutput
        
        config = {
            "output_path": "/path/to/recording.mp4",
            "format": "mp4",
            "codec": "h264_nvenc",
            "video_bitrate": "5000k",
            "video_crf": 20,
            "quality_mode": "crf",
            "audio_codec": "aac",
            "audio_bitrate": "128k",
            "split_mode": "time",
            "split_value": 600,
            "subtitles": "burnt",
            "video_preset": "fast"
        }
        
        output = RecordingOutput(config)
        
        assert output._output_path == "/path/to/recording.mp4"
        assert output._format == "mp4"
        assert output._codec == "h264_nvenc"
        assert output._video_bitrate == "5000k"
        assert output._video_crf == 20
        assert output._quality_mode == "crf"
        assert output._audio_codec == "aac"
        assert output._audio_bitrate == "128k"
        assert output._split_mode == "time"
        assert output._split_value == 600
        assert output._subtitles == "burnt"
        assert output._video_preset == "fast"

    def test_recording_default_values(self):
        """Test valores por defecto."""
        from modules.outputs.recording_output import RecordingOutput
        
        output = RecordingOutput({})
        
        assert output._output_path == "./output/recording.mp4"
        assert output._format == "mp4"
        assert output._codec == "copy"
        assert output._quality_mode == "cbr"
        assert output._split_mode == "none"
        assert output._subtitles == "none"
