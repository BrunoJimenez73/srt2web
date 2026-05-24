"""
Tests for module status indicators functionality.
"""

from pathlib import Path

import pytest


class TestStatusIndicatorsCSS:
    """Tests for status indicator CSS styles."""

    @pytest.fixture
    def dashboard_html(self) -> None:
        """Load dashboard HTML content."""
        html_path = Path(__file__).parent.parent.parent / "web" / "index.html"
        if html_path.exists():
            with open(html_path, encoding="utf-8") as f:
                return f.read()
        return None

    def test_phosphor_green_color_exists(self, dashboard_html) -> None:
        """Test that phosphor green color (#00ff00) is defined."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "#00ff00" in dashboard_html

    def test_running_status_dot_style_exists(self, dashboard_html) -> None:
        """Test that .status-dot.running style exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert ".status-dot.running" in dashboard_html
        assert "background: #00ff00" in dashboard_html

    def test_error_status_dot_style_exists(self, dashboard_html) -> None:
        """Test that .status-dot.error style exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert ".status-dot.error" in dashboard_html
        assert "#ff3333" in dashboard_html

    def test_disabled_status_dot_style_exists(self, dashboard_html) -> None:
        """Test that .status-dot.disabled style exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert ".status-dot.disabled" in dashboard_html

    def test_phosphor_pulse_animation_exists(self, dashboard_html) -> None:
        """Test that phosphor-pulse animation is defined."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "@keyframes phosphor-pulse" in dashboard_html
        assert "#00ff00" in dashboard_html

    def test_indicator_pulse_animation_exists(self, dashboard_html) -> None:
        """Test that indicator-pulse animation is defined."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "@keyframes indicator-pulse" in dashboard_html

    def test_error_pulse_animation_exists(self, dashboard_html) -> None:
        """Test that error-pulse animation is defined."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "@keyframes error-pulse" in dashboard_html

    def test_process_card_active_style_exists(self, dashboard_html) -> None:
        """Test that .process-card.active style exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert ".process-card.active" in dashboard_html
        assert "rgba(0, 255, 0" in dashboard_html

    def test_process_indicator_style_exists(self, dashboard_html) -> None:
        """Test that .process-indicator style exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert ".process-indicator" in dashboard_html
        assert ".process-indicator.active" in dashboard_html

    def test_box_shadow_glow_effects(self, dashboard_html) -> None:
        """Test that box-shadow glow effects are defined."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "box-shadow" in dashboard_html
        # Check for multiple glow layers
        assert dashboard_html.count("box-shadow") >= 3


class TestStatusIndicatorsHTML:
    """Tests for status indicator HTML elements."""

    @pytest.fixture
    def dashboard_html(self) -> None:
        """Load dashboard HTML content."""
        html_path = Path(__file__).parent.parent.parent / "web" / "index.html"
        if html_path.exists():
            with open(html_path, encoding="utf-8") as f:
                return f.read()
        return None

    def test_status_dot_exists(self, dashboard_html) -> None:
        """Test that main status-dot element exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert 'id="status-dot"' in dashboard_html

    def test_all_module_status_dots_exist(self, dashboard_html) -> None:
        """Test that all expected module status dot elements exist."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        # The actual IDs in the dashboard use indicator-* naming
        expected_modules = [
            "indicator-input",
            "indicator-translate",
            "indicator-subtitle",
            "indicator-dub",
            "indicator-output",
        ]

        for module_id in expected_modules:
            assert f'id="{module_id}"' in dashboard_html

    def test_indicator_dub_exists(self, dashboard_html) -> None:
        """Test that indicator-dub element exists in DOBLAR card."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert 'id="indicator-dub"' in dashboard_html

    def test_indicator_subtitle_exists(self, dashboard_html) -> None:
        """Test that indicator-subtitle element exists in SUBTITULAR card."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert 'id="indicator-subtitle"' in dashboard_html

    def test_card_dub_exists(self, dashboard_html) -> None:
        """Test that card-dub element exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert 'id="card-dub"' in dashboard_html
        assert 'class="process-card"' in dashboard_html or "process-card" in dashboard_html

    def test_card_subtitle_exists(self, dashboard_html) -> None:
        """Test that card-subtitle element exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert 'id="card-subtitle"' in dashboard_html


class TestStatusIndicatorsJavaScript:
    """Tests for status indicator JavaScript functionality."""

    @pytest.fixture
    def dashboard_html(self) -> None:
        """Load dashboard HTML content."""
        html_path = Path(__file__).parent.parent.parent / "web" / "index.html"
        if html_path.exists():
            with open(html_path, encoding="utf-8") as f:
                return f.read()
        return None

    def test_update_module_status_function_exists(self, dashboard_html) -> None:
        """Test that updateModuleStatus function exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "function updateModuleStatus" in dashboard_html

    def test_update_module_status_handles_running_state(self, dashboard_html) -> None:
        """Test that updateModuleStatus handles running state."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "mod.state === 'running'" in dashboard_html
        assert "'running'" in dashboard_html

    def test_update_module_status_handles_error_state(self, dashboard_html) -> None:
        """Test that updateModuleStatus handles error state."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "mod.state === 'error'" in dashboard_html
        assert "statusDot.classList.add('error')" in dashboard_html

    def test_update_module_status_handles_disabled_state(self, dashboard_html) -> None:
        """Test that updateModuleStatus handles disabled state."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "mod.state === 'disabled'" in dashboard_html
        assert "statusDot.classList.add('disabled')" in dashboard_html

    def test_update_module_status_updates_process_cards(self, dashboard_html) -> None:
        """Test that updateModuleStatus updates process cards."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "moduleToCard" in dashboard_html
        assert "card.classList.add('active')" in dashboard_html

    def test_update_module_status_updates_indicators(self, dashboard_html) -> None:
        """Test that updateModuleStatus updates process indicators."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "moduleToIndicator" in dashboard_html
        assert "indicator.classList.add('active')" in dashboard_html

    def test_update_module_status_calls_from_load_status(self, dashboard_html) -> None:
        """Test that updateModuleStatus is called from loadStatus."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        # Check that loadStatus calls updateModuleStatus
        assert "updateModuleStatus(status)" in dashboard_html


class TestStatusIndicatorsMappings:
    """Tests for module-to-indicator mappings."""

    @pytest.fixture
    def dashboard_html(self) -> None:
        """Load dashboard HTML content."""
        html_path = Path(__file__).parent.parent.parent / "web" / "index.html"
        if html_path.exists():
            with open(html_path, encoding="utf-8") as f:
                return f.read()
        return None

    def test_tts_engine_maps_to_dub_card(self, dashboard_html) -> None:
        """Test that tts_engine module maps to card-dub."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "'tts_engine': 'card-dub'" in dashboard_html
        assert "'tts_engine': 'indicator-dub'" in dashboard_html

    def test_audio_mixer_maps_to_dub_card(self, dashboard_html) -> None:
        """Test that audio_mixer module maps to card-dub."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "'audio_mixer': 'card-dub'" in dashboard_html
        assert "'audio_mixer': 'indicator-dub'" in dashboard_html

    def test_translator_maps_to_translate_card(self, dashboard_html) -> None:
        """Test that translator module maps to card-translate."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "'translator': 'card-translate'" in dashboard_html
        assert "'translator': 'indicator-translate'" in dashboard_html

    def test_subtitle_generator_maps_to_subtitle_card(self, dashboard_html) -> None:
        """Test that subtitle_generator module maps to card-subtitle."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "'subtitle_generator': 'card-subtitle'" in dashboard_html
        assert "'subtitle_generator': 'indicator-subtitle'" in dashboard_html

    def test_transcriber_maps_to_whisper_card(self, dashboard_html) -> None:
        """Test that transcriber module maps to card-whisper."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "'transcriber': 'card-whisper'" in dashboard_html
        assert "'transcriber': 'indicator-whisper'" in dashboard_html
