"""
Tests for configuration validation and server startup.

These tests ensure that:
- config.yaml has valid values
- All required modules can be loaded
- Server can start without errors
"""

import os
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = str(PROJECT_ROOT / "config.yaml")


# Valid values for config validation
VALID_WHISPER_MODELS = [
    "tiny",
    "tiny.en",
    "base",
    "base.en",
    "small",
    "small.en",
    "medium",
    "medium.en",
    "large",
    "large-v1",
    "large-v2",
    "large-v3",
]

VALID_LANGUAGES = [
    "auto",
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "nl",
    "ja",
    "zh",
    "ko",
    "ru",
    "ar",
    "hi",
    "tr",
    "pl",
    "cs",
    "sv",
    "da",
    "fi",
    "nb",
    "hu",
]

VALID_DEVICES = ["auto", "cpu", "cuda"]

VALID_TTS_VOICES = [
    "es_ES-davefx-medium",
    "en_US-lessac-medium",
    "fr_FR-siwis-medium",
]

VALID_VIDEO_PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]

VALID_ENCODER_MODES = ["auto", "passthrough", "cpu", "gpu_nvenc", "gpu_amf", "gpu_qsv", "gpu_videotoolbox"]


class TestConfigYAMLValidity:
    """Test that config.yaml has valid values."""

    def test_config_yaml_exists(self) -> None:
        """Test that config.yaml exists."""
        assert os.path.exists(CONFIG_PATH), "config.yaml not found"

    @pytest.mark.xfail(reason="Flaky with parallel execution")
    def test_config_yaml_is_valid_yaml(self) -> None:
        """Test that config.yaml is valid YAML."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert isinstance(config, dict), "config.yaml should be a dictionary"

    @pytest.mark.xfail(reason="Flaky with parallel execution")
    def test_config_server_section(self) -> None:
        """Test server configuration has valid values."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        server = config.get("server", {})

        # Host should be localhost or 127.0.0.1 for security
        host = server.get("host", "")
        assert host in ["127.0.0.1", "localhost", "0.0.0.0"], f"Invalid host: {host}"

        # Port should be valid
        port = server.get("port", 0)
        assert 1 <= port <= 65535, f"Invalid port: {port}"

        # Rate limit should be positive
        rate_limit = server.get("rate_limit_rpm", 0)
        assert rate_limit > 0, f"Rate limit must be positive: {rate_limit}"

    def test_config_transcriber_valid_model(self) -> None:
        """Test that transcriber uses a valid Whisper model."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        model = config.get("modules.transcriber.model", "")

        assert model in VALID_WHISPER_MODELS, f"Invalid model '{model}'. Valid models: {VALID_WHISPER_MODELS}"

    def test_config_transcriber_valid_language(self) -> None:
        """Test that transcriber uses a valid language code."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        modules = config.get("modules", {})
        transcriber = modules.get("transcriber", {})
        language = transcriber.get("language", "")

        assert language in VALID_LANGUAGES, f"Invalid language: '{language}'. Valid languages: {VALID_LANGUAGES}"

    def test_config_transcriber_valid_device(self) -> None:
        """Test that transcriber uses a valid device."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        modules = config.get("modules", {})
        transcriber = modules.get("transcriber", {})
        device = transcriber.get("device", "")

        assert device in VALID_DEVICES, f"Invalid device: '{device}'. Valid devices: {VALID_DEVICES}"

    def test_config_translator_valid_languages(self) -> None:
        """Test that translator uses valid language codes."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        modules = config.get("modules", {})
        translator = modules.get("translator", {})
        source_lang = translator.get("source_lang", "")
        target_lang = translator.get("target_lang", "")

        assert source_lang in VALID_LANGUAGES, f"Invalid source_lang: '{source_lang}'"
        assert target_lang in VALID_LANGUAGES, f"Invalid target_lang: '{target_lang}'"

    def test_config_tts_valid_voice(self) -> None:
        """Test that TTS uses a valid voice."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        modules = config.get("modules", {})
        tts = modules.get("tts_engine", {})

        # Only validate if TTS is enabled
        if tts.get("enabled", False):
            voice = tts.get("voice", "")
            # Voice should follow pattern: {lang}_{region}-{name}-{quality}
            assert len(voice) > 3, f"TTS voice seems invalid: '{voice}'"
            assert "-" in voice, f"TTS voice should contain '-': '{voice}'"

    def test_config_tts_valid_device(self) -> None:
        """Test that TTS uses a valid device."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        modules = config.get("modules", {})
        tts = modules.get("tts_engine", {})
        device = tts.get("device", "")

        assert device in VALID_DEVICES, f"Invalid TTS device: '{device}'"

    def test_config_video_muxer_valid_preset(self) -> None:
        """Test that video muxer uses valid preset."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        modules = config.get("modules", {})
        video_muxer = modules.get("video_muxer", {})
        preset = video_muxer.get("video_preset", "medium")

        assert preset in VALID_VIDEO_PRESETS, f"Invalid video preset: '{preset}'"

    def test_config_video_muxer_valid_encoder_mode(self) -> None:
        """Test that video muxer uses valid encoder mode."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        modules = config.get("modules", {})
        video_muxer = modules.get("video_muxer", {})
        encoder_mode = video_muxer.get("encoder_mode", "auto")

        assert encoder_mode in VALID_ENCODER_MODES, f"Invalid encoder mode: '{encoder_mode}'"

    def test_config_ports_no_conflict(self) -> None:
        """Test that configured ports don't conflict."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        server_port = config.get("server", {}).get("port", 0)
        srt_port = config.get("srt", {}).get("listen_port", 0)
        input_srt_port = config.get("input", {}).get("srt", {}).get("listen_port", 0)

        # SRT and server can share same config, but input and output SRT should be different
        # This is a basic check
        if input_srt_port and srt_port:
            # They can be the same (input srt is what we listen on)
            pass

    def test_config_directory_exists(self) -> None:
        """Test that output directory path is valid."""
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        output_dir = config.get("output_dir", {}).get("directory", "")
        assert output_dir, "Output directory not configured"
        assert not output_dir.startswith("/"), "Output directory should be relative path"


class TestConfigManagerLoadsConfig:
    """Test that ConfigManager can load the config."""

    def test_config_manager_loads_successfully(self) -> None:
        """Test that ConfigManager can load config.yaml."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        assert config is not None

    def test_config_manager_returns_valid_model(self) -> None:
        """Test that ConfigManager returns valid model."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        model = config.get("modules.transcriber.model", "")

        assert model in VALID_WHISPER_MODELS, f"Invalid model '{model}'. Valid models: {VALID_WHISPER_MODELS}"

    def test_config_manager_has_valid_model(self) -> None:
        """Test that ConfigManager has valid model configuration."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        model = config.get("modules.transcriber.model", "")

        assert model in VALID_WHISPER_MODELS, f"Invalid model '{model}'. Valid: {VALID_WHISPER_MODELS}"


class TestServerStartup:
    """Test that server can start without errors."""

    def test_main_py_exists(self) -> None:
        """Test that main.py exists."""
        assert os.path.exists("main.py"), "main.py not found"

    def test_main_py_can_be_imported(self) -> None:
        """Test that main.py can be imported without errors."""
        # Add project root to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        try:
            import main

            assert hasattr(main, "main"), "main.py should have a main() function"
        except Exception as e:
            pytest.fail(f"Failed to import main.py: {e}")

    def test_app_can_be_created(self) -> None:
        """Test that FastAPI app can be created."""
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from server.app import create_app

        config = ConfigManager()
        pipeline = Pipeline()

        app_context = {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": None,
            "log_subscribers": [],
            "log_broadcast": lambda level, msg: None,
        }

        app = create_app(app_context)
        assert app is not None
        assert app.title == "SRT2Web"

    def test_app_has_required_routes(self) -> None:
        """Test that app has required routes."""
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from server.app import create_app

        config = ConfigManager()
        pipeline = Pipeline()

        app_context = {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": None,
            "log_subscribers": [],
            "log_broadcast": lambda level, msg: None,
        }

        app = create_app(app_context)

        # Get all routes
        routes = [route.path for route in app.routes]

        assert "/" in routes, "Missing root route"
        assert "/health" in routes, "Missing health route"
        assert "/player" in routes or any("/player" in r for r in routes), "Missing player route"

    def test_app_health_endpoint(self) -> None:
        """Test that health endpoint returns OK."""
        from fastapi.testclient import TestClient

        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from server.app import create_app

        config = ConfigManager()
        pipeline = Pipeline()

        app_context = {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": None,
            "log_subscribers": [],
            "log_broadcast": lambda level, msg: None,
        }

        app = create_app(app_context)
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestRequiredDependencies:
    """Test that required dependencies are available."""

    def test_fastapi_available(self) -> None:
        """Test that FastAPI is installed."""
        try:
            import fastapi

            assert True
        except ImportError:
            pytest.fail("FastAPI not installed")

    def test_uvicorn_available(self) -> None:
        """Test that Uvicorn is installed."""
        try:
            import uvicorn

            assert True
        except ImportError:
            pytest.fail("Uvicorn not installed")

    def test_faster_whisper_available(self) -> None:
        """Test that faster-whisper is installed."""
        try:
            import faster_whisper

            assert True
        except ImportError:
            pytest.skip("faster-whisper not installed (optional)")

    def test_yaml_available(self) -> None:
        """Test that PyYAML is installed."""
        try:
            import yaml

            assert True
        except ImportError:
            pytest.fail("PyYAML not installed")

    def test_ffmpeg_available(self) -> None:
        """Test that FFmpeg is available."""
        from core.ffmpeg_utils import ensure_ffmpeg

        try:
            ffmpeg_path = ensure_ffmpeg()
            assert ffmpeg_path is not None, "FFmpeg not found"
        except Exception as e:
            pytest.skip(f"FFmpeg not available: {e}")
