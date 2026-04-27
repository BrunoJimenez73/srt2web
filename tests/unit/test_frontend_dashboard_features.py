"""
Tests for frontend dashboard features (April 2026).

Tests for:
- Config persistence in config.yaml
- Piper TTS voices availability
- Module status indicators (lucecitas verdes)
- GPU badge display logic
- Device/Encoder metrics display
- Output multi-output management
"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestConfigPersistence:
    """Test that config values persist correctly."""

    def test_config_yaml_exists(self) -> None:
        """Test that config.yaml exists and is valid."""
        config_path = PROJECT_ROOT / "config.yaml"
        assert config_path.exists(), "config.yaml should exist"
        
        content = config_path.read_text(encoding="utf-8")
        config = yaml.safe_load(content)
        assert config is not None

    def test_config_has_required_sections(self) -> None:
        """Test that config.yaml has all required sections."""
        config_path = PROJECT_ROOT / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        
        required_sections = ["pipeline", "modules", "input", "output"]
        for section in required_sections:
            assert section in config, f"Config should have '{section}' section"

    def test_config_piper_voice_persists(self) -> None:
        """Test that Piper TTS voice is configured in config.yaml."""
        config_path = PROJECT_ROOT / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        
        tts_config = config.get("modules", {}).get("tts_engine", {})
        assert "voice" in tts_config, "TTS config should have 'voice' setting"
        
    def test_config_chunk_duration_persists(self) -> None:
        """Test that chunk_duration_sec is configured."""
        config_path = PROJECT_ROOT / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        
        chunk_duration = config.get("pipeline", {}).get("chunk_duration_sec")
        assert chunk_duration is not None, "chunk_duration_sec should be configured"
        assert isinstance(chunk_duration, (int, float)), "chunk_duration should be numeric"

    def test_config_hls_settings_persists(self) -> None:
        """Test that HLS output settings are configured."""
        config_path = PROJECT_ROOT / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        
        output_config = config.get("output", {}).get("web", {})
        assert "segment_duration" in output_config
        assert "list_size" in output_config


class TestPiperVoices:
    """Test that Piper TTS voices are available."""

    def test_piper_models_directory_exists(self) -> None:
        """Test that Piper models directory exists."""
        models_dir = PROJECT_ROOT / "models" / "piper"
        assert models_dir.exists(), "Piper models directory should exist"

    def test_piper_voices_exist(self) -> None:
        """Test that at least one Piper voice model exists."""
        models_dir = PROJECT_ROOT / "models" / "piper"
        if not models_dir.exists():
            pytest.skip("Piper models directory does not exist")
            
        # Check for .onnx or .json files (Piper voice models)
        voice_files = list(models_dir.glob("*.onnx")) + list(models_dir.glob("*.json"))
        assert len(voice_files) > 0, "At least one Piper voice model should exist"

    def test_piper_voices_in_tts_config(self) -> None:
        """Test that config.yaml has Piper voices listed."""
        config_path = PROJECT_ROOT / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        
        # Config should have TTS voice configured
        tts_config = config.get("modules", {}).get("tts_engine", {})
        voice = tts_config.get("voice", "")
        
        # Voice should contain language code (e.g., en_US, es_ES)
        assert voice, "TTS voice should be configured"


class TestModuleStatusIndicators:
    """Test that module status indicators are properly mapped."""

    def test_moduleMap_in_index_astro(self) -> None:
        """Test that moduleMap exists in index.astro."""
        index_path = PROJECT_ROOT / "frontend" / "src" / "pages" / "index.astro"
        assert index_path.exists(), "index.astro should exist"
        
        content = index_path.read_text(encoding="utf-8")
        assert "moduleMap" in content, "moduleMap should be defined"

    def test_all_modules_in_moduleMap(self) -> None:
        """Test that all modules are mapped in moduleMap."""
        index_path = PROJECT_ROOT / "frontend" / "src" / "pages" / "index.astro"
        content = index_path.read_text(encoding="utf-8")
        
        required_modules = [
            "audio_extractor", "transcriber", "translator", "tts_engine",
            "subtitle_generator", "audio_mixer", "video_muxer", "output"
        ]
        
        for module in required_modules:
            assert f"'{module}':" in content, f"Module '{module}' should be in moduleMap"

    def test_indicator_ids_exist_in_components(self) -> None:
        """Test that indicator IDs are defined in component cards."""
        components = {
            "InputCard.astro": "indicator-input",
            "WhisperCard.astro": "indicator-whisper", 
            "HlsCard.astro": "indicator-video-muxer",
            "OutputCard.astro": "indicator-output",
        }
        
        for component, indicator_id in components.items():
            component_path = PROJECT_ROOT / "frontend" / "src" / "components" / component
            if component_path.exists():
                content = component_path.read_text(encoding="utf-8")
                assert indicator_id in content, f"{component} should have {indicator_id}"


class TestGPUBadgeDisplay:
    """Test that GPU badges display correctly."""

    def test_gpu_badge_elements_exist(self) -> None:
        """Test that GPU badge elements exist in component cards."""
        badge_ids = [
            ("InputCard.astro", "input-gpu-badge"),
            ("WhisperCard.astro", "whisper-gpu-badge"),
            ("TtsCard.astro", "tts-gpu-badge"),
            ("HlsCard.astro", "hls-gpu-badge"),
            ("OutputCard.astro", "output-gpu-badge"),
        ]
        
        for component, badge_id in badge_ids:
            component_path = PROJECT_ROOT / "frontend" / "src" / "components" / component
            if component_path.exists():
                content = component_path.read_text(encoding="utf-8")
                assert badge_id in content, f"{component} should have {badge_id}"

    def test_gpu_badge_css_exists(self) -> None:
        """Test that GPU badge CSS is defined."""
        components_with_badge = [
            "InputCard.astro",
            "WhisperCard.astro", 
            "TtsCard.astro",
            "HlsCard.astro",
            "OutputCard.astro",
        ]
        
        for component in components_with_badge:
            component_path = PROJECT_ROOT / "frontend" / "src" / "components" / component
            if component_path.exists():
                content = component_path.read_text(encoding="utf-8")
                assert ".gpu-badge" in content, f"{component} should have .gpu-badge CSS"
                assert ".gpu-badge.active" in content, f"{component} should have .gpu-badge.active CSS"

    def test_gpu_badge_logic_in_index_astro(self) -> None:
        """Test that GPU badge display logic exists in index.astro."""
        index_path = PROJECT_ROOT / "frontend" / "src" / "pages" / "index.astro"
        content = index_path.read_text(encoding="utf-8")
        
        # Check for badge logic
        assert "info.badge" in content, "Badge logic should reference info.badge"
        assert "using_gpu" in content, "Badge logic should check using_gpu"
        assert "classList.add('active')" in content, "Badge should add 'active' class when GPU is active"


class TestDeviceEncoderMetrics:
    """Test that device/encoder metrics display correctly."""

    def test_device_metric_elements_exist(self) -> None:
        """Test that device metric elements exist in cards."""
        # Whisper has Device metric
        whisper_path = PROJECT_ROOT / "frontend" / "src" / "components" / "WhisperCard.astro"
        if whisper_path.exists():
            content = whisper_path.read_text(encoding="utf-8")
            assert "module-device-transcriber" in content, "WhisperCard should have device metric"

    def test_encoder_metric_elements_exist(self) -> None:
        """Test that encoder metric elements exist in cards."""
        # HLS has Encoder metric
        hls_path = PROJECT_ROOT / "frontend" / "src" / "components" / "HlsCard.astro"
        if hls_path.exists():
            content = hls_path.read_text(encoding="utf-8")
            assert "module-encoder-video_muxer" in content, "HlsCard should have encoder metric"

    def test_device_encoder_logic_in_index_astro(self) -> None:
        """Test that device/encoder display logic exists."""
        index_path = PROJECT_ROOT / "frontend" / "src" / "pages" / "index.astro"
        content = index_path.read_text(encoding="utf-8")
        
        assert "module-device-" in content, "Should have device element lookup"
        assert "module-encoder-" in content, "Should have encoder element lookup"
        assert "modStatus.extra.device" in content, "Should read device from extra"
        assert "modStatus.extra.encoder_mode" in content, "Should read encoder_mode from extra"


class TestBackendStatusAPI:
    """Test that backend status API returns correct data."""

    def test_pipeline_status_has_modules(self) -> None:
        """Test that unified pipeline returns module status."""
        # Check that unified_pipeline.py has get_status method
        pipeline_path = PROJECT_ROOT / "core" / "unified_pipeline.py"
        assert pipeline_path.exists()
        
        content = pipeline_path.read_text(encoding="utf-8")
        assert "def get_status" in content, "Pipeline should have get_status method"

    def test_pipeline_status_returns_extra(self) -> None:
        """Test that pipeline status includes 'extra' field with device/encoder info."""
        pipeline_path = PROJECT_ROOT / "core" / "unified_pipeline.py"
        content = pipeline_path.read_text(encoding="utf-8")
        
        # The _get_output_module_status should return 'extra' with encoder_mode
        assert '"extra":' in content or "'extra':" in content, "Status should include 'extra' field"

    def test_transcriber_returns_device_in_status(self) -> None:
        """Test that transcriber returns device in status."""
        transcriber_path = PROJECT_ROOT / "modules" / "transcriber.py"
        if transcriber_path.exists():
            content = transcriber_path.read_text(encoding="utf-8")
            assert 'status.extra["device"]' in content, "Transcriber should set device in extra"

    def test_tts_engine_returns_device_in_status(self) -> None:
        """Test that TTS engine returns device in status."""
        tts_path = PROJECT_ROOT / "modules" / "tts_engine.py"
        if tts_path.exists():
            content = tts_path.read_text(encoding="utf-8")
            assert 'status.extra["device"]' in content, "TTS should set device in extra"

    def test_hls_output_returns_encoder_in_status(self) -> None:
        """Test that HLS output returns encoder_mode in status."""
        hls_path = PROJECT_ROOT / "modules" / "outputs" / "hls_output.py"
        if hls_path.exists():
            content = hls_path.read_text(encoding="utf-8")
            assert '"encoder_mode"' in content, "HLS output should include encoder_mode in status"


class TestOutputMultiOutput:
    """Test that OUTPUT module supports multiple outputs."""

    def test_output_card_has_add_button(self) -> None:
        """Test that OutputCard has '+ Añadir salida' button."""
        output_card_path = PROJECT_ROOT / "frontend" / "src" / "components" / "OutputCard.astro"
        assert output_card_path.exists()
        
        content = output_card_path.read_text(encoding="utf-8")
        assert "Añadir salida" in content, "OutputCard should have add button"

    def test_output_card_has_delete_button(self) -> None:
        """Test that OutputCard has delete buttons for outputs."""
        output_card_path = PROJECT_ROOT / "frontend" / "src" / "components" / "OutputCard.astro"
        content = output_card_path.read_text(encoding="utf-8")
        
        assert "Eliminar" in content or "delete" in content.lower(), "OutputCard should have delete button"

    def test_api_routes_has_outputs_endpoint(self) -> None:
        """Test that API has /api/outputs endpoint."""
        api_path = PROJECT_ROOT / "server" / "api_routes.py"
        if api_path.exists():
            content = api_path.read_text(encoding="utf-8")
            assert "/outputs" in content, "API should have /outputs endpoint"

    def test_api_routes_has_add_output_endpoint(self) -> None:
        """Test that API has POST /api/outputs endpoint."""
        api_path = PROJECT_ROOT / "server" / "api_routes.py"
        if api_path.exists():
            content = api_path.read_text(encoding="utf-8")
            # Should have method to add output
            assert "def add_output" in content or "@app.post" in content, "API should have add output method"


class TestMetricsDisplay:
    """Test that metrics display correctly in dashboard."""

    def test_time_metric_elements_exist(self) -> None:
        """Test that time metric elements exist for all modules."""
        index_path = PROJECT_ROOT / "frontend" / "src" / "pages" / "index.astro"
        content = index_path.read_text(encoding="utf-8")
        
        # Should have time element lookups
        assert "module-time-" in content, "Should have time metric elements"

    def test_chunks_metric_elements_exist(self) -> None:
        """Test that chunks metric elements exist for all modules."""
        index_path = PROJECT_ROOT / "frontend" / "src" / "pages" / "index.astro"
        content = index_path.read_text(encoding="utf-8")
        
        # Should have chunks element lookups
        assert "module-chunks-" in content, "Should have chunks metric elements"

    def test_metrics_display_logic(self) -> None:
        """Test that metrics display logic updates element textContent."""
        index_path = PROJECT_ROOT / "frontend" / "src" / "pages" / "index.astro"
        content = index_path.read_text(encoding="utf-8")
        
        # Should update textContent with processed_chunks
        assert "textContent = String(modStatus.processed_chunks)" in content
        # Should format time in ms or seconds
        assert "last_process_time_ms" in content


class TestRefreshModuleStatus:
    """Test that module status refresh works."""

    def test_status_poll_interval_exists(self) -> None:
        """Test that status polling is set up."""
        index_path = PROJECT_ROOT / "frontend" / "src" / "pages" / "index.astro"
        content = index_path.read_text(encoding="utf-8")
        
        # Should have setInterval for status updates
        assert "setInterval" in content, "Should have setInterval for status polling"
        assert "refreshModuleStatus" in content or "updateStatus" in content, "Should have status update function"

    def test_status_fetch_to_api(self) -> None:
        """Test that status is fetched from API."""
        index_path = PROJECT_ROOT / "frontend" / "src" / "pages" / "index.astro"
        content = index_path.read_text(encoding="utf-8")
        
        # Should fetch from /api/status (returns state + modules)
        assert "/api/status" in content, "Should fetch status from /api/status"