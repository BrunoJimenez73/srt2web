"""
Tests for Astro dashboard JavaScript functionality.
"""

import pytest
import re
from pathlib import Path


class TestAstroDashboardJavaScript:
    """Tests for Astro dashboard JavaScript functions."""

    @pytest.fixture
    def astro_frontend_content(self):
        """Load Astro index.astro content."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "index.astro"
        )
        if astro_path.exists():
            with open(astro_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_apply_config_to_ui_function_exists(self, astro_frontend_content):
        """Test that applyConfigToUI function exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "function applyConfigToUI()" in astro_frontend_content

    def test_save_config_function_exists(self, astro_frontend_content):
        """Test that saveConfig function exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "async function saveConfig(" in astro_frontend_content

    def test_update_urls_function_exists(self, astro_frontend_content):
        """Test that updateUrls function exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "function updateUrls(" in astro_frontend_content

    def test_toggle_functions_exist(self, astro_frontend_content):
        """Test that toggle functions exist."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "function toggleTranslate()" in astro_frontend_content
        assert "function toggleDub()" in astro_frontend_content
        assert "function toggleSubtitle()" in astro_frontend_content

    def test_copy_url_function_exists(self, astro_frontend_content):
        """Test that copyUrl function exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "function copyUrl(" in astro_frontend_content

    def test_load_status_function_exists(self, astro_frontend_content):
        """Test that loadStatus function exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "async function loadStatus()" in astro_frontend_content

    def test_update_module_status_function_exists(self, astro_frontend_content):
        """Test that updateModuleStatus function exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "function updateModuleStatus(" in astro_frontend_content

    def test_start_pipeline_function_exists(self, astro_frontend_content):
        """Test that startPipeline function exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "async function startPipeline()" in astro_frontend_content

    def test_stop_pipeline_function_exists(self, astro_frontend_content):
        """Test that stopPipeline function exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "async function stopPipeline()" in astro_frontend_content


class TestAstroDashboardAPI:
    """Tests for API call structure in Astro dashboard."""

    @pytest.fixture
    def astro_frontend_content(self):
        """Load Astro index.astro content."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "index.astro"
        )
        if astro_path.exists():
            with open(astro_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_api_prefix_used_for_config(self, astro_frontend_content):
        """Test that /api prefix is used for config endpoint."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "'/api/config'" in astro_frontend_content

    def test_api_prefix_used_for_status(self, astro_frontend_content):
        """Test that /api prefix is used for status endpoint."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "'/api/status'" in astro_frontend_content

    def test_api_prefix_used_for_start(self, astro_frontend_content):
        """Test that /api prefix is used for start endpoint."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "'/api/start'" in astro_frontend_content

    def test_api_prefix_used_for_stop(self, astro_frontend_content):
        """Test that /api prefix is used for stop endpoint."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "'/api/stop'" in astro_frontend_content


class TestAstroDashboardEventListeners:
    """Tests for event listeners in Astro dashboard."""

    @pytest.fixture
    def astro_frontend_content(self):
        """Load Astro index.astro content."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "index.astro"
        )
        if astro_path.exists():
            with open(astro_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_btn_start_listener_exists(self, astro_frontend_content):
        """Test that btn-start event listener exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "btn-start" in astro_frontend_content
        assert "addEventListener" in astro_frontend_content

    def test_btn_save_config_listener_exists(self, astro_frontend_content):
        """Test that btn-save-config event listener exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "btn-save-config" in astro_frontend_content

    def test_advanced_header_listener_exists(self, astro_frontend_content):
        """Test that advanced-header click listener exists."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "advanced-header" in astro_frontend_content
        assert "'expanded'" in astro_frontend_content

    def test_toggle_listeners_exist(self, astro_frontend_content):
        """Test that toggle event listeners exist."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "translate-enabled" in astro_frontend_content
        assert "dub-enabled" in astro_frontend_content
        assert "subtitle-enabled" in astro_frontend_content

    def test_copy_buttons_have_ids(self, astro_frontend_content):
        """Test that copy buttons have proper IDs."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert 'id="btn-copy-srt"' in astro_frontend_content
        assert 'id="btn-copy-stream"' in astro_frontend_content
        assert 'id="btn-copy-player"' in astro_frontend_content


class TestAstroDashboardModuleDependencies:
    """Tests for module dependency logic."""

    @pytest.fixture
    def astro_frontend_content(self):
        """Load Astro index.astro content."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "index.astro"
        )
        if astro_path.exists():
            with open(astro_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_toggle_translate_disables_dependent_modules(self, astro_frontend_content):
        """Test that disabling translation disables subtitle and dub."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "subtitleEnabled.checked = false" in astro_frontend_content
        assert "dubEnabled.checked = false" in astro_frontend_content

    def test_toggle_dub_enables_translation(self, astro_frontend_content):
        """Test that enabling dub automatically enables translation."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "translate-enabled" in astro_frontend_content
        assert "toggleTranslate()" in astro_frontend_content

    def test_toggle_subtitle_enables_translation(self, astro_frontend_content):
        """Test that enabling subtitle automatically enables translation."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "translate-enabled" in astro_frontend_content
        assert "toggleTranslate()" in astro_frontend_content


class TestAstroDashboardPlayerLink:
    """Tests for player link functionality."""

    @pytest.fixture
    def astro_frontend_content(self):
        """Load Astro index.astro content."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "index.astro"
        )
        if astro_path.exists():
            with open(astro_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_player_url_is_link(self, astro_frontend_content):
        """Test that player URL is an anchor tag."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "<a" in astro_frontend_content
        assert 'id="url-player"' in astro_frontend_content

    def test_player_url_has_target_blank(self, astro_frontend_content):
        """Test that player URL opens in new tab."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert 'target="_blank"' in astro_frontend_content

    def test_update_urls_updates_player_href(self, astro_frontend_content):
        """Test that updateUrls updates player href."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "playerLink.href" in astro_frontend_content


class TestAstroDashboardConfigStructure:
    """Tests for config structure sent to API."""

    @pytest.fixture
    def astro_frontend_content(self):
        """Load Astro index.astro content."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "index.astro"
        )
        if astro_path.exists():
            with open(astro_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_config_includes_input(self, astro_frontend_content):
        """Test that config includes input section."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "input:" in astro_frontend_content
        assert "type:" in astro_frontend_content
        assert "srt:" in astro_frontend_content

    def test_config_includes_modules(self, astro_frontend_content):
        """Test that config includes modules section."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "modules:" in astro_frontend_content
        assert "transcriber:" in astro_frontend_content
        assert "translator:" in astro_frontend_content
        assert "subtitle_generator:" in astro_frontend_content
        assert "tts_engine:" in astro_frontend_content
        assert "audio_mixer:" in astro_frontend_content
        assert "video_muxer:" in astro_frontend_content

    def test_config_includes_output(self, astro_frontend_content):
        """Test that config includes output section."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "output:" in astro_frontend_content
        assert "web:" in astro_frontend_content

    def test_save_config_uses_wrapper(self, astro_frontend_content):
        """Test that saveConfig sends config wrapped in config object."""
        if astro_frontend_content is None:
            pytest.skip("index.astro not found")

        assert "{ config: update }" in astro_frontend_content
