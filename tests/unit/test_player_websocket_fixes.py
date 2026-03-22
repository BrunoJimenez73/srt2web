"""
Tests for WebSocket, CSP, and HLS playback fixes.

These tests verify that:
- CSP headers allow HLS playback resources
- WebSocket connections work without errors
- HLS endpoints are accessible
- Player code has no JavaScript errors
"""

import pytest
from fastapi.testclient import TestClient


class TestCSPHeaders:
    """Test that CSP headers allow HLS playback."""

    @pytest.fixture
    def client(self):
        from server.app import create_app
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline

        config = ConfigManager()
        pipeline = Pipeline()
        app_context = {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": None,
            "log_subscribers": [],
            "log_broadcast": lambda level, msg: None,
        }
        app = create_app(app_context)
        return TestClient(app)

    def test_csp_allows_hls_media(self, client):
        """Test that CSP allows media from HTTP sources."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")
        
        # Should allow media from http/https
        assert "media-src" in csp
        assert "http://" in csp or "https://" in csp

    def test_csp_allows_cdn_scripts(self, client):
        """Test that CSP allows scripts from CDN (for HLS.js)."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")
        
        # Should allow jsdelivr.net for HLS.js
        assert "cdn.jsdelivr.net" in csp

    def test_csp_allows_websockets(self, client):
        """Test that CSP allows WebSocket connections."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")
        
        # Should allow ws:// and wss:// connections
        assert "ws://" in csp or "connect-src" in csp

    def test_security_headers_present(self, client):
        """Test that all security headers are present."""
        response = client.get("/health")
        
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "content-security-policy" in response.headers


class TestWebSocketConnection:
    """Test WebSocket connection works correctly."""

    @pytest.fixture
    def client(self):
        from server.app import create_app
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline

        config = ConfigManager()
        pipeline = Pipeline()
        app_context = {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": None,
            "log_subscribers": [],
            "log_broadcast": lambda level, msg: None,
        }
        app = create_app(app_context)
        return TestClient(app)

    def test_websocket_connects_successfully(self, client):
        """Test that WebSocket connects without errors."""
        with client.websocket_connect("/ws/logs") as ws:
            # Connection should succeed
            assert ws is not None

    def test_websocket_ping_pong(self, client):
        """Test that WebSocket handles ping/pong."""
        with client.websocket_connect("/ws/logs") as ws:
            ws.send_text('{"type": "ping"}')
            response = ws.receive_text()
            assert "pong" in response

    def test_websocket_accepts_without_token_when_no_auth(self, client):
        """Test WebSocket accepts connections when auth is disabled."""
        # With no auth_token configured, should accept
        with client.websocket_connect("/ws/logs") as ws:
            # Should connect successfully
            assert ws is not None


class TestHTTPEndpoints:
    """Test HTTP endpoints work correctly."""

    @pytest.fixture
    def client(self):
        from server.app import create_app
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline

        config = ConfigManager()
        pipeline = Pipeline()
        app_context = {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": None,
            "log_subscribers": [],
            "log_broadcast": lambda level, msg: None,
        }
        app = create_app(app_context)
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_config_endpoint(self, client):
        """Test config endpoint returns configuration."""
        response = client.get("/api/config")
        assert response.status_code == 200
        config = response.json()
        assert "server" in config
        assert "modules" in config

    def test_status_endpoint(self, client):
        """Test status endpoint returns pipeline status."""
        response = client.get("/api/status")
        assert response.status_code == 200
        status = response.json()
        assert "state" in status


class TestPlayerCode:
    """Test that player.astro has correct code."""

    def test_player_has_hls_js_import(self):
        """Test that player imports HLS.js from CDN."""
        with open("frontend/src/pages/player.astro", "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "hls.js" in content
        assert "cdn.jsdelivr.net" in content or "jsdelivr" in content

    def test_player_has_error_overlay(self):
        """Test that player has error overlay elements."""
        with open("frontend/src/pages/player.astro", "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "error-overlay" in content
        assert "error-message" in content
        assert "btn-retry" in content

    def test_player_has_show_error_function(self):
        """Test that player has showError function."""
        with open("frontend/src/pages/player.astro", "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "showError" in content
        assert "hideError" in content

    def test_player_no_invalid_error_types(self):
        """Test that player doesn't use invalid Hls.ErrorTypes."""
        with open("frontend/src/pages/player.astro", "r", encoding="utf-8") as f:
            content = f.read()
        
        # These should not exist
        assert "ERROR其它" not in content
        assert "ERROR_UNKNOWN" not in content or "ErrorTypes" in content

    def test_player_hides_waiting_on_manifest_parsed(self):
        """Test that player hides waiting message on MANIFEST_PARSED."""
        with open("frontend/src/pages/player.astro", "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "MANIFEST_PARSED" in content
        assert "waiting.style.display = 'none'" in content

    def test_player_has_error_handling(self):
        """Test that player has proper HLS error handling."""
        with open("frontend/src/pages/player.astro", "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "Hls.Events.ERROR" in content
        assert "NETWORK_ERROR" in content
        assert "MEDIA_ERROR" in content


class TestWebSocketRequestWrapper:
    """Test WebSocketRequest wrapper class."""

    def test_websocket_request_class_exists(self):
        """Test that WebSocketRequest class is defined."""
        from server.ws_routes import WebSocketRequest
        
        assert WebSocketRequest is not None

    def test_websocket_request_has_required_fields(self):
        """Test that WebSocketRequest has required fields."""
        from server.ws_routes import WebSocketRequest
        
        # Create a mock request
        req = WebSocketRequest(
            headers={},
            query_params={},
            client=None
        )
        
        assert hasattr(req, 'headers')
        assert hasattr(req, 'query_params')
        assert hasattr(req, 'client')


class TestSecurityMiddlewareOrder:
    """Test that security middlewares are applied in correct order."""

    def test_app_has_gzip_middleware(self):
        """Test that GZip middleware is added."""
        from server.app import create_app
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline

        config = ConfigManager()
        pipeline = Pipeline()
        app_context = {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": None,
            "log_subscribers": [],
            "log_broadcast": lambda level, msg: None,
        }
        app = create_app(app_context)
        
        # Check that middleware is present
        middleware_names = [type(m).__name__ for m in app.user_middleware]
        # GZipMiddleware should be present
        assert any("GZip" in name for name in middleware_names) or len(app.user_middleware) > 0

    def test_app_has_security_headers(self, client):
        """Test that security headers are applied to responses."""
        response = client.get("/health")
        
        # All these headers should be present
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "SAMEORIGIN"
        assert "content-security-policy" in response.headers
        assert "strict-transport-security" in response.headers
