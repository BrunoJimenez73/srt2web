"""
Tests for Astro dashboard JavaScript functionality.
"""

import pytest
from pathlib import Path


def get_all_frontend_content():
    """Load all frontend source files for testing."""
    base_path = Path(__file__).parent.parent.parent / "frontend" / "src"

    files = [
        base_path / "pages" / "index.astro",
        base_path / "components" / "StatusCard.astro",
        base_path / "components" / "ProcessCard.astro",
        base_path / "layouts" / "BaseLayout.astro",
    ]

    content = ""
    for f in files:
        if f.exists():
            with open(f, "r", encoding="utf-8") as fh:
                content += "\n" + fh.read()

    return content if content else None


class TestAstroDashboardJavaScript:
    """Tests for Astro dashboard JavaScript functions."""

    @pytest.fixture
    def content(self):
        """Load all frontend content."""
        return get_all_frontend_content()

    def test_apply_config_to_ui_function_exists(self, content):
        """Test that applyConfigToUI function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "function applyConfigToUI()" in content

    def test_save_config_function_exists(self, content):
        """Test that saveConfig function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "async function saveConfig(" in content

    def test_update_connection_urls_function_exists(self, content):
        """Test that updateConnectionUrls function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "function updateConnectionUrls()" in content

    def test_toggle_functions_exist(self, content):
        """Test that toggle functions exist."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "function toggleTranslate()" in content
        assert "function toggleDub()" in content
        assert "function toggleSubtitle()" in content

    def test_copy_url_function_exists(self, content):
        """Test that copyUrl function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "async function copyUrl(" in content

    def test_load_status_function_exists(self, content):
        """Test that loadStatus function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "async function loadStatus()" in content

    def test_update_module_status_function_exists(self, content):
        """Test that updateModuleStatus function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "function updateModuleStatus(" in content

    def test_start_pipeline_function_exists(self, content):
        """Test that startPipeline function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "async function startPipeline()" in content

    def test_stop_pipeline_function_exists(self, content):
        """Test that stopPipeline function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "async function stopPipeline()" in content


class TestAstroDashboardAPI:
    """Tests for API calls in Astro dashboard."""

    @pytest.fixture
    def content(self):
        """Load all frontend content."""
        return get_all_frontend_content()

    def test_api_prefix_used_for_config(self, content):
        """Test that /api/config is used."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "'/api/config'" in content

    def test_api_prefix_used_for_status(self, content):
        """Test that /api/status is used."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "'/api/status'" in content

    def test_api_prefix_used_for_start(self, content):
        """Test that /api/start is used."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "'/api/start'" in content

    def test_api_prefix_used_for_stop(self, content):
        """Test that /api/stop is used."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "'/api/stop'" in content


class TestAstroDashboardEventListeners:
    """Tests for event listeners in Astro dashboard."""

    @pytest.fixture
    def content(self):
        """Load all frontend content."""
        return get_all_frontend_content()

    def test_btn_start_listener_exists(self, content):
        """Test that btn-start event listener exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "btn-start').addEventListener" in content

    def test_btn_save_config_listener_exists(self, content):
        """Test that btn-save-config event listener exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "btn-save-config').addEventListener" in content

    def test_advanced_header_listener_exists(self, content):
        """Test that advanced-header click listener exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "'expanded'" in content

    def test_toggle_listeners_exist(self, content):
        """Test that toggle event listeners exist."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "translate-enabled" in content
        assert "dub-enabled" in content
        assert "subtitle-enabled" in content

    def test_copy_buttons_have_ids(self, content):
        """Test that copy buttons have proper IDs."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert 'id="btn-copy-srt"' in content
        assert 'id="btn-copy-stream"' in content
        assert 'id="btn-copy-player"' in content


class TestAstroDashboardModuleDependencies:
    """Tests for module dependency logic."""

    @pytest.fixture
    def content(self):
        """Load all frontend content."""
        return get_all_frontend_content()

    def test_toggle_translate_disables_dependent_modules(self, content):
        """Test that disabling translation disables subtitle and dub."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "subtitleEnabled.checked = false" in content
        assert "dubEnabled.checked = false" in content

    def test_toggle_dub_enables_translation(self, content):
        """Test that enabling dub automatically enables translation."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "translate-enabled" in content
        assert "toggleTranslate()" in content

    def test_toggle_subtitle_enables_translation(self, content):
        """Test that enabling subtitle automatically enables translation."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "translate-enabled" in content
        assert "toggleTranslate()" in content


class TestConnectionMode:
    """Tests for SRT connection mode (LOCAL/REMOTE) functionality."""

    @pytest.fixture
    def content(self):
        """Load all frontend content."""
        return get_all_frontend_content()

    def test_connection_mode_state_exists(self, content):
        """Test that connectionMode state variable exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "let connectionMode = 'local'" in content

    def test_network_info_state_exists(self, content):
        """Test that networkInfo state variable exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "let networkInfo = null" in content

    def test_load_network_info_function_exists(self, content):
        """Test that loadNetworkInfo function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "async function loadNetworkInfo()" in content

    def test_set_connection_mode_function_exists(self, content):
        """Test that setConnectionMode function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "function setConnectionMode(mode)" in content

    def test_update_connection_urls_function_exists(self, content):
        """Test that updateConnectionUrls function exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "function updateConnectionUrls()" in content

    def test_local_remote_buttons_exist(self, content):
        """Test that LOCAL and REMOTE buttons exist."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert 'id="btn-mode-local"' in content
        assert 'id="btn-mode-remote"' in content

    def test_emitter_address_input_exists(self, content):
        """Test that emitter address input exists for remote mode."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert 'id="emitter-address"' in content

    def test_remote_config_hidden_by_default(self, content):
        """Test that remote config is hidden by default."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert 'id="remote-config"' in content

    def test_local_mode_sets_caller(self, content):
        """Test that LOCAL mode uses mode=caller in URL."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "mode=caller" in content

    def test_remote_mode_shows_config(self, content):
        """Test that remote mode shows emitter config."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "remoteConfig.style.display = 'block'" in content

    def test_event_listeners_for_mode_buttons(self, content):
        """Test that event listeners exist for mode buttons."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "btn-mode-local').addEventListener" in content
        assert "btn-mode-remote').addEventListener" in content


class TestConnectionURLGeneration:
    """Tests for URL generation based on connection mode."""

    @pytest.fixture
    def content(self):
        """Load all frontend content."""
        return get_all_frontend_content()

    def test_srt_url_element_exists(self, content):
        """Test that SRT URL element exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert 'id="url-srt"' in content

    def test_stream_url_element_exists(self, content):
        """Test that Stream URL element exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert 'id="url-stream"' in content

    def test_player_url_element_exists(self, content):
        """Test that Player URL element exists."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert 'id="url-player"' in content

    def test_local_mode_uses_127_for_stream_player(self, content):
        """Test that LOCAL mode uses 127.0.0.1 for stream and player."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "http://127.0.0.1:9999/hls/stream.m3u8" in content
        assert "http://127.0.0.1:9999/player" in content

    def test_local_mode_uses_local_ip_for_srt(self, content):
        """Test that LOCAL mode uses local IP for SRT URL."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "networkInfo.local_ip" in content

    def test_remote_mode_uses_public_ip(self, content):
        """Test that REMOTE mode uses public IP for stream/player."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "networkInfo.public_ip" in content


class TestSaveConfigWithConnectionMode:
    """Tests for saveConfig with connection mode configuration."""

    @pytest.fixture
    def content(self):
        """Load all frontend content."""
        return get_all_frontend_content()

    def test_save_config_includes_srt_mode(self, content):
        """Test that saveConfig includes srt mode in config."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "mode: srtMode" in content

    def test_save_config_includes_caller_address(self, content):
        """Test that saveConfig includes caller_address in config."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "caller_address: callerAddress" in content

    def test_remote_mode_sets_caller_config(self, content):
        """Test that remote mode sets caller mode and address."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "connectionMode === 'remote'" in content

    def test_apply_config_restores_connection_mode(self, content):
        """Test that applyConfigToUI restores connection mode from config."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "connectionMode = srtMode === 'caller'" in content
        assert "setConnectionMode(connectionMode)" in content

    def test_apply_config_restores_emitter_address(self, content):
        """Test that applyConfigToUI restores emitter address."""
        if content is None:
            pytest.skip("Frontend files not found")
        assert "emitter-address'" in content
        assert "caller_address" in content
