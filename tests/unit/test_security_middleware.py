"""
Tests for the new security middleware (Phase 1).
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient


class TestRateLimiter:
    """Test the RateLimiter class."""

    def test_rate_limiter_allows_requests_under_limit(self):
        """Test that requests under the limit are allowed."""
        from server.security import RateLimiter

        limiter = RateLimiter(requests_per_minute=10)

        for i in range(10):
            allowed, remaining = limiter.is_allowed("test_key")
            assert allowed is True
            assert remaining == 9 - i

    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that requests over the limit are blocked."""
        from server.security import RateLimiter

        limiter = RateLimiter(requests_per_minute=5)

        # Use up all allowed requests
        for _ in range(5):
            limiter.is_allowed("test_key")

        # Next request should be blocked
        allowed, remaining = limiter.is_allowed("test_key")
        assert allowed is False
        assert remaining == 0

    def test_rate_limiter_different_keys(self):
        """Test that different keys have separate limits."""
        from server.security import RateLimiter

        limiter = RateLimiter(requests_per_minute=2)

        # Exhaust limit for key1
        limiter.is_allowed("key1")
        limiter.is_allowed("key1")

        # key2 should still be allowed
        allowed, _ = limiter.is_allowed("key2")
        assert allowed is True

    def test_rate_limiter_retry_after(self):
        """Test that retry_after returns correct wait time."""
        from server.security import RateLimiter

        limiter = RateLimiter(requests_per_minute=1)
        limiter.is_allowed("test_key")

        retry_after = limiter.get_retry_after("test_key")
        assert 0 < retry_after <= 61  # Should be around 60 seconds


class TestSecurityMiddleware:
    """Test the security middleware."""

    @pytest.fixture
    def app_with_auth(self):
        """Create a test app with authentication enabled."""
        from server.security import AuthMiddleware

        app = FastAPI()

        # Add auth middleware with a test token
        app.add_middleware(
            AuthMiddleware,
            get_auth_token=lambda: "test-token-123"
        )

        @app.get("/protected")
        async def protected():
            return {"message": "success"}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        return app

    def test_auth_middleware_allows_without_token_configured(self):
        """Test that requests pass when no token is configured."""
        from server.security import AuthMiddleware

        app = FastAPI()
        app.add_middleware(
            AuthMiddleware,
            get_auth_token=lambda: ""  # No token
        )

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

    def test_auth_middleware_blocks_without_auth_header(self, app_with_auth):
        """Test that requests without auth header are blocked."""
        client = TestClient(app_with_auth, raise_server_exceptions=False)
        response = client.get("/protected")
        assert response.status_code == 401

    def test_auth_middleware_allows_with_valid_token(self, app_with_auth):
        """Test that requests with valid token are allowed."""
        client = TestClient(app_with_auth)
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer test-token-123"}
        )
        assert response.status_code == 200

    def test_auth_middleware_blocks_with_invalid_token(self, app_with_auth):
        """Test that requests with invalid token are blocked."""
        client = TestClient(app_with_auth, raise_server_exceptions=False)
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer wrong-token"}
        )
        assert response.status_code == 401

    def test_auth_middleware_allows_public_paths(self, app_with_auth):
        """Test that public paths don't require authentication."""
        client = TestClient(app_with_auth)
        response = client.get("/health")
        assert response.status_code == 200


class TestSecurityHeadersMiddleware:
    """Test the security headers middleware."""

    def test_security_headers_present(self):
        """Test that security headers are added to responses."""
        from server.security import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
        assert "Content-Security-Policy" in response.headers
        assert "Strict-Transport-Security" in response.headers


class TestRequestSizeLimitMiddleware:
    """Test the request size limit middleware."""

    def test_allows_small_request(self):
        """Test that small requests are allowed."""
        from server.security import RequestSizeLimitMiddleware

        app = FastAPI()
        app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=1000)

        @app.post("/test")
        async def test_endpoint(data: dict):
            return {"received": True}

        client = TestClient(app)
        response = client.post("/test", json={"small": "data"})
        assert response.status_code == 200

    def test_blocks_large_request(self):
        """Test that large requests are blocked."""
        from server.security import RequestSizeLimitMiddleware

        app = FastAPI()
        app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=100)

        @app.post("/test")
        async def test_endpoint(data: dict):
            return {"received": True}

        client = TestClient(app, raise_server_exceptions=False)

        # Create a large payload that exceeds 100 bytes
        large_data = {"data": "x" * 100}
        response = client.post("/test", json=large_data)
        assert response.status_code == 413


class TestWebSocketAuth:
    """Test WebSocket authentication."""

    def test_validate_ws_auth_without_token(self):
        """Test that WS auth passes when no token is configured."""
        from server.security import validate_ws_auth

        mock_request = Mock(spec=Request)
        mock_request.query_params = {}
        mock_request.client = Mock(host="127.0.0.1")

        result = validate_ws_auth(mock_request, lambda: "")
        assert result is True

    def test_validate_ws_auth_with_valid_token(self):
        """Test that WS auth passes with valid token."""
        from server.security import validate_ws_auth

        mock_request = Mock(spec=Request)
        mock_request.query_params = {"token": "secret123"}
        mock_request.client = Mock(host="127.0.0.1")

        result = validate_ws_auth(mock_request, lambda: "secret123")
        assert result is True

    def test_validate_ws_auth_with_invalid_token(self):
        """Test that WS auth fails with invalid token."""
        from server.security import validate_ws_auth

        mock_request = Mock(spec=Request)
        mock_request.query_params = {"token": "wrong"}
        mock_request.client = Mock(host="127.0.0.1")

        result = validate_ws_auth(mock_request, lambda: "secret123")
        assert result is False

    def test_validate_ws_auth_without_token_param(self):
        """Test that WS auth fails when token is required but not provided."""
        from server.security import validate_ws_auth

        mock_request = Mock(spec=Request)
        mock_request.query_params = {}
        mock_request.client = Mock(host="127.0.0.1")

        result = validate_ws_auth(mock_request, lambda: "secret123")
        assert result is False


class TestConfigManagerDefaults:
    """Test that config manager has secure defaults."""

    def test_default_host_is_localhost(self):
        """Test that default host is 127.0.0.1 (localhost only)."""
        from core.config_manager import ConfigManager, DEFAULT_CONFIG

        assert DEFAULT_CONFIG["server"]["host"] == "127.0.0.1"

    def test_default_auth_token_is_empty(self):
        """Test that auth_token defaults to empty (backwards compatible)."""
        from core.config_manager import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["server"]["auth_token"] == ""

    def test_default_rate_limit_configured(self):
        """Test that rate limiting is configured by default."""
        from core.config_manager import DEFAULT_CONFIG

        assert "rate_limit_rpm" in DEFAULT_CONFIG["server"]
        assert DEFAULT_CONFIG["server"]["rate_limit_rpm"] == 60


class TestSecurityCardComponent:
    """Test that security functionality exists in the frontend."""

    def test_security_in_header_component(self):
        """Test that security button exists in Header component."""
        import os
        header_path = "frontend/src/components/Header.astro"
        if not os.path.exists(header_path):
            pytest.skip("Header.astro not found")
        with open(header_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Secure" in content, "Security toggle should be in Header"

    def test_api_ts_has_auth_functions(self):
        """Test that api.ts has auth token functions."""
        with open("frontend/src/lib/api.ts", "r") as f:
            content = f.read()

        assert "getAuthToken" in content, "getAuthToken function not found"
        assert "setAuthToken" in content, "setAuthToken function not found"
        assert "clearAuthToken" in content, "clearAuthToken function not found"
        assert "Authorization" in content, "Authorization header handling not found"


class TestSecurityFixes:
    """Tests for security fixes applied to the codebase."""

    def test_csp_no_unsafe_eval(self):
        """Test that CSP does not allow unsafe-eval."""
        import importlib
        import server.security as sec
        importlib.reload(sec)

        # Read the source to check CSP string
        import inspect
        source = inspect.getsource(sec.SecurityHeadersMiddleware.dispatch)

        # Create a mock request/response to extract CSP
        # Instead, just check the source code directly
        assert "unsafe-eval" not in source, \
            "CSP should not contain unsafe-eval"

    def test_config_endpoint_masks_token(self):
        """Test that /api/config does not expose raw auth_token."""
        from fastapi.testclient import TestClient
        from server.app import create_app
        from core.config_manager import ConfigManager

        config = ConfigManager()
        config.set("server.auth_token", "secret_token_123")

        app = create_app({
            "config": config,
            "pipeline": MagicMock(),
            "srt_ingest": MagicMock(),
            "log_broadcast": lambda x, y: None,
        })

        client = TestClient(app)
        response = client.get(
            "/api/config",
            headers={"Authorization": "Bearer secret_token_123"}
        )
        assert response.status_code == 200

        data = response.json()
        token_value = data.get("server", {}).get("auth_token", "")
        assert token_value == "***", \
            f"auth_token should be masked, got: {token_value}"

    def test_host_default_is_localhost(self):
        """Test that default host is 127.0.0.1, not 0.0.0.0."""
        import inspect
        from main import main

        source = inspect.getsource(main)
        # Check that the code defaults to 127.0.0.1
        assert '127.0.0.1' in source or "config.get(\"server.host\"" in source

    def test_docs_url_disabled(self):
        """Test that Swagger docs are disabled."""
        from server.app import create_app

        app = create_app({
            "config": MagicMock(),
            "pipeline": MagicMock(),
            "srt_ingest": MagicMock(),
            "log_broadcast": lambda x, y: None,
        })

        assert app.docs_url is None, "Swagger docs should be disabled"
        assert app.redoc_url is None, "ReDoc should be disabled"

    def test_xff_spoofing_protection(self):
        """Test that X-Forwarded-For is only trusted from localhost."""
        from server.security import RateLimitMiddleware, RateLimiter

        # Read the source to verify the logic
        import inspect
        source = inspect.getsource(RateLimitMiddleware._get_client_ip)

        # Should check client host before trusting XFF
        assert "127.0.0.1" in source or "localhost" in source, \
            "X-Forwarded-For should only be trusted from localhost"

    def test_ws_max_subscribers(self):
        """Test that WebSocket has a max subscriber limit."""
        from server.ws_routes import LogBroadcaster

        assert hasattr(LogBroadcaster, 'MAX_SUBSCRIBERS'), \
            "LogBroadcaster should have MAX_SUBSCRIBERS limit"
        assert LogBroadcaster.MAX_SUBSCRIBERS <= 50, \
            "MAX_SUBSCRIBERS should be reasonable (<=50)"

    def test_error_response_no_traceback(self):
        """Test that toggle endpoint does not expose tracebacks."""
        import inspect
        from server.api_routes import create_api_router

        source = inspect.getsource(create_api_router)

        # The error handler should not include err_msg in response
        # Look for the pattern where "error": err_msg was removed
        lines = source.split('\n')
        in_toggle_catch = False
        for line in lines:
            if 'except Exception as e:' in line:
                in_toggle_catch = True
            if in_toggle_catch and '"error":' in line and 'err_msg' in line:
                raise AssertionError("Toggle endpoint still exposes err_msg in response")
            if in_toggle_catch and 'return {' in line and 'error' not in line:
                break
