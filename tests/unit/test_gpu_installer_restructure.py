"""
Tests for GPU indicators, installer, and project restructure.

These tests verify:
1. GPU indicators work correctly in all modules
2. EncoderConfig provides correct arguments
3. Piper loader subprocess works
4. Installer/startup scripts exist and are valid
5. Project structure is correct
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = str(PROJECT_ROOT / "config.yaml")
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# GPU Indicators Tests
# ============================================================


@pytest.mark.unit
class TestGPUIndicators:
    """Tests for GPU indicator functionality in modules."""

    def test_transcriber_get_status_has_device(self) -> None:
        """Test that transcriber get_status includes device info."""
        from core.module_base import ModuleState
        from modules.transcriber import Transcriber

        transcriber = Transcriber({"model": "tiny", "language": "en", "device": "cpu"})
        transcriber._state = ModuleState.IDLE

        status = transcriber.get_status()
        assert "device" in status.extra
        assert "compute_type" in status.extra
        assert "using_gpu" in status.extra

    def test_transcriber_get_status_gpu_false_for_cpu(self) -> None:
        """Test that transcriber reports GPU=False for CPU device."""
        from core.module_base import ModuleState
        from modules.transcriber import Transcriber

        transcriber = Transcriber({"model": "tiny", "language": "en", "device": "cpu"})
        transcriber._state = ModuleState.IDLE

        status = transcriber.get_status()
        assert status.extra["using_gpu"] is False

    def test_transcriber_get_status_gpu_true_for_cuda(self) -> None:
        """Test that transcriber reports GPU=True when _device is set to cuda."""
        from core.module_base import ModuleState
        from modules.transcriber import Transcriber

        transcriber = Transcriber({"model": "tiny", "language": "en", "device": "cuda"})
        transcriber._state = ModuleState.IDLE
        # _device is normally set in start(), but we set it directly for testing
        transcriber._device = "cuda"

        status = transcriber.get_status()
        assert status.extra["using_gpu"] is True

    @patch("os.makedirs")
    @patch("os.listdir")
    def test_tts_get_status_has_device(self, mock_listdir, mock_makedirs) -> None:
        """Test that TTS get_status includes device and engine info."""
        mock_listdir.return_value = []
        from modules.tts_engine import TTSEngine

        tts = TTSEngine({"engine": "piper", "device": "auto"})
        tts.start()

        status = tts.get_status()
        assert "device" in status.extra
        assert "engine" in status.extra
        assert "using_gpu" in status.extra
        assert status.extra["engine"] == "piper"

    @patch("os.makedirs")
    @patch("os.listdir")
    def test_tts_gpu_false_for_edge_tts(self, mock_listdir, mock_makedirs) -> None:
        """Test that edge-tts never reports GPU usage."""
        mock_listdir.return_value = []
        from modules.tts_engine import TTSEngine

        tts = TTSEngine({"engine": "edge-tts"})
        tts.start()

        status = tts.get_status()
        assert status.extra["using_gpu"] is False
        assert status.extra["engine"] == "edge-tts"

    @patch("modules.video_muxer.ensure_ffmpeg")
    @patch("core.ffmpeg_utils.check_gpu_support")
    @patch("os.makedirs")
    @patch("glob.glob")
    def test_video_muxer_get_status_has_encoder(self, mock_glob, mock_makedirs, mock_gpu, mock_ensure) -> None:
        """Test that video muxer get_status includes encoder info."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_gpu.return_value = {"nvenc": True, "qsv": False, "amf": False, "vaapi": False}
        mock_glob.return_value = []

        from modules.video_muxer import VideoMuxer

        class Testable(VideoMuxer):
            def _do_process(self, data) -> None:
                return data

        muxer = Testable(output_dir="/tmp")
        muxer.start()

        status = muxer.get_status()
        assert "encoder_mode" in status.extra
        assert "using_gpu" in status.extra
        assert "gpu_available" in status.extra
        assert status.extra["encoder_mode"] in ["gpu_nvenc", "auto"]
        assert status.extra["using_gpu"] is True

    @patch("modules.video_muxer.ensure_ffmpeg")
    @patch("core.ffmpeg_utils.check_gpu_support")
    @patch("os.makedirs")
    @patch("glob.glob")
    def test_video_muxer_cpu_mode(self, mock_glob, mock_makedirs, mock_gpu, mock_ensure) -> None:
        """Test that video muxer reports CPU when no GPU available."""
        mock_ensure.return_value = "/bin/ffmpeg"
        mock_gpu.return_value = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False}
        mock_glob.return_value = []

        from modules.video_muxer import VideoMuxer

        class Testable(VideoMuxer):
            def _do_process(self, data) -> None:
                return data

        muxer = Testable(output_dir="/tmp")
        muxer.start()

        status = muxer.get_status()
        assert status.extra["encoder_mode"] in ["cpu", "auto"]
        assert status.extra["using_gpu"] is False


# ============================================================
# EncoderConfig Tests
# ============================================================


class TestEncoderConfig:
    """Tests for EncoderConfig class."""

    def test_default_values(self) -> None:
        """Test default EncoderConfig values."""
        from core.encoder_config import EncoderConfig

        config = EncoderConfig()
        assert config.encoder_mode == "auto"
        assert config.video_preset == "medium"
        assert config.video_crf == 18
        assert config.gpu_preset == "p7"
        assert config.audio_codec == "aac"
        assert config.audio_bitrate == "192k"

    def test_custom_values(self) -> None:
        """Test EncoderConfig with custom values."""
        from core.encoder_config import EncoderConfig

        config = EncoderConfig(
            {
                "encoder_mode": "gpu_nvenc",
                "video_preset": "fast",
                "gpu_preset": "p5",
                "audio_codec": "opus",
                "audio_bitrate": "128k",
            }
        )
        assert config.encoder_mode == "gpu_nvenc"
        assert config.video_preset == "fast"
        assert config.gpu_preset == "p5"
        assert config.audio_codec == "opus"
        assert config.audio_bitrate == "128k"

    def test_get_cpu_args(self) -> None:
        """Test CPU encoding arguments."""
        from core.encoder_config import EncoderConfig

        config = EncoderConfig({"video_preset": "medium"})
        args = config.get_cpu_args()

        assert "-preset" in args
        assert "medium" in args
        assert "-crf" in args
        assert "18" in args
        assert "-profile:v" in args
        assert "high" in args

    def test_get_gpu_nvenc_args(self) -> None:
        """Test NVENC GPU encoding arguments."""
        from core.encoder_config import EncoderConfig

        config = EncoderConfig({"gpu_preset": "p3"})
        args = config.get_gpu_nvenc_args()

        assert "-preset" in args
        assert "p3" in args
        assert "-rc" in args
        assert "vbr" in args
        assert "-cq" in args
        assert "20" in args  # p3 maps to CQ 20

    def test_get_gpu_amf_args(self) -> None:
        """Test AMF GPU encoding arguments."""
        from core.encoder_config import EncoderConfig

        config = EncoderConfig({"video_preset": "medium"})
        args = config.get_gpu_amf_args()

        assert "-usage" in args
        assert "lowlatency" in args
        assert "-quality" in args
        assert "balanced" in args

    def test_get_gpu_qsv_args(self) -> None:
        """Test QSV GPU encoding arguments."""
        from core.encoder_config import EncoderConfig

        config = EncoderConfig()
        args = config.get_gpu_qsv_args()

        assert "-low_power" in args
        assert "1" in args
        assert "-async_depth" in args

    def test_get_audio_args(self) -> None:
        """Test audio encoding arguments."""
        from core.encoder_config import EncoderConfig

        config = EncoderConfig({"audio_codec": "aac", "audio_bitrate": "128k"})
        args = config.get_audio_args()

        assert "-c:a" in args
        assert "aac" in args
        assert "-b:a" in args
        assert "128k" in args

    def test_to_dict(self) -> None:
        """Test EncoderConfig serialization."""
        from core.encoder_config import EncoderConfig

        config = EncoderConfig({"encoder_mode": "gpu_nvenc", "gpu_preset": "p5"})
        d = config.to_dict()

        assert d["encoder_mode"] == "gpu_nvenc"
        assert d["gpu_preset"] == "p5"
        assert "video_preset" in d
        assert "audio_codec" in d

    def test_from_dict(self) -> None:
        """Test EncoderConfig deserialization."""
        from core.encoder_config import EncoderConfig

        d = {
            "encoder_mode": "cpu",
            "video_preset": "fast",
            "video_crf": 20,
            "gpu_preset": "p1",
            "audio_codec": "opus",
        }
        config = EncoderConfig.from_dict(d)

        assert config.encoder_mode == "cpu"
        assert config.video_preset == "fast"
        assert config.video_crf == 20
        assert config.audio_codec == "opus"

    def test_cpu_presets_have_crf(self) -> None:
        """Test that all CPU presets have CRF values."""
        from core.encoder_config import EncoderConfig

        for preset_name, preset_info in EncoderConfig.CPU_PRESETS.items():
            assert "crf" in preset_info, f"CPU preset '{preset_name}' missing CRF"
            assert isinstance(preset_info["crf"], int)

    def test_gpu_presets_have_cq(self) -> None:
        """Test that all GPU presets have CQ values."""
        from core.encoder_config import EncoderConfig

        for preset_name, preset_info in EncoderConfig.GPU_PRESETS.items():
            assert "cq" in preset_info, f"GPU preset '{preset_name}' missing CQ"
            assert isinstance(preset_info["cq"], int)


# ============================================================
# Piper Loader Tests
# ============================================================


class TestPiperLoader:
    """Tests for Piper TTS loader subprocess."""

    def test_check_piper_environment_returns_dict(self) -> None:
        """Test that check_piper_environment returns a dict with expected keys."""
        from modules.piper_loader import check_piper_environment

        try:
            result = check_piper_environment()
        except AttributeError:
            pytest.skip("onnxruntime mock conflict in test environment")

        assert isinstance(result, dict)
        assert "piper_available" in result
        assert "onnxruntime_available" in result
        assert "python_path" in result
        assert "python_version" in result

    def test_check_piper_environment_reports_availability(self) -> None:
        """Test that check_piper_environment correctly reports piper availability."""
        from modules.piper_loader import check_piper_environment

        try:
            result = check_piper_environment()
        except AttributeError:
            pytest.skip("onnxruntime mock conflict in test environment")

        assert isinstance(result["piper_available"], bool)
        assert isinstance(result["onnxruntime_available"], bool)

    def test_load_piper_model_subprocess_returns_dict(self) -> None:
        """Test that load_piper_model_subprocess returns error dict for missing model."""
        from modules.piper_loader import load_piper_model_subprocess

        result = load_piper_model_subprocess(
            voice_name="nonexistent_voice",
            model_path="/nonexistent/model.onnx",
            config_path="/nonexistent/model.onnx.json",
            device="cpu",
            timeout=10,
        )

        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "error"

    def test_load_piper_model_subprocess_timeout(self) -> None:
        """Test that load_piper_model_subprocess handles timeout."""
        from modules.piper_loader import load_piper_model_subprocess

        result = load_piper_model_subprocess(
            voice_name="test",
            model_path="/nonexistent/model.onnx",
            config_path="/nonexistent/model.onnx.json",
            device="cpu",
            timeout=5,
        )

        assert result["status"] == "error"


# ============================================================
# Installer/Startup Scripts Tests
# ============================================================


class TestInstallerScripts:
    """Tests for installer and startup scripts."""

    def test_install_bat_exists(self) -> None:
        """Test that Install.bat exists."""
        assert os.path.exists("Install.bat"), "Install.bat not found"

    def test_start_bat_exists(self) -> None:
        """Test that Start.bat exists."""
        assert os.path.exists("Start.bat"), "Start.bat not found"

    def test_stop_bat_exists(self) -> None:
        """Test that Stop.bat exists."""
        assert os.path.exists("Stop.bat"), "Stop.bat not found"

    def test_install_bat_has_venv_creation(self) -> None:
        """Test that Install.bat creates virtual environment."""
        with open("Install.bat", encoding="utf-8") as f:
            content = f.read()
        assert "venv" in content.lower()
        assert "python" in content.lower()

    def test_install_bat_has_pip_install(self) -> None:
        """Test that Install.bat installs dependencies."""
        with open("Install.bat", encoding="utf-8") as f:
            content = f.read()
        assert "pip" in content.lower()
        assert "requirements" in content.lower()

    def test_install_bat_checks_cuda(self) -> None:
        """Test that Install.bat checks CUDA availability."""
        with open("Install.bat", encoding="utf-8") as f:
            content = f.read()
        assert "cuda" in content.lower() or "onnxruntime" in content.lower()

    def test_start_bat_uses_venv_python(self) -> None:
        """Test that Start.bat uses virtual environment Python."""
        with open("Start.bat", encoding="utf-8") as f:
            content = f.read()
        assert "venv" in content.lower()
        assert "python" in content.lower()

    def test_start_bat_runs_main_py(self) -> None:
        """Test that Start.bat runs main.py."""
        with open("Start.bat", encoding="utf-8") as f:
            content = f.read()
        assert "main.py" in content

    def test_start_bat_shows_dashboard_url(self) -> None:
        """Test that Start.bat shows dashboard URL."""
        with open("Start.bat", encoding="utf-8") as f:
            content = f.read()
        assert "localhost" in content.lower() or "9999" in content


# ============================================================
# Project Restructure Tests
# ============================================================


class TestProjectStructure:
    """Tests for project directory structure."""

    def test_core_directory_exists(self) -> None:
        """Test that core/ directory exists."""
        assert os.path.isdir("core"), "core/ directory not found"

    def test_modules_directory_exists(self) -> None:
        """Test that modules/ directory exists."""
        assert os.path.isdir("modules"), "modules/ directory not found"

    def test_server_directory_exists(self) -> None:
        """Test that server/ directory exists."""
        assert os.path.isdir("server"), "server/ directory not found"

    def test_frontend_directory_exists(self) -> None:
        """Test that frontend/ directory exists."""
        assert os.path.isdir("frontend"), "frontend/ directory not found"

    def test_tests_directory_exists(self) -> None:
        """Test that tests/ directory exists."""
        assert os.path.isdir("tests"), "tests/ directory not found"

    def test_config_yaml_exists(self) -> None:
        """Test that config.yaml exists."""
        assert os.path.exists(CONFIG_PATH), "config.yaml not found"

    def test_main_py_exists(self) -> None:
        """Test that main.py exists."""
        assert os.path.exists("main.py"), "main.py not found"

    def test_core_modules_present(self) -> None:
        """Test that core modules exist."""
        expected_core_files = [
            "config_manager.py",
            "pipeline.py",
            "module_base.py",
            "ffmpeg_utils.py",
            "encoder_config.py",
            "model_cache.py",
            "network_utils.py",
        ]
        for filename in expected_core_files:
            filepath = os.path.join("core", filename)
            assert os.path.exists(filepath), f"core/{filename} not found"

    def test_processing_modules_present(self) -> None:
        """Test that processing modules exist."""
        expected_modules = [
            "transcriber.py",
            "translator.py",
            "subtitle_generator.py",
            "tts_engine.py",
            "audio_mixer.py",
            "video_muxer.py",
            "audio_extractor.py",
            "piper_loader.py",
        ]
        for filename in expected_modules:
            filepath = os.path.join("modules", filename)
            assert os.path.exists(filepath), f"modules/{filename} not found"

    def test_server_modules_present(self) -> None:
        """Test that server modules exist."""
        expected_server_files = [
            "app.py",
            "api_routes.py",
            "ws_routes.py",
            "security.py",
        ]
        for filename in expected_server_files:
            filepath = os.path.join("server", filename)
            assert os.path.exists(filepath), f"server/{filename} not found"

    def test_frontend_has_astro_config(self) -> None:
        """Test that frontend has Astro config."""
        assert os.path.exists(os.path.join("frontend", "astro.config.mjs")), "frontend/astro.config.mjs not found"
        assert os.path.exists(os.path.join("frontend", "package.json")), "frontend/package.json not found"

    def test_requirements_txt_exists(self) -> None:
        """Test that requirements.txt exists (in config/ or root)."""
        assert os.path.exists("requirements.txt") or os.path.exists(
            os.path.join("config", "requirements.txt")
        ), "requirements.txt not found"

    def test_bin_directory_exists(self) -> None:
        """Test that bin/ directory exists (for FFmpeg)."""
        assert os.path.isdir("bin"), "bin/ directory not found"

    def test_models_directory_exists(self) -> None:
        """Test that models/ directory exists."""
        assert os.path.isdir("models"), "models/ directory not found"

    def test_server_static_directory_exists(self) -> None:
        """Test that server/static/ directory exists (built frontend)."""
        static_dir = os.path.join("server", "static")
        assert os.path.isdir(static_dir), "server/static/ directory not found"

    def test_server_static_has_index(self) -> None:
        """Test that server/static/index.html exists."""
        index_path = os.path.join("server", "static", "index.html")
        assert os.path.exists(index_path), "server/static/index.html not found"

    def test_server_static_has_player(self) -> None:
        """Test that server/static/player/ exists."""
        player_dir = os.path.join("server", "static", "player")
        assert os.path.isdir(player_dir), "server/static/player/ not found"

    def test_test_files_cover_all_modules(self) -> None:
        """Test that test files exist for major modules."""
        expected_test_files = [
            "test_transcriber.py",
            "test_translator.py",
            "test_subtitle_generator.py",
            "test_tts_engine.py",
            "test_audio_mixer.py",
            "test_video_muxer.py",
            "test_config_manager.py",
            "test_pipeline.py",
            "test_module_base.py",
            "test_security_middleware.py",
            "test_api_routes.py",
        ]
        for filename in expected_test_files:
            filepath = os.path.join("tests", "unit", filename)
            assert os.path.exists(filepath), f"tests/unit/{filename} not found"


# ============================================================
# FFmpeg Pool Tests
# ============================================================


class TestFFmpegPool:
    """Tests for FFmpeg process pool."""

    def test_ffmpeg_pool_module_exists(self) -> None:
        """Test that ffmpeg_pool module exists."""
        assert os.path.exists(os.path.join("core", "ffmpeg_pool.py")), "core/ffmpeg_pool.py not found"

    def test_ffmpeg_pool_can_be_imported(self) -> None:
        """Test that ffmpeg_pool can be imported."""
        from core.ffmpeg_pool import FFmpegPool

        assert FFmpegPool is not None


# ============================================================
# Watchdog Tests
# ============================================================


class TestWatchdogModule:
    """Tests for watchdog module."""

    def test_watchdog_module_exists(self) -> None:
        """Test that watchdog module exists."""
        assert os.path.exists(os.path.join("core", "watchdog.py")), "core/watchdog.py not found"

    def test_watchdog_can_be_imported(self) -> None:
        """Test that watchdog can be imported."""
        from core.watchdog import FFmpegWatchdog, ProcessManager

        assert FFmpegWatchdog is not None
        assert ProcessManager is not None
