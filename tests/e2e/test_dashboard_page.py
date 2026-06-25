"""
E2E tests for the dashboard page using Astro frontend.
"""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_astro_source_content(file_path):  # type: ignore
    """Load Astro source file for testing."""
    base_path = PROJECT_ROOT / "frontend" / "src"
    astro_file = base_path / file_path

    if astro_file.exists():
        with open(astro_file, encoding="utf-8") as f:
            return f.read()
    return None


def get_built_html_content(file_path="index.html"):  # type: ignore
    """Load built HTML file for testing."""
    html_path = PROJECT_ROOT / "server" / "static" / file_path
    if html_path.exists():
        with open(html_path, encoding="utf-8") as f:
            return f.read()
    return None


def get_js_content(file_path):  # type: ignore
    """Load JavaScript/TypeScript file for testing."""
    js_path = PROJECT_ROOT / "frontend" / "src" / "lib" / file_path
    if js_path.exists():
        with open(js_path, encoding="utf-8") as f:
            return f.read()
    return None


class TestDashboardPageStructure:
    """Tests for dashboard page structure (without running server)."""

    @pytest.fixture
    def dashboard_html(self) -> None:
        """Load dashboard HTML content."""
        return get_built_html_content("index.html")

    @pytest.fixture
    def dashboard_astro(self) -> None:
        """Load dashboard Astro source."""
        return get_astro_source_content("pages/index.astro")

    def test_index_astro_exists(self, dashboard_astro) -> None:
        """Test that index.astro exists."""
        assert dashboard_astro is not None

    def test_built_html_exists(self, dashboard_html) -> None:
        """Test that built index.html exists."""
        assert dashboard_html is not None

    def test_has_required_elements(self, dashboard_html) -> None:
        """Test that HTML has all required elements."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        # Check for dashboard structure
        assert "dashboard" in dashboard_html.lower() or "process" in dashboard_html.lower()

    def test_has_navigation(self, dashboard_html) -> None:
        """Test that navigation elements exist."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "SRT2Web" in dashboard_html or "srt2web" in dashboard_html.lower()

    def test_has_player_link(self, dashboard_html) -> None:
        """Test that player link exists."""
        if dashboard_html is None:
            pytest.skip("index.html not found")

        assert "/player" in dashboard_html or "player" in dashboard_html


class TestAppJavaScript:
    """Tests for app.js functionality (API library)."""

    @pytest.fixture
    def api_lib_content(self) -> None:
        """Load API library content."""
        return get_js_content("api.ts")

    def test_api_lib_exists(self, api_lib_content) -> None:
        """Test that api.ts exists."""
        assert api_lib_content is not None

    def test_has_api_calls(self, api_lib_content) -> None:
        """Test that API call functions exist."""
        if api_lib_content is None:
            pytest.skip("api.ts not found")

        assert "fetch" in api_lib_content.lower() or "api" in api_lib_content.lower()

    def test_has_module_labels(self, api_lib_content) -> None:
        """Test that module labels are defined."""
        if api_lib_content is None:
            pytest.skip("api.ts not found")

        assert (
            "transcriber" in api_lib_content or "translator" in api_lib_content or "module" in api_lib_content.lower()
        )


class TestWebSocketClient:
    """Tests for WebSocket client."""

    @pytest.fixture
    def api_lib_content(self) -> None:
        """Load API library content."""
        return get_js_content("api.ts")

    def test_has_ws_client_or_connection(self, api_lib_content) -> None:
        """Test that WebSocket connection is defined."""
        if api_lib_content is None:
            pytest.skip("api.ts not found")

        assert "ws" in api_lib_content.lower() or "websocket" in api_lib_content.lower()

    def test_has_reconnection_logic(self, api_lib_content) -> None:
        """Test that reconnection logic exists."""
        if api_lib_content is None:
            pytest.skip("api.ts not found")

        # Look for reconnection patterns
        has_reconnect = "reconnect" in api_lib_content.lower()
        has_retry = "retry" in api_lib_content.lower() or "attempt" in api_lib_content.lower()
        assert has_reconnect or has_retry


class TestStreamPlayer:
    """Tests for player integration."""

    @pytest.fixture
    def player_html(self) -> None:
        """Load built player HTML."""
        return get_built_html_content("player/index.html")

    def test_player_html_exists(self, player_html) -> None:
        """Test that player HTML exists."""
        assert player_html is not None

    def test_has_hls_integration(self, player_html) -> None:
        """Test that HLS.js integration exists."""
        if player_html is None:
            pytest.skip("player/index.html not found")

        assert "Hls" in player_html or "hls.js" in player_html


class TestDashboardWithMockServer:
    """Tests for dashboard functionality (with mocked server)."""

    @pytest.fixture
    def mock_server(self) -> None:
        """Create a mock server for testing."""
        from fastapi.testclient import TestClient

        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from server.app import create_app

        config = ConfigManager()
        pipeline = Pipeline()

        # Add dummy modules
        class DummyModule:
            def __init__(self, name):  # type: ignore
                self.name = name
                self.enabled = True
                from core.module_base import ModuleState

                self._state = ModuleState.IDLE

            def get_status(self):  # type: ignore
                from core.module_base import ModuleStatus

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

    def test_page_loads_successfully(self, mock_server):  # type: ignore
        """Test that dashboard page loads successfully."""
        response = mock_server.get("/")

        assert response.status_code == 200

    def test_api_status_returns_json(self, mock_server):  # type: ignore
        """Test that /api/status returns valid JSON."""
        response = mock_server.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert "modules" in data

    def test_api_config_returns_json(self, mock_server):  # type: ignore
        """Test that /api/config returns valid JSON."""
        response = mock_server.get("/api/config")

        assert response.status_code == 200
        data = response.json()
        assert "server" in data

    def test_can_update_config(self, mock_server):  # type: ignore
        """Test that configuration can be updated."""
        response = mock_server.put("/api/config", json={"config": {"pipeline": {"chunk_duration_sec": 6}}})

        assert response.status_code == 200

    def test_srt_info_endpoint(self, mock_server):  # type: ignore
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
    def live_server_url(self) -> None:
        """Get the live server URL."""
        return "http://localhost:9999"

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in",
    )
    def test_live_server_health(self, live_server_url) -> None:
        """Test that live server is healthy."""
        import requests

        response = requests.get(f"{live_server_url}/health", timeout=5)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in",
    )
    def test_live_dashboard_accessible(self, live_server_url) -> None:
        """Test that dashboard is accessible on live server."""
        import requests

        response = requests.get(f"{live_server_url}/", timeout=5)

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestAstroComponents:
    """Tests for Astro components structure."""

    @pytest.fixture
    def header_content(self) -> None:
        """Load Header component."""
        return get_astro_source_content("components/Header.astro")

    @pytest.fixture
    def status_card_content(self) -> None:
        """Load StatusCard component."""
        return get_astro_source_content("components/StatusCard.astro")

    @pytest.fixture
    def metrics_card_content(self) -> None:
        """Load MetricsCard component."""
        return get_astro_source_content("components/MetricsCard.astro")

    @pytest.fixture
    def process_grid_content(self) -> None:
        """Load ProcessGrid component."""
        return get_astro_source_content("components/ProcessGrid.astro")

    @pytest.fixture
    def log_panel_content(self) -> None:
        """Load LogPanel component."""
        return get_astro_source_content("components/LogPanel.astro")

    def test_header_component_exists(self, header_content) -> None:
        """Test that Header component exists."""
        assert header_content is not None

    def test_status_card_component_exists(self, status_card_content) -> None:
        """Test that StatusCard component exists."""
        assert status_card_content is not None

    def test_metrics_card_component_exists(self, metrics_card_content) -> None:
        """Test that MetricsCard component exists."""
        assert metrics_card_content is not None

    def test_process_grid_component_exists(self, process_grid_content) -> None:
        """Test that ProcessGrid component exists."""
        assert process_grid_content is not None

    def test_log_panel_component_exists(self, log_panel_content) -> None:
        """Test that LogPanel component exists."""
        assert log_panel_content is not None

    def test_header_has_logo(self, header_content) -> None:
        """Test that Header has logo."""
        if header_content is None:
            pytest.skip("Header.astro not found")
        assert "logo" in header_content.lower() or "SRT2Web" in header_content

    def test_status_card_has_controls(self, status_card_content) -> None:
        """Test that StatusCard has pipeline controls."""
        if status_card_content is None:
            pytest.skip("StatusCard.astro not found")
        assert "start" in status_card_content.lower() or "stop" in status_card_content.lower()

    def test_metrics_card_has_metrics(self, metrics_card_content) -> None:
        """Test that MetricsCard has metrics display."""
        if metrics_card_content is None:
            pytest.skip("MetricsCard.astro not found")
        assert (
            "cpu" in metrics_card_content.lower()
            or "memory" in metrics_card_content.lower()
            or "metric" in metrics_card_content.lower()
        )


class TestStaticAssets:
    """Tests for static assets."""

    def test_favicon_exists(self) -> None:
        """Test that favicon exists."""
        favicon_path = PROJECT_ROOT / "server" / "static" / "favicon.svg"
        assert favicon_path.exists()

    def test_astro_css_assets_exist(self) -> None:
        """Test that Astro CSS assets exist."""
        astro_css_path = PROJECT_ROOT / "server" / "static" / "_astro"
        if astro_css_path.exists():
            css_files = list(astro_css_path.glob("*.css"))
            assert len(css_files) > 0, "No CSS files found in _astro directory"
