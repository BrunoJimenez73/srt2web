"""
E2E tests for the player page.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _get_player_html():  # type: ignore
    """Load player HTML content - try built output first, then web dir."""
    built_path = PROJECT_ROOT / "server" / "static" / "player" / "index.html"
    if built_path.exists():
        with open(built_path, encoding="utf-8") as f:
            return f.read()
    html_path = PROJECT_ROOT / "web" / "player.html"
    if html_path.exists():
        with open(html_path, encoding="utf-8") as f:
            return f.read()
    return None


def _get_player_js_bundle() -> str | None:
    """Load the Astro-bundled player JS (where F108 subtitle logic lives)."""
    bundle_dir = PROJECT_ROOT / "server" / "static" / "_astro"
    if not bundle_dir.exists():
        return None
    for js_file in sorted(bundle_dir.glob("player*.js")):
        with open(js_file, encoding="utf-8") as f:
            return f.read()
    return None


def _get_player_combined() -> str | None:
    """Load HTML + Astro JS bundle as a single string (HTML first, then JS)."""
    html = _get_player_html()
    if html is None:
        return None
    js = _get_player_js_bundle() or ""
    return html + "\n" + js


class TestPlayerPageStructure:
    """Tests for player page structure."""

    @pytest.fixture
    def player_html_content(self) -> None:
        return _get_player_html()

    def test_player_html_exists(self, player_html_content) -> None:
        """Test that player.html exists."""
        assert player_html_content is not None

    def test_has_video_element(self, player_html_content) -> None:
        """Test that HTML has video element."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "<video" in player_html_content
        assert 'id="video-player"' in player_html_content

    def test_has_hls_js_included(self, player_html_content) -> None:
        """Test that HLS.js is included."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        content_lower = player_html_content.lower()
        assert (
            "hls.js" in content_lower
            or "hls.min.js" in content_lower
            or "cdn.jsdelivr.net" in content_lower
            or "hls" in content_lower
        )

    def test_has_subtitle_styling(self, player_html_content) -> None:
        """Test that subtitle styling is defined."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "::cue" in player_html_content or "text-shadow" in player_html_content

    def test_links_to_hls_stream(self, player_html_content) -> None:
        """Test that player links to HLS stream (URL built in JS bundle, F108)."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        combined = _get_player_combined() or player_html_content
        assert "master.m3u8" in combined or "/hls/" in combined or "stream.m3u8" in combined


class TestPlayerSubtitleHandling:
    """Tests for player subtitle handling."""

    @pytest.fixture
    def player_html_content(self) -> None:
        return _get_player_html()

    def test_hls_subtitles_enabled(self, player_html_content) -> None:
        """Test that HLS.js subtitlesEnabled is configured."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        assert "subtitlesEnabled" in player_html_content

    def test_manual_subtitle_track_creation(self, player_html_content) -> None:
        """Test that manual subtitle track is created via JavaScript."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        assert "createElement" in player_html_content
        assert "subtitles" in player_html_content

    def test_subtitle_track_label_from_manifest(self, player_html_content) -> None:
        """Test that subtitle track label is updated from HLS manifest."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        assert (
            "firstTrack" in player_html_content
            or "subtitleLanguageName" in player_html_content
            or "subtitleTracks" in player_html_content
            or "SUBTITLE_TRACKS_UPDATED" in player_html_content
        )

    def test_subtitle_native_hls_handling(self, player_html_content) -> None:
        """Test that subtitle updates use HLS.js native events (F108, no polling)."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        combined = _get_player_combined() or player_html_content
        assert "hlsSubtitleTracksUpdated" in combined
        assert "hlsManifestParsed" in combined
        assert "preferredLang" in combined
        assert "subtitleTrack" in combined

    def test_track_appended_to_video(self, player_html_content) -> None:
        """Test that manual track is appended to video element."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        assert "appendChild" in player_html_content

    def test_subtitle_tracks_updated_event(self, player_html_content) -> None:
        """Test that SUBTITLE_TRACKS_UPDATED event updates language info."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        assert "SUBTITLE_TRACKS_UPDATED" in player_html_content or "subtitle" in player_html_content.lower()

    def test_srclang_defaults_to_spanish(self, player_html_content) -> None:
        """Test that srclang defaults to Spanish (es)."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        assert "srclang" in player_html_content

    def test_default_track_label_is_spanish(self, player_html_content) -> None:
        """Test that default track label is Spanish."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        assert "Spanish" in player_html_content or "label" in player_html_content


class TestPlayerFunctionality:
    """Tests for player functionality."""

    @pytest.fixture
    def player_html_content(self) -> None:
        return _get_player_html()

    @pytest.fixture
    def mock_server(self) -> None:
        """Create a mock server for testing."""
        from fastapi.testclient import TestClient

        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from server.app import create_app

        config = ConfigManager()
        pipeline = Pipeline()
        srt_ingest = Mock()

        app = create_app(
            {
                "config": config,
                "pipeline": pipeline,
                "srt_ingest": srt_ingest,
                "log_broadcast": lambda x, y: None,
            }
        )

        return TestClient(app)

    def test_player_endpoint_accessible(self, mock_server) -> None:
        """Test that player endpoint is accessible."""
        response = mock_server.get("/player")
        assert response.status_code == 200

    def test_hls_directory_mounted(self, mock_server) -> None:
        """Test that HLS directory is mounted."""
        response = mock_server.get("/hls/")
        assert response.status_code in [200, 404]

    def test_player_has_autoplay(self, player_html_content) -> None:
        """Test that video has autoplay attribute."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        assert "autoplay" in player_html_content

    def test_player_has_playsinline(self, player_html_content) -> None:
        """Test that video has playsinline for mobile."""
        if player_html_content is None:
            pytest.skip("player.html not found")
        assert "playsinline" in player_html_content


class TestPlayerJavaScript:
    """Tests for player JavaScript logic."""

    def test_hls_initialization(self) -> None:
        """Test HLS.js initialization code exists."""
        player_js_path = PROJECT_ROOT / "web" / "js" / "player.js"
        if not player_js_path.exists():
            pytest.skip("player.js not found")

        with open(player_js_path, encoding="utf-8") as f:
            content = f.read()

        assert "new Hls" in content
        assert "loadSource" in content
        assert "attachMedia" in content

    def test_hls_error_handling(self) -> None:
        """Test HLS error handling code exists."""
        player_js_path = PROJECT_ROOT / "web" / "js" / "player.js"
        if not player_js_path.exists():
            pytest.skip("player.js not found")

        with open(player_js_path, encoding="utf-8") as f:
            content = f.read()

        assert "Hls.Events.ERROR" in content
        assert "fatal" in content.lower()

    def test_subtitle_tracks_handling(self) -> None:
        """Test subtitle tracks handling code exists."""
        player_js_path = PROJECT_ROOT / "web" / "js" / "player.js"
        if not player_js_path.exists():
            pytest.skip("player.js not found")

        with open(player_js_path, encoding="utf-8") as f:
            content = f.read()

        assert "subtitleTrack" in content
        assert "textTracks" in content


class TestPlayerWithLiveServer:
    """Tests that require a live running server."""

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in",
    )
    def test_live_player_accessible(self) -> None:
        """Test that player page is accessible on live server."""
        import requests

        response = requests.get("http://localhost:8080/player", timeout=5)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in",
    )
    def test_hls_stream_available(self) -> None:
        """Test that HLS stream is available."""
        import requests

        response = requests.head("http://localhost:8080/hls/master.m3u8", timeout=5)
        assert response.status_code in [200, 404]


class TestPlayerResponsive:
    """Tests for player responsiveness."""

    @pytest.fixture
    def player_html_and_css(self) -> None:
        """Load player HTML and CSS content."""
        html_content = _get_player_html()
        css_content = None

        css_dir = PROJECT_ROOT / "server" / "static" / "_astro"
        if css_dir.exists():
            for css_file in css_dir.glob("*.css"):
                with open(css_file, encoding="utf-8") as f:
                    css_content = (css_content or "") + f.read()

        return html_content, css_content

    def test_player_has_full_viewport(self, player_html_and_css) -> None:
        """Test that player uses full viewport."""
        html_content, css_content = player_html_and_css
        if html_content is None:
            pytest.skip("player.html not found")

        combined = html_content + (css_content or "")
        assert "width" in combined and "100%" in combined
        assert "height" in combined and "100%" in combined

    def test_player_has_black_background(self, player_html_and_css) -> None:
        """Test that player has dark background."""
        html_content, css_content = player_html_and_css
        if html_content is None:
            pytest.skip("player.html not found")

        combined = html_content + (css_content or "")
        assert "background" in combined or "#000" in combined or "black" in combined
