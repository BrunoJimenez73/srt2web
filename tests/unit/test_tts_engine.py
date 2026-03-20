"""
Unit tests for TTSEngine module.
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Mock edge_tts and piper before importing TTSEngine
sys.modules["edge_tts"] = MagicMock()
sys.modules["piper"] = MagicMock()
sys.modules["onnxruntime"] = MagicMock()

from modules.tts_engine import TTSEngine
from core.module_base import PipelineData, ModuleState


class TestTTSEngine:
    """Tests for TTSEngine class."""

    def test_init(self):
        """Test initialization and config."""
        tts = TTSEngine({"engine": "piper", "voice": "es_ES-sharvard-medium"})
        assert tts._engine == "piper"
        assert tts._voice_model == "es_ES-sharvard-medium"

    @patch("os.makedirs")
    @patch("os.listdir")
    @patch("os.remove")
    def test_start_edge_tts(self, mock_remove, mock_listdir, mock_makedirs):
        """Test startup with edge-tts engine."""
        mock_listdir.return_value = ["old.wav"]
        tts = TTSEngine({"engine": "edge-tts"})
        tts.start()

        assert tts.state == ModuleState.RUNNING
        mock_remove.assert_called_once()

    @patch("modules.tts_engine.TTSEngine._ensure_piper_model")
    @patch("os.makedirs")
    @patch("os.listdir")
    def test_start_piper(self, mock_listdir, mock_makedirs, mock_ensure):
        """Test startup with piper engine."""
        mock_listdir.return_value = []
        mock_ensure.return_value = ("/model.onnx", "/config.json")

        # Setup PiperVoice mock
        mock_piper = sys.modules["piper"]
        mock_piper.PiperVoice.load.return_value = MagicMock()

        tts = TTSEngine({"engine": "piper"})
        tts.start()

        assert tts.state == ModuleState.RUNNING
        mock_ensure.assert_called_once()

    def test_ensure_piper_model_locally_exists(self):
        """Test model path resolution when already downloaded."""
        tts = TTSEngine()
        with patch("os.path.exists", return_value=True):
            model, config = tts._ensure_piper_model("es_ES-sharvard-medium")
            assert model.endswith("es_ES-sharvard-medium.onnx")
            assert config.endswith("es_ES-sharvard-medium.onnx.json")

    @patch("urllib.request.urlretrieve")
    @patch("os.path.exists", return_value=False)
    @patch("os.makedirs")
    def test_ensure_piper_model_download(
        self, mock_makedirs, mock_exists, mock_retrieve
    ):
        """Test model download logic."""
        tts = TTSEngine()
        # Mocking os.path.join and abspath to avoid issues with different OS paths
        with patch("os.path.abspath", return_value="/tmp/models/piper"):
            model, config = tts._ensure_piper_model("es_ES-sharvard-medium")

            assert mock_retrieve.call_count == 2
            # Should have called with correct Hugging Face URL
            args, _ = mock_retrieve.call_args_list[0]
            assert "huggingface.co" in args[0]
            assert "es_ES/sharvard/medium/es_ES-sharvard-medium.onnx" in args[0]

    @patch("modules.tts_engine.TTSEngine._run_edge_tts")
    def test_do_process_edge(self, mock_run_edge):
        """Test processing with edge-tts."""
        tts = TTSEngine({"engine": "edge-tts"})
        tts._tts_dir = "/tmp/tts"

        data = PipelineData(chunk_index=1, translated_text="Hello")
        result = tts._do_process(data)

        assert result.dubbed_audio_path == os.path.join("/tmp/tts", "tts_000001.wav")
        mock_run_edge.assert_called_once()

    @patch("wave.open")
    def test_run_piper_tts(self, mock_wave_open):
        """Test piper synthesis execution."""
        tts = TTSEngine({"engine": "piper"})
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        tts._piper_voice = mock_voice

        tts._run_piper_tts("Hello", "/tmp/out.wav")

        mock_voice.synthesize.assert_called_once_with(
            "Hello", mock_wave_open().__enter__()
        )

    def test_format_speed(self):
        """Test speed format conversion for edge-tts."""
        tts = TTSEngine()

        assert tts._format_speed(1.0) == "+0%"
        assert tts._format_speed(2.0) == "+100%"
        assert tts._format_speed(0.5) == "-50%"
        assert tts._format_speed(1.5) == "+50%"
        assert tts._format_speed(0.75) == "-25%"

    def test_speed_config(self):
        """Test that speed parameter is properly configured."""
        tts = TTSEngine({"speed": 1.5})
        assert tts._speed == 1.5

        tts.configure({"speed": 2.0})
        assert tts._speed == 2.0

        tts.configure({})
        assert tts._speed == 2.0  # Should retain last value

    @patch("modules.tts_engine.TTSEngine._run_edge_tts")
    def test_edge_tts_uses_speed(self, mock_run_edge):
        """Test that edge-tts generation uses the configured speed."""
        tts = TTSEngine({"engine": "edge-tts", "speed": 0.5})
        tts._tts_dir = "/tmp/tts"

        data = PipelineData(chunk_index=1, translated_text="Hello world")
        tts._do_process(data)

        mock_run_edge.assert_called_once()
        # Verify the speed was set correctly
        assert tts._speed == 0.5
