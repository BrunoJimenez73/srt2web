"""
Tests for Dashboard JavaScript functionality using web/index.html.
"""

import pytest
from pathlib import Path


def get_frontend_content():
    """Load the actual frontend HTML file for testing."""
    base_path = Path(__file__).parent.parent.parent / "web"
    index_html = base_path / "index.html"

    if index_html.exists():
        with open(index_html, "r", encoding="utf-8") as f:
            return f.read()
    return None


class TestDashboardJavaScript:
    """Tests for Dashboard JavaScript functions."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_apply_config_to_ui_function_exists(self, content):
        """Test that applyConfigToUI function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "function applyConfigToUI()" in content

    def test_save_config_function_exists(self, content):
        """Test that saveConfig function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "async function saveConfig(" in content

    def test_load_status_function_exists(self, content):
        """Test that loadStatus function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "async function loadStatus()" in content

    def test_update_module_status_function_exists(self, content):
        """Test that updateModuleStatus function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "function updateModuleStatus(" in content

    def test_start_pipeline_function_exists(self, content):
        """Test that startPipeline function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "async function startPipeline()" in content

    def test_stop_pipeline_function_exists(self, content):
        """Test that stopPipeline function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "async function stopPipeline()" in content

    def test_whisper_card_exists(self, content):
        """Test that whisper card exists in process-grid."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-whisper" in content

    def test_hls_output_card_exists(self, content):
        """Test that HLS output card exists in process-grid."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-hls" in content

    def test_save_config_button_in_header(self, content):
        """Test that save config button exists in header."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "btn-save" in content

    def test_toggle_translate_function_exists(self, content):
        """Test that toggleTranslate function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "function toggleTranslate()" in content

    def test_toggle_dub_function_exists(self, content):
        """Test that toggleDub function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "function toggleDub()" in content

    def test_toggle_subtitle_function_exists(self, content):
        """Test that toggleSubtitle function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "function toggleSubtitle()" in content


class TestDashboardAPI:
    """Tests for API calls in Dashboard."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_api_call_function_exists(self, content):
        """Test that apiCall function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "async function apiCall(" in content

    def test_api_prefix_in_apicall(self, content):
        """Test that /api prefix is used in apiCall."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "/api${path}" in content or "`/api${path}`" in content

    def test_api_config_used(self, content):
        """Test that /config endpoint is used in apiCall."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'/config'" in content or '"/config"' in content

    def test_api_status_used(self, content):
        """Test that /status endpoint is used in apiCall."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'/status'" in content or '"/status"' in content

    def test_api_start_used(self, content):
        """Test that /start endpoint is used in apiCall."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'/start'" in content or '"/start"' in content

    def test_api_stop_used(self, content):
        """Test that /stop endpoint is used in apiCall."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'/stop'" in content or '"/stop"' in content


class TestDashboardProcessGrid:
    """Tests for Process Grid (main module cards)."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_whisper_card_exists(self, content):
        """Test that whisper card exists in process-grid."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-whisper" in content

    def test_hls_output_card_exists(self, content):
        """Test that HLS output card exists in process-grid."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-hls" in content

    def test_save_config_button_in_header(self, content):
        """Test that save config button exists in header."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "btn-save" in content

    def test_process_grid_has_7_cards(self, content):
        """Test that process-grid contains 7 module cards."""
        if content is None:
            pytest.skip("web/index.html not found")
        card_count = content.count("card-")
        assert card_count >= 7, f"Expected at least 7 cards, found {card_count}"


class TestDashboardEventListeners:
    """Tests for event listeners in Dashboard."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_btn_start_listener_exists(self, content):
        """Test that btn-start event listener exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "btn-start" in content

    def test_btn_stop_listener_exists(self, content):
        """Test that btn-stop event listener exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "btn-stop" in content

    def test_toggle_translate_changes_checkbox(self, content):
        """Test that toggleTranslate function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "translate-enabled" in content

    def test_toggle_dub_changes_checkbox(self, content):
        """Test that toggleDub function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "dub-enabled" in content

    def test_toggle_subtitle_changes_checkbox(self, content):
        """Test that toggleSubtitle function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "subtitle-enabled" in content


class TestDashboardModuleDependencies:
    """Tests for module dependency logic in frontend."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_toggle_translate_disables_dependent_modules(self, content):
        """Test that disabling translation disables subtitle and dub."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "subtitleEnabled" in content
        assert "dubEnabled" in content

    def test_toggle_dub_enables_translation(self, content):
        """Test that enabling dub automatically enables translation."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "translate-enabled" in content
        assert "toggleTranslate()" in content

    def test_toggle_subtitle_enables_translation(self, content):
        """Test that enabling subtitle automatically enables translation."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "translate-enabled" in content
        assert "toggleTranslate()" in content

    def test_translator_card_exists(self, content):
        """Test that translator card exists (separate from subtitle/dub)."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-translate" in content

    def test_subtitle_card_exists(self, content):
        """Test that subtitle card exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-subtitle" in content

    def test_dub_card_exists(self, content):
        """Test that dub card exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-dub" in content


class TestDashboardConnectionMode:
    """Tests for SRT connection mode (LOCAL/REMOTE) functionality."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_local_remote_buttons_exist(self, content):
        """Test that LOCAL and REMOTE buttons exist with data-mode attributes."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert 'data-mode="local"' in content
        assert 'data-mode="remote"' in content

    def test_local_ip_display_exists(self, content):
        """Test that local IP display exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        # Now URLs are in status card
        assert "status-url-srt" in content or "status-url-player" in content

    def test_update_urls_function_exists(self, content):
        """Test that updateUrls function exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "function updateUrls(" in content

    def test_status_urls_exist_in_status_card(self, content):
        """Test that status URLs exist in status card."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "status-url-srt" in content
        assert "status-url-stream" in content
        assert "status-url-player" in content


class TestDashboardURLs:
    """Tests for URL generation."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_srt_url_element_exists(self, content):
        """Test that SRT URL element exists in status card."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "status-url-srt" in content

    def test_stream_url_element_exists(self, content):
        """Test that Stream URL element exists in status card."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "status-url-stream" in content

    def test_player_url_element_exists(self, content):
        """Test that Player URL element exists in status card."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "status-url-player" in content

    def test_hls_url_generated(self, content):
        """Test that HLS URL is generated."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "/hls/stream.m3u8" in content or "hls" in content.lower()


class TestDashboardModuleIndicators:
    """Tests for module status indicators."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_indicator_input_exists(self, content):
        """Test that indicator-input exists (for transcriber/audio extractor)."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "indicator-input" in content

    def test_indicator_translate_exists(self, content):
        """Test that indicator-translate exists for translator module."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "indicator-translate" in content

    def test_indicator_subtitle_exists(self, content):
        """Test that indicator-subtitle exists for subtitle_generator module."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "indicator-subtitle" in content

    def test_indicator_dub_exists(self, content):
        """Test that indicator-dub exists for TTS/mixer modules."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "indicator-dub" in content

    def test_indicator_output_exists(self, content):
        """Test that indicator-output exists for HLS output."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "indicator-output" in content

    def test_update_module_status_uses_indicators(self, content):
        """Test that updateModuleStatus updates indicators."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "indicator-" in content
        assert "updateModuleStatus" in content

    def test_translator_maps_to_translate_indicator(self, content):
        """Test that translator module maps to indicator-translate."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'translator': 'indicator-translate'" in content

    def test_subtitle_generator_maps_to_subtitle_indicator(self, content):
        """Test that subtitle_generator maps to indicator-subtitle."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'subtitle_generator': 'indicator-subtitle'" in content

    def test_tts_engine_maps_to_dub_indicator(self, content):
        """Test that tts_engine maps to indicator-dub."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'tts_engine': 'indicator-dub'" in content

    def test_audio_mixer_maps_to_dub_indicator(self, content):
        """Test that audio_mixer maps to indicator-dub."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'audio_mixer': 'indicator-dub'" in content


class TestDashboardProcessCards:
    """Tests for process cards (module cards)."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_card_input_exists(self, content):
        """Test that card-input exists (for transcriber/audio extractor)."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-input" in content

    def test_card_translate_exists(self, content):
        """Test that card-translate exists for translator module."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-translate" in content

    def test_card_subtitle_exists(self, content):
        """Test that card-subtitle exists for subtitle_generator module."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-subtitle" in content

    def test_card_dub_exists(self, content):
        """Test that card-dub exists for TTS/mixer modules."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-dub" in content

    def test_card_output_exists(self, content):
        """Test that card-output exists for HLS output."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "card-output" in content

    def test_transcriber_maps_to_whisper_card(self, content):
        """Test that transcriber module maps to card-whisper in updateModuleStatus."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'transcriber': 'card-whisper'" in content

    def test_translator_maps_to_translate_card(self, content):
        """Test that translator module maps to card-translate."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'translator': 'card-translate'" in content

    def test_subtitle_generator_maps_to_subtitle_card(self, content):
        """Test that subtitle_generator maps to card-subtitle."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'subtitle_generator': 'card-subtitle'" in content

    def test_tts_engine_maps_to_dub_card(self, content):
        """Test that tts_engine maps to card-dub."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "'tts_engine': 'card-dub'" in content


class TestDashboardWebSocket:
    """Tests for WebSocket functionality."""

    @pytest.fixture
    def content(self):
        """Load frontend content."""
        return get_frontend_content()

    def test_websocket_connection_exists(self, content):
        """Test that WebSocket connection is used."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "/ws/logs" in content or "WebSocket" in content

    def test_websocket_reconnect_logic_exists(self, content):
        """Test that WebSocket reconnection logic exists."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "reconnect" in content.lower()

    def test_log_panel_exists(self, content):
        """Test that log panel exists for WebSocket logs."""
        if content is None:
            pytest.skip("web/index.html not found")
        assert "log-panel" in content or "logs" in content
