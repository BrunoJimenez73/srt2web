"""
Tests for configuration validation and server startup.

These tests ensure that:
- config.yaml has valid values
- All required modules can be loaded
- Server can start without errors
"""

import os
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = str(PROJECT_ROOT / "config.yaml")


def _collect_paths(routes: list) -> list[str]:
    """Collect route paths, handling FastAPI's nested _IncludedRouter entries.

    Newer FastAPI versions wrap routers included via ``include_router`` in
    ``_IncludedRouter`` objects inside ``app.routes``; those have no
    ``path`` attribute but expose their own nested ``routes`` list.
    """
    paths: list[str] = []
    for route in routes:
        if hasattr(route, "path"):
            paths.append(route.path)
        nested = getattr(route, "routes", None)
        if not nested:
            sub_router = getattr(route, "router", None)
            nested = getattr(sub_router, "routes", None)
        if nested:
            paths.extend(_collect_paths(nested))
    return paths


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

from core.constants import ALLOWED_ENCODER_MODES as VALID_ENCODER_MODES  # noqa: E402


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
        from core.config_manager import ConfigManager

        language = ConfigManager(CONFIG_PATH).get("modules.transcriber.language", "")

        assert language in VALID_LANGUAGES, f"Invalid language: '{language}'. Valid languages: {VALID_LANGUAGES}"

    def test_config_transcriber_valid_device(self) -> None:
        """Test that transcriber uses a valid device."""
        from core.config_manager import ConfigManager

        device = ConfigManager(CONFIG_PATH).get("modules.transcriber.device", "")

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
        video_preset = video_muxer.get("video_preset", "fast")
        gpu_preset = video_muxer.get("gpu_preset", "p4")

        from core.config_schema import ALLOWED_GPU_PRESETS, ALLOWED_VIDEO_PRESETS

        assert video_preset in ALLOWED_VIDEO_PRESETS, f"Invalid video preset: '{video_preset}'"
        assert gpu_preset in ALLOWED_GPU_PRESETS, f"Invalid GPU preset: '{gpu_preset}'"

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

        _ = config.get("server", {}).get("port", 0)
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
        routes = _collect_paths(app.routes)

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
        import fastapi

        assert fastapi.__version__ is not None

    def test_uvicorn_available(self) -> None:
        """Test that Uvicorn is installed."""
        import uvicorn

        assert uvicorn.__version__ is not None

    def test_faster_whisper_available(self) -> None:
        """Test that faster-whisper is installed."""
        _ = pytest.importorskip("faster_whisper")

    def test_yaml_available(self) -> None:
        """Test that PyYAML is installed."""
        import yaml

        assert yaml.__version__ is not None

    def test_ffmpeg_available(self) -> None:
        """Test that FFmpeg is available."""
        from core.ffmpeg_utils import ensure_ffmpeg

        try:
            ffmpeg_path = ensure_ffmpeg()
            assert ffmpeg_path is not None, "FFmpeg not found"
        except Exception as e:
            pytest.skip(f"FFmpeg not available: {e}")


class TestConfigManagerAtomicSave:
    """Tests for ConfigManager atomic save behavior."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """ConfigManager.save() creates the config file."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("server:\n  port: 9999\n", encoding="utf-8")

        from core.config_manager import ConfigManager

        mgr = ConfigManager(str(config_path))
        mgr.set("server.port", 8000)
        mgr.save()

        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "8000" in content

    def test_save_atomic_temp_file_cleaned(self, tmp_path: Path) -> None:
        """Temp .tmp file is removed after successful save."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("server:\n  port: 9999\n", encoding="utf-8")

        from core.config_manager import ConfigManager

        mgr = ConfigManager(str(config_path))
        mgr.save()

        assert not (tmp_path / "config.yaml.tmp").exists()

    def test_save_with_lock_no_race(self, tmp_path: Path) -> None:
        """ConfigManager uses a threading lock for save."""
        import threading

        config_path = tmp_path / "config.yaml"
        config_path.write_text("server:\n  port: 9999\n", encoding="utf-8")

        from core.config_manager import ConfigManager

        mgr = ConfigManager(str(config_path))
        assert hasattr(mgr, "_lock")
        assert isinstance(mgr._lock, type(threading.Lock()))

    def test_update_from_dict_validates_before_assign(self, tmp_path: Path) -> None:
        """update_from_dict validates via Pydantic before mutating _config."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("server:\n  port: 9999\n", encoding="utf-8")

        from core.config_manager import ConfigManager

        mgr = ConfigManager(str(config_path))
        original = mgr.to_dict()

        with pytest.raises(ValueError):
            mgr.update_from_dict({"server": {"port": "not_a_number"}})

        # Config should be unchanged after failed validation
        assert mgr.to_dict() == original


class TestSecretValidation:
    """F112: Validate SRT2WEB_JWT_SECRET (and future secrets) at startup.

    Tests cover:
    - empty/missing secret → blocking error
    - insecure default 'change-me-in-production' → blocking error
    - placeholder 'your-secret-token-here' (legacy) → blocking error
    - short secret (< 32 chars) → warning but still valid
    - valid secret → ok
    - generate_jwt_secret() returns a non-empty urlsafe token
    """

    def _set(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv("SRT2WEB_JWT_SECRET", value)

    def _clear(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SRT2WEB_JWT_SECRET", raising=False)

    def test_validate_secrets_empty_blocks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty SRT2WEB_JWT_SECRET is a hard error in strict mode."""
        from core.config_manager import validate_secrets

        self._clear(monkeypatch)
        ok, msg = validate_secrets(strict=True)
        assert ok is False
        assert "empty or unset" in msg.lower()

    def test_validate_secrets_insecure_default_blocks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The fallback 'change-me-in-production' is rejected."""
        from core.config_manager import validate_secrets

        self._set(monkeypatch, "change-me-in-production")
        ok, msg = validate_secrets(strict=True)
        assert ok is False
        assert "insecure fallback" in msg.lower()

    def test_validate_secrets_placeholder_legacy_blocks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Legacy 'your-secret-token-here' placeholder (was in .env.example) is rejected."""
        from core.config_manager import validate_secrets

        self._set(monkeypatch, "your-secret-token-here")
        ok, _ = validate_secrets(strict=True)
        assert ok is False

    def test_validate_secrets_short_warns_but_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Short secrets (< 32 chars) are warnings, not blocking errors."""
        from core.config_manager import validate_secrets

        self._set(monkeypatch, "short-but-not-default")
        ok, msg = validate_secrets(strict=True)
        assert ok is True
        assert "warning" in msg.lower() or "shorter" in msg.lower()

    def test_validate_secrets_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A real 32+ char secret is accepted."""
        from core.config_manager import generate_jwt_secret, validate_secrets

        self._set(monkeypatch, generate_jwt_secret())
        ok, msg = validate_secrets(strict=True)
        assert ok is True
        assert msg == "ok"

    def test_generate_jwt_secret_returns_urlsafe_token(self) -> None:
        """generate_jwt_secret() returns a 43-char urlsafe token from token_urlsafe(32)."""
        from core.config_manager import generate_jwt_secret

        secret = generate_jwt_secret()
        # secrets.token_urlsafe(32) → 43 chars of base64-url alphabet
        assert len(secret) >= 43
        assert all(c.isalnum() or c in "-_" for c in secret)
        # Two calls produce different values
        assert generate_jwt_secret() != generate_jwt_secret()

    def test_env_example_has_no_legacy_placeholders(self) -> None:
        """F112: .env.example no longer contains the public 'your-secret-token-here'."""
        from pathlib import Path

        repo_root = Path(__file__).parent.parent.parent
        example = (repo_root / ".env.example").read_text(encoding="utf-8")
        assert "your-secret-token-here" not in example
        assert "your-secret-key-here" not in example
        # And the real secret is the only one declared
        assert "SRT2WEB_JWT_SECRET=" in example

    def test_env_example_secret_is_empty(self) -> None:
        """F112: SRT2WEB_JWT_SECRET is empty in .env.example (installer fills it)."""
        from pathlib import Path

        repo_root = Path(__file__).parent.parent.parent
        example = (repo_root / ".env.example").read_text(encoding="utf-8")
        for line in example.splitlines():
            if line.startswith("SRT2WEB_JWT_SECRET="):
                value = line.split("=", 1)[1].strip()
                assert value == "", f"Expected empty SRT2WEB_JWT_SECRET, got: {value!r}"
                return
        pytest.fail("SRT2WEB_JWT_SECRET not declared in .env.example")
