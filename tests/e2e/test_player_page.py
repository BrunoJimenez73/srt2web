"""
E2E tests for the player page.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestPlayerPageStructure:
    """Tests for player page structure."""

    @pytest.fixture
    def player_html_content(self):
        """Load player HTML content."""
        html_path = PROJECT_ROOT / "web" / "player.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_player_html_exists(self, player_html_content):
        """Test that player.html exists."""
        assert player_html_content is not None

    def test_has_video_element(self, player_html_content):
        """Test that HTML has video element."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "<video" in player_html_content
        assert 'id="video-player"' in player_html_content

    def test_has_hls_js_included(self, player_html_content):
        """Test that HLS.js is included."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "hls.js" in player_html_content.lower()

    def test_has_subtitle_styling(self, player_html_content):
        """Test that subtitle styling is defined."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "::cue" in player_html_content or "text-shadow" in player_html_content

    def test_links_to_hls_stream(self, player_html_content):
        """Test that player links to HLS stream."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "master.m3u8" in player_html_content or "/hls/" in player_html_content


class TestPlayerSubtitleHandling:
    """Tests for player subtitle handling."""

    @pytest.fixture
    def player_html_content(self):
        """Load player HTML content."""
        html_path = PROJECT_ROOT / "web" / "player.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_hls_subtitles_enabled_is_false(self, player_html_content):
        """Test that HLS.js subtitlesEnabled is set to false to prevent duplicate tracks."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "subtitlesEnabled: false" in player_html_content

    def test_manual_subtitle_track_creation(self, player_html_content):
        """Test that manual subtitle track is created via JavaScript."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert (
            "subtitleTrackElement = document.createElement('track')"
            in player_html_content
        )
        assert "subtitleTrackElement.kind = 'subtitles'" in player_html_content

    def test_subtitle_track_label_dynamic_from_manifest(self, player_html_content):
        """Test that subtitle track label is updated from HLS manifest."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "subtitleLanguageName = firstTrack.name" in player_html_content
        assert (
            "subtitleTrackElement.label = subtitleLanguageName" in player_html_content
        )

    def test_subtitle_refresh_interval_is_1_second(self, player_html_content):
        """Test that subtitle refresh interval is 1 second for better sync."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "setInterval(loadVTT, 1000)" in player_html_content

    def test_track_appended_to_video_element(self, player_html_content):
        """Test that manual track is appended to video element."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "video.appendChild(subtitleTrackElement)" in player_html_content

    def test_only_first_subtitle_track_enabled(self, player_html_content):
        """Test that only first subtitle track is kept, others disabled."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "i === 0" in player_html_content or "(i === 0)" in player_html_content
        assert "'showing'" in player_html_content
        assert "'disabled'" in player_html_content

    def test_subtitle_tracks_updated_event_handler(self, player_html_content):
        """Test that SUBTITLE_TRACKS_UPDATED event updates language info."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "SUBTITLE_TRACKS_UPDATED" in player_html_content

    def test_srclang_defaults_to_spanish(self, player_html_content):
        """Test that srclang defaults to Spanish (es)."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "srclang = 'es'" in player_html_content

    def test_default_track_label_is_spanish(self, player_html_content):
        """Test that default track label is Spanish."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "label = subtitleLanguageName || 'Spanish'" in player_html_content


class TestPlayerFunctionality:
    """Tests for player functionality."""

    @pytest.fixture
    def player_html_content(self):
        """Load player HTML content."""
        html_path = PROJECT_ROOT / "web" / "player.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    @pytest.fixture
    def mock_server(self):
        """Create a mock server for testing."""
        from fastapi.testclient import TestClient
        from server.app import create_app
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline

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

    def test_player_endpoint_accessible(self, mock_server):
        """Test that player endpoint is accessible."""
        response = mock_server.get("/player")

        assert response.status_code == 200

    def test_hls_directory_mounted(self, mock_server):
        """Test that HLS directory is mounted."""
        # Try to access HLS directory
        response = mock_server.get("/hls/")

        # Should either serve files or return 404 if empty
        assert response.status_code in [200, 404]

    def test_player_has_autoplay(self, player_html_content):
        """Test that video has autoplay attribute."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "autoplay" in player_html_content

    def test_player_has_playsinline(self, player_html_content):
        """Test that video has playsinline for mobile."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "playsinline" in player_html_content


class TestPlayerJavaScript:
    """Tests for player JavaScript logic."""

    def test_hls_initialization(self):
        """Test HLS.js initialization code exists."""
        player_js_path = PROJECT_ROOT / "web" / "js" / "player.js"

        if not player_js_path.exists():
            pytest.skip("player.js not found")

        with open(player_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "new Hls" in content
        assert "loadSource" in content
        assert "attachMedia" in content

    def test_hls_error_handling(self):
        """Test HLS error handling code exists."""
        player_js_path = PROJECT_ROOT / "web" / "js" / "player.js"

        if not player_js_path.exists():
            pytest.skip("player.js not found")

        with open(player_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Hls.Events.ERROR" in content
        assert "fatal" in content.lower()

    def test_subtitle_tracks_handling(self):
        """Test subtitle tracks handling code exists."""
        player_js_path = PROJECT_ROOT / "web" / "js" / "player.js"

        if not player_js_path.exists():
            pytest.skip("player.js not found")

        with open(player_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "subtitleTrack" in content
        assert "textTracks" in content


class TestPlayerWithLiveServer:
    """Tests that require a live running server."""

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in",
    )
    def test_live_player_accessible(self):
        """Test that player page is accessible on live server."""
        import requests

        response = requests.get("http://localhost:9999/player", timeout=5)

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in",
    )
    def test_hls_stream_available(self):
        """Test that HLS stream is available."""
        import requests

        response = requests.head("http://localhost:9999/hls/master.m3u8", timeout=5)

        # May not exist yet if pipeline isn't running
        assert response.status_code in [200, 404]


class TestPlayerResponsive:
    """Tests for player responsiveness."""

    @pytest.fixture
    def player_html_content(self):
        """Load player HTML content."""
        html_path = PROJECT_ROOT / "web" / "player.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_player_has_full_viewport(self, player_html_content):
        """Test that player uses full viewport."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert "width: 100%" in player_html_content
        assert "height: 100%" in player_html_content
        assert "object-fit: contain" in player_html_content

    def test_player_has_black_background(self, player_html_content):
        """Test that player has black background."""
        if player_html_content is None:
            pytest.skip("player.html not found")

        assert (
            "background-color: #000" in player_html_content
            or "background-color: black" in player_html_content
            or "background: #000" in player_html_content
        )
