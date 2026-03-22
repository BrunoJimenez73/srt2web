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
    """Test that security card component exists."""

    def test_security_card_file_exists(self):
        """Test that the SecurityCard component file exists."""
        import os
        card_path = "frontend/src/components/SecurityCard.astro"
        assert os.path.exists(card_path), f"SecurityCard component not found at {card_path}"

    def test_api_ts_has_auth_functions(self):
        """Test that api.ts has auth token functions."""
        with open("frontend/src/lib/api.ts", "r") as f:
            content = f.read()

        assert "getAuthToken" in content, "getAuthToken function not found"
        assert "setAuthToken" in content, "setAuthToken function not found"
        assert "clearAuthToken" in content, "clearAuthToken function not found"
        assert "Authorization" in content, "Authorization header handling not found"
