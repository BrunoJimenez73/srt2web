"""
Tests for server startup and basic functionality.

These tests verify that the server can start without errors
and that basic functionality works correctly.
"""

import os
import sys
import pytest
import threading
import time
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestServerStartup:
    """Test that the server can start without errors."""

    def test_config_loads_successfully(self):
        """Test that config.yaml loads without errors."""
        from core.config_manager import ConfigManager
        
        config_path = str(PROJECT_ROOT / "config.yaml")
        config = ConfigManager(config_path)
        assert config is not None
        # The config loads with fallback to DEFAULT_CONFIG for some values
        # Check that the config file was loaded
        assert config._config_path == config_path

    def test_pipeline_builds_successfully(self):
        """Test that pipeline builds without errors."""
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from core.io_factory import InputFactory, OutputFactory, auto_discover
        
        # Auto-discover inputs/outputs
        auto_discover()
        
        # Load config
        config = ConfigManager(str(PROJECT_ROOT / "config.yaml"))
        
        # Create input source
        input_config = config.get_section("input")
        input_type = input_config.get("type", "srt")
        type_config = input_config.get(input_type, {})
        type_config["chunk_duration_sec"] = 15
        
        input_source = InputFactory.create(input_type, type_config)
        
        # Create output sink
        output_config = config.get_section("output")
        output_type = output_config.get("type", "web")
        type_config = output_config.get(output_type, {})
        
        output_sink = OutputFactory.create(output_type, type_config)
        
        # Create pipeline
        pipeline = Pipeline(input_source, output_sink)
        assert pipeline is not None
        
        # Verify modules can be registered
        assert len(pipeline.get_modules()) == 0

    def test_fastapi_app_creates(self):
        """Test that FastAPI app creates without errors."""
        from server.app import create_app
        from core.config_manager import ConfigManager
        
        config = ConfigManager(str(PROJECT_ROOT / "config.yaml"))
        app = create_app(config)
        
        assert app is not None

    def test_pipeline_modules_register(self):
        """Test that all pipeline modules register correctly."""
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from core.io_factory import InputFactory, OutputFactory, auto_discover
        from modules.audio_extractor import AudioExtractor
        from modules.subtitle_generator import SubtitleGenerator
        from modules.audio_mixer import AudioMixer
        
        auto_discover()
        config_path = str(PROJECT_ROOT / "config.yaml")
        config = ConfigManager(config_path)
        
        # Create input/output
        input_config = config.get_section("input")
        input_type = input_config.get("type", "srt")
        input_source = InputFactory.create(input_type, input_config.get(input_type, {}))
        
        output_config = config.get_section("output")
        output_type = output_config.get("type", "web")
        output_sink = OutputFactory.create(output_type, output_config.get(output_type, {}))
        
        pipeline = Pipeline(input_source, output_sink)
        
        # Register modules
        audio_extractor = AudioExtractor(config={"enabled": True})
        pipeline.register_module(audio_extractor)
        
        subtitle_generator = SubtitleGenerator(config={"enabled": True})
        pipeline.register_module(subtitle_generator)
        
        audio_mixer = AudioMixer(config={"enabled": True})
        pipeline.register_module(audio_mixer)
        
        # Verify modules registered
        modules = pipeline.get_modules()
        assert len(modules) == 3
        assert modules[0].name == "audio_extractor"
        assert modules[1].name == "subtitle_generator"
        assert modules[2].name == "audio_mixer"

    def test_io_wrappers_import(self):
        """Test that I/O wrappers can be imported."""
        from modules.io_wrappers import InputModuleWrapper, OutputModuleWrapper
        from core.input_source import InputSource
        from core.output_sink import OutputSink
        
        assert InputModuleWrapper is not None
        assert OutputModuleWrapper is not None

    def test_io_module_base_import(self):
        """Test that IOBaseModule can be imported."""
        from core.io_module_base import IOBaseModule, InputModule, OutputModule, IOModuleType
        
        assert IOBaseModule is not None
        assert InputModule is not None
        assert OutputModule is not None
        assert IOModuleType.INPUT == "input"
        assert IOModuleType.OUTPUT == "output"


class TestConfigStructure:
    """Test config.yaml structure and values."""

    def test_config_has_valid_structure(self):
        """Test that config.yaml has all required sections."""
        import yaml
        
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # Check root sections
        assert "server" in config
        assert "input" in config
        assert "output" in config
        assert "modules" in config
        
        # Check server section
        assert "port" in config["server"]
        assert config["server"]["port"] == 9999
        
        # Check input section
        assert "type" in config["input"]
        assert config["input"]["type"] == "srt"
        
        # Check output section
        assert "type" in config["output"]
        
        # Check modules section
        assert "transcriber" in config["modules"]
        assert "tts_engine" in config["modules"]

    def test_transcriber_model_valid(self):
        """Test that transcriber has a valid model."""
        from core.config_manager import ConfigManager
        
        config = ConfigManager(str(PROJECT_ROOT / "config.yaml"))
        model = config.get("modules.transcriber.model")
        
        valid_models = ["tiny", "small", "medium", "large", "large-v2", "large-v3"]
        assert model in valid_models, f"Invalid model: {model}"

    def test_encoder_mode_valid(self):
        """Test that video muxer has valid encoder mode."""
        from core.constants import VALID_ENCODER_MODES
        
        # Test that constants include all modes
        assert "auto" in VALID_ENCODER_MODES
        assert "cpu" in VALID_ENCODER_MODES
        assert "gpu_nvenc" in VALID_ENCODER_MODES


class TestModuleToggle:
    """Test module enable/disable functionality."""

    def test_module_enable_disable(self):
        """Test that modules can be enabled/disabled."""
        from modules.audio_extractor import AudioExtractor
        
        # Create module with enabled=True
        module = AudioExtractor(config={"enabled": True}, output_dir="./output")
        assert module.enabled is True
        assert module.state.value == "idle"
        
        # Disable module
        module.configure({"enabled": False})
        assert module.enabled is False

    def test_io_module_wrapper_enable_disable(self):
        """Test that I/O wrappers respect enable/disable."""
        from modules.io_wrappers import InputModuleWrapper
        from modules.inputs.srt_input import SRTInput
        
        # Create input source
        input_source = SRTInput({"listen_port": 9000})
        
        # Create wrapper with enabled=True
        wrapper = InputModuleWrapper("test_input", input_source, {"enabled": True})
        assert wrapper.enabled is True
        
        # Disable wrapper
        wrapper.configure({"enabled": False})
        assert wrapper.enabled is False
