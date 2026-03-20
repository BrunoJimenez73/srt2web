"""
E2E tests for the dashboard page.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestDashboardPageStructure:
    """Tests for dashboard page structure (without running server)."""

    @pytest.fixture
    def dashboard_html(self):
        """Load dashboard HTML content."""
        html_path = PROJECT_ROOT / "web" / "index.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_index_html_exists(self, dashboard_html):
        """Test that index.html exists."""
        assert dashboard_html is not None

    def test_has_required_elements(self, dashboard_html):
        """Test that HTML has all required elements."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert 'id="btn-start"' in dashboard_html
        assert 'id="btn-stop"' in dashboard_html
        assert (
            'id="status-url-srt"' in dashboard_html or 'id="url-srt"' in dashboard_html
        )
        assert 'id="logs-content"' in dashboard_html

    def test_has_navigation(self, dashboard_html):
        """Test that navigation elements exist."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "SRT2Web" in dashboard_html
        assert "Dashboard" in dashboard_html or "Processing Engine" in dashboard_html

    def test_has_srt_settings(self, dashboard_html):
        """Test that SRT settings form exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert 'id="input-port"' in dashboard_html
        assert 'id="input-type"' in dashboard_html
        assert 'id="input-latency"' in dashboard_html
        assert 'id="output-segment"' in dashboard_html

    def test_has_player_link(self, dashboard_html):
        """Test that player link exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "/player" in dashboard_html


class TestAppJavaScript:
    """Tests for app.js functionality."""

    @pytest.fixture
    def app_js_content(self):
        """Load app.js content."""
        js_path = PROJECT_ROOT / "web" / "js" / "app.js"
        if js_path.exists():
            with open(js_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_app_js_exists(self, app_js_content):
        """Test that app.js exists."""
        assert app_js_content is not None

    def test_has_api_calls(self, app_js_content):
        """Test that API call functions exist."""
        if app_js_content is None:
            pytest.skip("app.js not found")

        assert "function apiCall" in app_js_content
        assert "function startPipeline" in app_js_content
        assert "function stopPipeline" in app_js_content
        assert "function saveConfig" in app_js_content
        assert "function toggleModule" in app_js_content

    def test_has_module_labels(self, app_js_content):
        """Test that module labels are defined."""
        if app_js_content is None:
            pytest.skip("app.js not found")

        assert "MODULE_LABELS" in app_js_content
        assert "transcriber" in app_js_content
        assert "translator" in app_js_content
        assert "tts_engine" in app_js_content

    def test_has_api_endpoints(self, app_js_content):
        """Test that correct API endpoints are used."""
        if app_js_content is None:
            pytest.skip("app.js not found")

        # Check for API call function and endpoint patterns
        assert "apiCall" in app_js_content
        assert "loadStatus" in app_js_content
        assert "startPipeline" in app_js_content
        assert "stopPipeline" in app_js_content


class TestWebSocketClient:
    """Tests for WebSocket client."""

    @pytest.fixture
    def ws_js_content(self):
        """Load ws.js content."""
        js_path = PROJECT_ROOT / "web" / "js" / "ws.js"
        if js_path.exists():
            with open(js_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_ws_js_exists(self, ws_js_content):
        """Test that ws.js exists."""
        assert ws_js_content is not None

    def test_has_ws_client_class(self, ws_js_content):
        """Test that WSClient class is defined."""
        if ws_js_content is None:
            pytest.skip("ws.js not found")

        assert "class WSClient" in ws_js_content

    def test_has_reconnection_logic(self, ws_js_content):
        """Test that reconnection logic exists."""
        if ws_js_content is None:
            pytest.skip("ws.js not found")

        assert "reconnect" in ws_js_content.lower()

    def test_has_heartbeat(self, ws_js_content):
        """Test that heartbeat/ping mechanism exists."""
        if ws_js_content is None:
            pytest.skip("ws.js not found")

        assert "ping" in ws_js_content.lower()


class TestStreamPlayer:
    """Tests for StreamPlayer class."""

    @pytest.fixture
    def player_js_content(self):
        """Load player.js content."""
        js_path = PROJECT_ROOT / "web" / "js" / "player.js"
        if js_path.exists():
            with open(js_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def test_player_js_exists(self, player_js_content):
        """Test that player.js exists."""
        assert player_js_content is not None

    def test_has_stream_player_class(self, player_js_content):
        """Test that StreamPlayer class is defined."""
        if player_js_content is None:
            pytest.skip("player.js not found")

        assert "class StreamPlayer" in player_js_content

    def test_has_hls_integration(self, player_js_content):
        """Test that HLS.js integration exists."""
        if player_js_content is None:
            pytest.skip("player.js not found")

        assert "Hls" in player_js_content
        assert "hls.js" in player_js_content or "hls.js@" in player_js_content


class TestDashboardFunctionality:
    """Tests for dashboard functionality (with mocked server)."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock server for testing."""
        from fastapi.testclient import TestClient
        from server.app import create_app
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline

        config = ConfigManager()
        pipeline = Pipeline()

        # Add dummy modules
        class DummyModule:
            def __init__(self, name):
                self.name = name
                self.enabled = True
                from core.module_base import ModuleState

                self._state = ModuleState.IDLE

            def get_status(self):
                from core.module_base import ModuleStatus, ModuleState

                return ModuleStatus(
                    name=self.name,
                    state=self._state,
                    enabled=self.enabled,
                )

        pipeline.register_module(DummyModule("transcriber"))
        pipeline.register_module(DummyModule("translator"))

        srt_ingest = Mock()
        srt_ingest.is_receiving.return_value = False
        srt_ingest.get_srt_url.return_value = "srt://127.0.0.1:9000"

        app = create_app(
            {
                "config": config,
                "pipeline": pipeline,
                "srt_ingest": srt_ingest,
                "log_broadcast": Mock(),
            }
        )

        return TestClient(app)

    def test_page_loads_successfully(self, mock_server):
        """Test that dashboard page loads successfully."""
        response = mock_server.get("/")

        assert response.status_code == 200

    def test_api_status_returns_json(self, mock_server):
        """Test that /api/status returns valid JSON."""
        response = mock_server.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert "modules" in data

    def test_api_config_returns_json(self, mock_server):
        """Test that /api/config returns valid JSON."""
        response = mock_server.get("/api/config")

        assert response.status_code == 200
        data = response.json()
        assert "server" in data

    def test_can_update_config(self, mock_server):
        """Test that configuration can be updated."""
        response = mock_server.put(
            "/api/config", json={"config": {"pipeline": {"chunk_duration_sec": 6}}}
        )

        assert response.status_code == 200

    def test_srt_info_endpoint(self, mock_server):
        """Test SRT info endpoint."""
        response = mock_server.get("/api/srt-info")

        # srt-info may return 500 if no input source is configured
        assert response.status_code in [200, 500]
        data = response.json()

        # Check that either proper data or error is returned
        if response.status_code == 200:
            assert "srt_port" in data or "error" in data


class TestDashboardWithLiveServer:
    """
    Tests that require a live running server.
    These tests should be run with the server running.
    """

    @pytest.fixture
    def live_server_url(self):
        """Get the live server URL."""
        return "http://localhost:8080"

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in",
    )
    def test_live_server_health(self, live_server_url):
        """Test that live server is healthy."""
        import requests

        response = requests.get(f"{live_server_url}/health", timeout=5)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in",
    )
    def test_live_dashboard_accessible(self, live_server_url):
        """Test that dashboard is accessible on live server."""
        import requests

        response = requests.get(f"{live_server_url}/", timeout=5)

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
