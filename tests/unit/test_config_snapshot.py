"""
Tests de snapshot/contrato para la configuracion por defecto.

Verifican que los defaults del schema Pydantic sean estables y consistentes.
Cualquier cambio intencional debe reflejarse aqui.
"""

import os

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_manager import DEFAULT_CONFIG, ConfigManager  # noqa: E402
from core.config_schema import (  # noqa: E402
    SRT2WebConfig,
)


@pytest.mark.unit
class TestDefaultConfigSnapshot:
    """Snapshot tests para la configuracion por defecto."""

    def test_default_config_has_all_sections(self):
        """Default config should have all top-level sections."""
        expected_sections = {
            "server",
            "input",
            "output",
            "pipeline",
            "modules",
            "output_dir",
            "subtitle_sync",
            "webhooks",
            "pipeline_validation",
        }
        assert set(DEFAULT_CONFIG.keys()) == expected_sections

    def test_default_server_section(self):
        """Server defaults should match expected values."""
        server = DEFAULT_CONFIG["server"]
        assert server["host"] == "127.0.0.1"
        assert server["port"] == 9999
        assert server["auth_token"] == ""
        assert server["rate_limit_rpm"] == 600
        assert server["max_request_size_mb"] == 100

    def test_default_pipeline_section(self):
        """Pipeline defaults should match expected values."""
        pipeline = DEFAULT_CONFIG["pipeline"]
        assert pipeline["chunk_duration_sec"] == 5
        assert pipeline["mode"] == "thread_parallel"
        assert pipeline["max_concurrent_chunks"] == 4
        assert pipeline["buffer_size"] == 10
        assert pipeline["retry_attempts"] == 3
        assert pipeline["retry_delay"] == 1.0

    def test_default_input_section(self):
        """Input defaults should have SRT as default type."""
        input_cfg = DEFAULT_CONFIG["input"]
        assert input_cfg["type"] == "srt"
        assert input_cfg["srt"]["listen_port"] == 9000
        assert input_cfg["srt"]["mode"] == "listener"
        assert input_cfg["srt"]["latency_ms"] == 200
        # SRT chunk_duration_syncs with pipeline.chunk_duration_sec via validation
        assert input_cfg["srt"]["chunk_duration_sec"] == 5

    def test_default_output_section(self):
        """Output defaults should have web as default type."""
        output_cfg = DEFAULT_CONFIG["output"]
        assert output_cfg["type"] == "web"
        assert output_cfg["web"]["segment_duration"] == 5
        assert output_cfg["web"]["list_size"] == 12
        assert output_cfg["web"]["encoder_mode"] == "auto"

    def test_default_modules_section(self):
        """All expected modules should be present in defaults."""
        modules = DEFAULT_CONFIG["modules"]
        expected_modules = {
            "audio_extractor",
            "transcriber",
            "translator",
            "dmr_translator",
            "subtitle_generator",
            "tts_engine",
            "audio_mixer",
            "video_muxer",
        }
        assert set(modules.keys()) == expected_modules

    def test_default_module_enabled_states(self):
        """Default enabled states should match expected values."""
        modules = DEFAULT_CONFIG["modules"]
        # These should be enabled by default
        assert modules["audio_extractor"]["enabled"] is True
        assert modules["transcriber"]["enabled"] is True
        assert modules["translator"]["enabled"] is True
        assert modules["subtitle_generator"]["enabled"] is True
        assert modules["tts_engine"]["enabled"] is True
        assert modules["audio_mixer"]["enabled"] is True
        assert modules["video_muxer"]["enabled"] is True

    def test_default_transcriber_config(self):
        """Transcriber defaults should be sensible."""
        transcriber = DEFAULT_CONFIG["modules"]["transcriber"]
        assert transcriber["model"] == "tiny"
        assert transcriber["language"] == "auto"
        assert transcriber["device"] == "auto"
        assert transcriber["beam_size"] == 2

    def test_default_tts_config(self):
        """TTS defaults should be sensible."""
        tts = DEFAULT_CONFIG["modules"]["tts_engine"]
        assert tts["engine"] == "edge-tts"
        assert tts["device"] == "auto"
        assert tts["speed"] == 1.0

    def test_default_audio_mixer_config(self):
        """Audio mixer defaults should be sensible."""
        mixer = DEFAULT_CONFIG["modules"]["audio_mixer"]
        assert mixer["original_volume"] == 0.7
        assert mixer["tts_volume"] == 1.0

    def test_default_output_dir(self):
        """Output directory default should be ./output."""
        assert DEFAULT_CONFIG["output_dir"]["directory"] == "./output"


class TestConfigContract:
    """Contract tests ensuring config structure stability."""

    def test_config_manager_returns_valid_dict(self):
        """ConfigManager.to_dict() should return a valid config dict."""
        cm = ConfigManager(config_path="/nonexistent/path")
        config_dict = cm.to_dict()
        # Should be validatable by Pydantic
        SRT2WebConfig.from_dict(config_dict)

    def test_config_roundtrip_preserves_values(self):
        """Config should survive load -> to_dict -> from_dict roundtrip."""
        cm = ConfigManager(config_path="/nonexistent/path")
        original = cm.to_dict()
        validated = SRT2WebConfig.from_dict(original)
        result = validated.to_dict()

        # Key values should be preserved
        assert result["server"]["host"] == original["server"]["host"]
        assert result["server"]["port"] == original["server"]["port"]
        assert result["pipeline"]["mode"] == original["pipeline"]["mode"]

    def test_partial_update_preserves_other_values(self):
        """Updating one section should not affect others."""
        cm = ConfigManager(config_path="/nonexistent/path")
        original = cm.to_dict()
        cm.set("server.port", 8888)
        updated = cm.to_dict()

        assert updated["server"]["port"] == 8888
        assert updated["pipeline"]["mode"] == original["pipeline"]["mode"]
        assert updated["input"]["type"] == original["input"]["type"]
        assert updated["modules"]["transcriber"]["model"] == original["modules"]["transcriber"]["model"]

    def test_schema_defaults_match_manager_defaults(self):
        """Schema defaults should match ConfigManager defaults."""
        schema_defaults = SRT2WebConfig().to_dict()
        manager_defaults = DEFAULT_CONFIG

        # Compare top-level structure
        assert set(schema_defaults.keys()) == set(manager_defaults.keys())

        # Compare server section
        assert schema_defaults["server"]["host"] == manager_defaults["server"]["host"]
        assert schema_defaults["server"]["port"] == manager_defaults["server"]["port"]

        # Compare pipeline section
        assert schema_defaults["pipeline"]["mode"] == manager_defaults["pipeline"]["mode"]

    def test_no_none_values_in_defaults(self):
        """Default config should not have None values for required fields."""
        config = DEFAULT_CONFIG

        # Server
        assert config["server"]["host"] is not None
        assert config["server"]["port"] is not None

        # Pipeline
        assert config["pipeline"]["chunk_duration_sec"] is not None
        assert config["pipeline"]["mode"] is not None

        # Input
        assert config["input"]["type"] is not None

        # Output
        assert config["output"]["type"] is not None

    def test_all_enum_values_are_valid(self):
        """Enum values in defaults should be valid enum members."""
        config = DEFAULT_CONFIG

        # Pipeline mode
        valid_modes = {"sequential", "thread_parallel", "asyncio"}
        assert config["pipeline"]["mode"] in valid_modes

        # Input type
        valid_inputs = {"srt", "rtmp", "file", "audio"}
        assert config["input"]["type"] in valid_inputs

        # Output type
        valid_outputs = {"web", "hls", "srt", "rtmp", "file", "recording"}
        assert config["output"]["type"] in valid_outputs

        # TTS engine
        valid_engines = {"edge-tts", "piper", "elevenlabs"}
        assert config["modules"]["tts_engine"]["engine"] in valid_engines


class TestConfigValidationRanges:
    """Test that config values fall within expected ranges."""

    def test_port_in_valid_range(self):
        """Port should be between 1 and 65535."""
        config = DEFAULT_CONFIG
        assert 1 <= config["server"]["port"] <= 65535
        assert 1 <= config["input"]["srt"]["listen_port"] <= 65535

    def test_chunk_duration_reasonable(self):
        """Chunk duration should be between 1 and 60 seconds."""
        config = DEFAULT_CONFIG
        assert 1 <= config["pipeline"]["chunk_duration_sec"] <= 60
        assert 1 <= config["input"]["srt"]["chunk_duration_sec"] <= 60

    def test_buffer_sizes_positive(self):
        """Buffer sizes should be positive."""
        config = DEFAULT_CONFIG
        assert config["pipeline"]["buffer_size"] > 0
        assert config["pipeline"]["max_concurrent_chunks"] > 0
        assert config["output"]["web"]["list_size"] > 0

    def test_volumes_in_range(self):
        """Audio volumes should be between 0 and 2."""
        config = DEFAULT_CONFIG
        mixer = config["modules"]["audio_mixer"]
        assert 0 <= mixer["original_volume"] <= 2.0
        assert 0 <= mixer["tts_volume"] <= 2.0

    def test_retry_config_reasonable(self):
        """Retry config should be reasonable."""
        config = DEFAULT_CONFIG
        assert 0 <= config["pipeline"]["retry_attempts"] <= 10
        assert 0.1 <= config["pipeline"]["retry_delay"] <= 10.0

    def test_transcriber_beam_size_positive(self):
        """Beam size should be positive."""
        config = DEFAULT_CONFIG
        assert config["modules"]["transcriber"]["beam_size"] >= 1

    def test_tts_speed_reasonable(self):
        """TTS speed should be between 0.5 and 2.0."""
        config = DEFAULT_CONFIG
        assert 0.5 <= config["modules"]["tts_engine"]["speed"] <= 2.0
