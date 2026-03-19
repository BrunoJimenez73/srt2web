"""
Tests for Astro player page functionality.
"""

import pytest
from pathlib import Path


class TestPlayerAstroStructure:
    """Tests for Astro player page structure."""

    @pytest.fixture
    def player_astro_content(self):
        """Load Astro player.astro content."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "player.astro"
        )
        if astro_path.exists():
            with open(astro_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_player_astro_file_exists(self):
        """Test that player.astro file exists."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "player.astro"
        )
        assert astro_path.exists()

    def test_player_has_video_element(self, player_astro_content):
        """Test that player has video element."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert '<video id="video-player"' in player_astro_content
        assert "controls" in player_astro_content
        assert "autoplay" in player_astro_content

    def test_player_has_waiting_message(self, player_astro_content):
        """Test that player has waiting message."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "Esperando stream" in player_astro_content

    def test_player_includes_hls_js(self, player_astro_content):
        """Test that player includes HLS.js library."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "hls.js" in player_astro_content

    def test_player_has_vtt_loader(self, player_astro_content):
        """Test that player has VTT loader function."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "loadVTT" in player_astro_content
        assert "/hls/subs.vtt" in player_astro_content

    def test_player_has_init_player_function(self, player_astro_content):
        """Test that player has initPlayer function."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "initPlayer" in player_astro_content
        assert "/hls/master.m3u8" in player_astro_content

    def test_player_has_subtitle_listener(self, player_astro_content):
        """Test that player has subtitle change listener."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "setupSubtitleChangeListener" in player_astro_content


class TestPlayerAstroStyles:
    """Tests for Astro player page styles."""

    @pytest.fixture
    def player_astro_content(self):
        """Load Astro player.astro content."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "player.astro"
        )
        if astro_path.exists():
            with open(astro_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_player_has_black_background(self, player_astro_content):
        """Test that player has black background."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "background-color: #000" in player_astro_content

    def test_player_has_video_container(self, player_astro_content):
        """Test that player has video container."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "video-container" in player_astro_content
        assert "video-player" in player_astro_content

    def test_player_has_cue_styling(self, player_astro_content):
        """Test that player has subtitle cue styling."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "::cue" in player_astro_content

    def test_player_has_waiting_text_style(self, player_astro_content):
        """Test that player has waiting text styling."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "waiting-text" in player_astro_content


class TestPlayerAstroJavaScript:
    """Tests for Astro player JavaScript functionality."""

    @pytest.fixture
    def player_astro_content(self):
        """Load Astro player.astro content."""
        astro_path = (
            Path(__file__).parent.parent.parent
            / "frontend"
            / "src"
            / "pages"
            / "player.astro"
        )
        if astro_path.exists():
            with open(astro_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_player_loads_vtt_periodically(self, player_astro_content):
        """Test that player loads VTT periodically."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "setInterval" in player_astro_content
        assert "loadVTT" in player_astro_content

    def test_player_creates_track_element(self, player_astro_content):
        """Test that player creates track element."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "createElement" in player_astro_content
        assert "kind = 'subtitles'" in player_astro_content

    def test_player_handles_hls_events(self, player_astro_content):
        """Test that player handles HLS events."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "MANIFEST_PARSED" in player_astro_content
        assert "ERROR" in player_astro_content

    def test_player_retries_on_error(self, player_astro_content):
        """Test that player retries initialization on error."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "ERROR" in player_astro_content
        assert "initPlayer" in player_astro_content

    def test_player_supports_apple_hls(self, player_astro_content):
        """Test that player supports native HLS on Apple devices."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert "canPlayType" in player_astro_content
        assert "application/vnd.apple.mpegurl" in player_astro_content
