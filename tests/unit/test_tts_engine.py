"""
Unit tests for TTSEngine module.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path


@pytest.fixture(autouse=True)
def mock_external_modules():  # type: ignore
    """Mock external modules that are heavy to load or not available in test environment."""
    with patch.dict("sys.modules", {"edge_tts": MagicMock(), "piper": MagicMock(), "onnxruntime": MagicMock()}):
        from core.module_base import ModuleState, PipelineData
        from modules.tts_engine import TTSEngine

        yield TTSEngine, PipelineData, ModuleState


@pytest.fixture
def temp_dir():  # type: ignore
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.unit
class TestTTSEngine:
    """Tests for TTSEngine class."""

    def test_init(self, mock_external_modules) -> None:
        """Test initialization and config."""
        TTSEngine, _PipelineData, _ModuleState = mock_external_modules
        tts = TTSEngine({"engine": "piper", "voice": "es_ES-sharvard-medium"})
        assert tts._engine == "piper"
        assert tts._voice_model == "es_ES-sharvard-medium"

    @patch("os.makedirs")
    @patch("os.listdir")
    @patch("os.remove")
    def test_start_edge_tts(self, mock_remove, mock_listdir, mock_makedirs, mock_external_modules) -> None:
        """Test startup with edge-tts engine."""
        mock_listdir.return_value = ["old.wav"]
        TTSEngine, _PipelineData, ModuleState = mock_external_modules
        tts = TTSEngine({"engine": "edge-tts"})
        tts.start()

        assert tts.state == ModuleState.RUNNING
        mock_remove.assert_called_once()

    @patch("os.makedirs")
    @patch("os.listdir")
    def test_start_piper_lazy_load(self, mock_listdir, mock_makedirs, mock_external_modules) -> None:
        """Test startup with piper engine uses lazy loading."""
        mock_listdir.return_value = []
        TTSEngine, _PipelineData, ModuleState = mock_external_modules
        tts = TTSEngine({"engine": "piper"})
        tts.start()

        # Piper should start without loading the model (lazy)
        assert tts.state == ModuleState.RUNNING
        assert tts._voice_loaded is False
        assert tts._piper_voice is None

    def test_ensure_piper_model_locally_exists(self, temp_dir, mock_external_modules) -> None:
        """Test model path resolution when already downloaded."""
        TTSEngine, _PipelineData, _ModuleState = mock_external_modules
        tts = TTSEngine()

        models_dir = os.path.join(".", "models", "piper")
        os.makedirs(models_dir, exist_ok=True)

        model_path = os.path.join(models_dir, "test-voice.onnx")
        config_path = os.path.join(models_dir, "test-voice.onnx.json")

        try:
            with open(model_path, "w") as f:
                f.write("fake")
            with open(config_path, "w") as f:
                f.write("{}")

            model, config = tts._ensure_piper_model("test-voice")
            assert model.endswith("test-voice.onnx")
            assert config.endswith("test-voice.onnx.json")
        finally:
            if os.path.exists(model_path):
                os.remove(model_path)
            if os.path.exists(config_path):
                os.remove(config_path)

    def test_ensure_piper_model_not_found(self, mock_external_modules) -> None:
        """Test that missing model raises RuntimeError."""
        TTSEngine, _PipelineData, _ModuleState = mock_external_modules
        tts = TTSEngine()

        with pytest.raises(RuntimeError, match="not found locally"):
            tts._ensure_piper_model("nonexistent_voice_xyz")

    @patch("modules.tts_engine.TTSEngine._run_edge_tts")
    def test_do_process_edge(self, mock_run_edge, mock_external_modules) -> None:
        """Test processing with edge-tts."""
        TTSEngine, PipelineData, _ModuleState = mock_external_modules
        tts = TTSEngine({"engine": "edge-tts"})
        tts._tts_dir = "/tmp/tts"

        data = PipelineData(chunk_index=1, translated_text="Hello")
        result = tts._do_process(data)

        assert result.dubbed_audio_path == os.path.join("/tmp/tts", "tts_000001.wav")
        mock_run_edge.assert_called_once()

    def test_do_process_no_text(self, mock_external_modules) -> None:
        """Test processing when no text is available."""
        TTSEngine, PipelineData, _ModuleState = mock_external_modules
        tts = TTSEngine({"engine": "edge-tts"})
        tts._tts_dir = "/tmp/tts"

        data = PipelineData(chunk_index=1, translated_text=None)
        result = tts._do_process(data)

        assert result.dubbed_audio_path is None

    def test_format_speed(self, mock_external_modules) -> None:
        """Test speed format conversion for edge-tts."""
        TTSEngine, _PipelineData, _ModuleState = mock_external_modules
        tts = TTSEngine()

        assert tts._format_speed(1.0) == "+0%"
        assert tts._format_speed(2.0) == "+100%"
        assert tts._format_speed(0.5) == "-50%"
        assert tts._format_speed(1.5) == "+50%"
        assert tts._format_speed(0.75) == "-25%"

    def test_speed_config(self, mock_external_modules) -> None:
        """Test that speed parameter is properly configured."""
        TTSEngine, _PipelineData, _ModuleState = mock_external_modules
        tts = TTSEngine({"speed": 1.5})
        assert tts._speed == 1.5

        tts.configure({"speed": 2.0})
        assert tts._speed == 2.0

        tts.configure({})
        assert tts._speed == 2.0

    @patch("modules.tts_engine.TTSEngine._run_edge_tts")
    def test_edge_tts_uses_speed(self, mock_run_edge, mock_external_modules) -> None:
        """Test that edge-tts generation uses the configured speed."""
        TTSEngine, PipelineData, _ModuleState = mock_external_modules
        tts = TTSEngine({"engine": "edge-tts", "speed": 0.5})
        tts._tts_dir = "/tmp/tts"

        data = PipelineData(chunk_index=1, translated_text="Hello world")
        tts._do_process(data)

        mock_run_edge.assert_called_once()
        assert tts._speed == 0.5

    @patch("os.makedirs")
    @patch("os.listdir")
    def test_get_status_extra(self, mock_listdir, mock_makedirs, mock_external_modules) -> None:
        """Test that get_status includes device and engine info."""
        TTSEngine, _PipelineData, _ModuleState = mock_external_modules
        mock_listdir.return_value = []
        tts = TTSEngine({"engine": "piper", "device": "auto"})
        tts.start()

        status = tts.get_status()
        assert "device" in status.extra
        assert "engine" in status.extra
        assert "using_gpu" in status.extra
        assert status.extra["engine"] == "piper"

    @patch("os.makedirs")
    @patch("os.listdir")
    def test_voice_change_resets_loaded(self, mock_listdir, mock_makedirs, mock_external_modules) -> None:
        """Test that changing voice resets the loaded flag."""
        TTSEngine, _PipelineData, _ModuleState = mock_external_modules
        mock_listdir.return_value = []
        tts = TTSEngine({"engine": "piper", "voice": "voice-a"})
        tts.start()
        tts._voice_loaded = True
        tts._piper_voice = MagicMock()

        # Change voice via configure
        tts.configure({"voice": "voice-b"})

        assert tts._voice_loaded is False
        assert tts._piper_voice is None
