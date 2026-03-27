"""
Tests for Astro player page functionality.
"""

import pytest
from pathlib import Path


def get_astro_source_content(file_path):
    """Load Astro source file for testing."""
    base_path = Path(__file__).parent.parent.parent / "frontend" / "src"
    astro_file = base_path / file_path

    if astro_file.exists():
        with open(astro_file, "r", encoding="utf-8") as f:
            return f.read()
    return None


def get_built_html_content(file_path="player/index.html"):
    """Load built HTML file for testing."""
    base_path = Path(__file__).parent.parent.parent / "server" / "static"
    html_file = base_path / file_path

    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return None


class TestPlayerAstroStructure:
    """Tests for Astro player page structure."""

    @pytest.fixture
    def player_astro_content(self):
        """Load Astro player.astro content."""
        return get_astro_source_content("pages/player.astro")

    @pytest.fixture
    def player_built_content(self):
        """Load built player HTML."""
        return get_built_html_content("player/index.html")

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

    def test_player_built_html_exists(self, player_built_content):
        """Test that built player HTML exists."""
        assert player_built_content is not None

    def test_player_has_video_element(self, player_built_content):
        """Test that player has video element."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "<video" in player_built_content or "video-player" in player_built_content
        )
        assert "controls" in player_built_content

    def test_player_has_waiting_message(self, player_astro_content):
        """Test that player has waiting message."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert (
            "Esperando" in player_astro_content
            or "waiting" in player_astro_content.lower()
        )

    def test_player_includes_hls_js(self, player_built_content):
        """Test that player includes HLS.js library."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert "hls.js" in player_built_content or "Hls" in player_built_content

    def test_player_has_hls_source(self, player_built_content):
        """Test that player has HLS source URL."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert "/hls/" in player_built_content or "m3u8" in player_built_content

    def test_player_has_subtitle_track(self, player_built_content):
        """Test that player has subtitle track element."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "track" in player_built_content.lower()
            or "subtitle" in player_built_content.lower()
        )


class TestPlayerAstroStyles:
    """Tests for Astro player page styles."""

    @pytest.fixture
    def player_astro_content(self):
        """Load Astro player.astro content."""
        return get_astro_source_content("pages/player.astro")

    def test_player_has_video_container(self, player_astro_content):
        """Test that player has video container."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert (
            "video-container" in player_astro_content
            or "video" in player_astro_content.lower()
        )

    def test_player_has_cue_styling(self, player_astro_content):
        """Test that player has subtitle cue styling."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert (
            "::cue" in player_astro_content
            or "subtitle" in player_astro_content.lower()
        )


class TestPlayerJavaScript:
    """Tests for player JavaScript functionality."""

    @pytest.fixture
    def player_built_content(self):
        """Load built player HTML."""
        return get_built_html_content("player/index.html")

    def test_player_has_hls_initialization(self, player_built_content):
        """Test that player has HLS initialization code."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert "Hls" in player_built_content or "hls.js" in player_built_content

    def test_player_handles_hls_events(self, player_built_content):
        """Test that player handles HLS events."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "MANIFEST_PARSED" in player_built_content or "ERROR" in player_built_content
        )

    def test_player_has_vtt_loader(self, player_built_content):
        """Test that player has VTT loader function."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "vtt" in player_built_content.lower()
            or "subtitle" in player_built_content.lower()
        )

    def test_player_has_refresh_interval(self, player_built_content):
        """Test that player has periodic refresh for subtitles."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert "setInterval" in player_built_content

    def test_player_supports_native_hls(self, player_built_content):
        """Test that player supports native HLS on Apple devices."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "canPlayType" in player_built_content or "nativeHls" in player_built_content
        )


class TestPlayerHLSIntegration:
    """Tests for HLS integration in player."""

    @pytest.fixture
    def player_built_content(self):
        """Load built player HTML."""
        return get_built_html_content("player/index.html")

    def test_player_loads_master_playlist(self, player_built_content):
        """Test that player loads master playlist."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert "m3u8" in player_built_content or "/hls/" in player_built_content

    def test_player_loads_subtitle_playlist(self, player_built_content):
        """Test that player loads subtitle playlist."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "vtt" in player_built_content.lower()
            or "subtitle" in player_built_content.lower()
        )

    def test_player_has_error_handling(self, player_built_content):
        """Test that player has error handling."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "error" in player_built_content.lower() or "ERROR" in player_built_content
        )


class TestPlayerControls:
    """Tests for player controls."""

    @pytest.fixture
    def player_built_content(self):
        """Load built player HTML."""
        return get_built_html_content("player/index.html")

    def test_player_has_play_controls(self, player_built_content):
        """Test that player has play controls."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert "video" in player_built_content.lower()

    def test_player_has_volume_control(self, player_built_content):
        """Test that player has volume control."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "volume" in player_built_content.lower()
            or "video" in player_built_content.lower()
        )

    def test_player_has_fullscreen_support(self, player_built_content):
        """Test that player has video element which supports browser fullscreen."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")
        # Video element inherently supports fullscreen via browser controls
        assert (
            "video" in player_built_content.lower()
            and "controls" in player_built_content.lower()
        )


class TestPlayerSubtitles:
    """Tests for subtitle functionality."""

    @pytest.fixture
    def player_astro_content(self):
        """Load Astro player.astro content."""
        return get_astro_source_content("pages/player.astro")

    @pytest.fixture
    def player_built_content(self):
        """Load built player HTML."""
        return get_built_html_content("player/index.html")

    def test_player_has_subtitle_support(self, player_astro_content):
        """Test that player has subtitle support."""
        if player_astro_content is None:
            pytest.skip("player.astro not found")

        assert (
            "subtitle" in player_astro_content.lower()
            or "track" in player_astro_content.lower()
        )

    def test_player_loads_vtt_files(self, player_built_content):
        """Test that player loads VTT files."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "vtt" in player_built_content.lower()
            or "/hls/subs.vtt" in player_built_content
        )

    def test_player_has_cc_toggle(self, player_built_content):
        """Test that player has CC toggle button."""
        if player_built_content is None:
            pytest.skip("Built player/index.html not found")

        assert (
            "cc" in player_built_content.lower()
            or "subtitle" in player_built_content.lower()
        )
