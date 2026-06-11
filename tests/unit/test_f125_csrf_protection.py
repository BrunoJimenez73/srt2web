"""
F125: CSRF protection tests.

Tests CsrfMiddleware token generation/validation and the /api/csrf-token endpoint.
"""

import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestCsrfTokenGeneration:
    """Test CSRF token generation and validation."""

    def test_generate_and_validate(self):
        """Generated token should validate successfully."""
        from server.security import CsrfMiddleware

        secret = "test-secret-123"
        token = CsrfMiddleware.generate_token(secret)
        assert CsrfMiddleware.validate_token(token, secret) is True

    def test_different_secrets_fail(self):
        """Token generated with one secret should not validate with another."""
        from server.security import CsrfMiddleware

        token = CsrfMiddleware.generate_token("secret-1")
        assert CsrfMiddleware.validate_token(token, "secret-2") is False

    def test_empty_secret_fails(self):
        """Empty secret should return False."""
        from server.security import CsrfMiddleware

        token = CsrfMiddleware.generate_token("secret")
        assert CsrfMiddleware.validate_token(token, "") is False

    def test_invalid_token_format(self):
        """Malformed tokens should return False."""
        from server.security import CsrfMiddleware

        assert CsrfMiddleware.validate_token("", "secret") is False
        assert CsrfMiddleware.validate_token("not-base64!!!", "secret") is False
        assert CsrfMiddleware.validate_token("aGVsbG8=", "secret") is False  # "hello"

    def test_expired_token_rejected(self):
        """Expired token should be rejected."""
        from server.security import CsrfMiddleware

        secret = "test-secret"
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000
            token = CsrfMiddleware.generate_token(secret)
            # Advance past expiry
            mock_time.return_value = 1000 + 3600 + 1
            assert CsrfMiddleware.validate_token(token, secret) is False

    def test_token_not_expired_yet(self):
        """Token should be valid before expiry."""
        from server.security import CsrfMiddleware

        secret = "test-secret"
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000
            token = CsrfMiddleware.generate_token(secret)
            # Still within window
            mock_time.return_value = 1000 + 1800
            assert CsrfMiddleware.validate_token(token, secret) is True

    def test_unique_tokens(self):
        """Each generated token should be different."""
        from server.security import CsrfMiddleware

        secret = "test-secret"
        tokens = {CsrfMiddleware.generate_token(secret) for _ in range(10)}
        assert len(tokens) == 10


class TestCsrfMiddleware:
    """Test the CsrfMiddleware integration."""

    def _make_app(self):
        from server.security import CsrfMiddleware

        app = FastAPI()
        app.add_middleware(
            CsrfMiddleware,
            get_csrf_secret=lambda: "test-csrf-secret",
        )

        @app.post("/api/test-mutate")
        async def mutate_endpoint():
            return {"status": "mutated"}

        @app.get("/api/test-read")
        async def read_endpoint():
            return {"status": "read"}

        return TestClient(app, raise_server_exceptions=False)

    def test_get_request_skips_csrf(self):
        """GET requests should not require CSRF token."""
        client = self._make_app()
        resp = client.get("/api/test-read")
        assert resp.status_code == 200

    def test_post_without_csrf_rejected(self):
        """POST without CSRF token should be rejected with 403."""
        client = self._make_app()
        resp = client.post("/api/test-mutate", json={"data": "test"})
        assert resp.status_code == 403
        assert "CSRF" in resp.text

    def test_post_with_valid_csrf_accepted(self):
        """POST with valid CSRF token should be accepted."""
        from server.security import CsrfMiddleware

        client = self._make_app()
        token = CsrfMiddleware.generate_token("test-csrf-secret")
        resp = client.post(
            "/api/test-mutate",
            json={"data": "test"},
            headers={"X-CSRF-Token": token},
        )
        assert resp.status_code == 200

    def test_post_with_invalid_csrf_rejected(self):
        """POST with invalid CSRF token should be rejected."""
        client = self._make_app()
        resp = client.post(
            "/api/test-mutate",
            json={"data": "test"},
            headers={"X-CSRF-Token": "invalid-token"},
        )
        assert resp.status_code == 403

    def test_authorization_header_exempts_csrf(self):
        """Requests with Bearer Authorization header should skip CSRF."""
        client = self._make_app()
        resp = client.post(
            "/api/test-mutate",
            json={"data": "test"},
            headers={"Authorization": "Bearer some-token"},
        )
        assert resp.status_code == 200

    def test_csrf_token_across_multiple_requests(self):
        """Same CSRF token should work for multiple requests within expiry."""
        from server.security import CsrfMiddleware

        client = self._make_app()
        token = CsrfMiddleware.generate_token("test-csrf-secret")
        for _ in range(3):
            resp = client.post(
                "/api/test-mutate",
                json={"data": "test"},
                headers={"X-CSRF-Token": token},
            )
            assert resp.status_code == 200

    def test_public_paths_skip_csrf(self):
        """Public and auth paths should not require CSRF."""
        from server.security import CsrfMiddleware

        app = FastAPI()
        app.add_middleware(
            CsrfMiddleware,
            get_csrf_secret=lambda: "test-csrf-secret",
        )

        @app.post("/api/auth/login")
        async def login():
            return {"status": "ok"}

        @app.post("/api/auth/setup")
        async def setup():
            return {"status": "ok"}

        client = TestClient(app, raise_server_exceptions=False)
        resp1 = client.post("/api/auth/login", json={"username": "admin", "password": "pass"})
        assert resp1.status_code == 200
        resp2 = client.post("/api/auth/setup", json={"password": "pass"})
        assert resp2.status_code == 200

    def test_put_and_delete_also_protected(self):
        """PUT and DELETE should also require CSRF."""
        from server.security import CsrfMiddleware

        app = FastAPI()
        app.add_middleware(
            CsrfMiddleware,
            get_csrf_secret=lambda: "test-csrf-secret",
        )

        @app.put("/api/test-put")
        async def put_endpoint():
            return {"status": "ok"}

        @app.delete("/api/test-delete")
        async def delete_endpoint():
            return {"status": "ok"}

        client = TestClient(app, raise_server_exceptions=False)
        resp1 = client.put("/api/test-put", json={"data": "test"})
        assert resp1.status_code == 403
        resp2 = client.delete("/api/test-delete")
        assert resp2.status_code == 403


class TestCsrfTokenEndpoint:
    """Test the GET /api/auth/csrf-token endpoint."""

    def setup_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def teardown_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    @pytest.fixture(autouse=True)
    def _setup(self):
        from core.auth_db import auth_db

        auth_db._users.clear()
        auth_db._blacklist.clear()
        auth_db.setup_first_admin("MyStr0ng!Pass")
        yield

    def _get_token(self, secret: str = "test-jwt-secret") -> str:
        """Helper: login and return auth token."""
        from core.auth_db import auth_db
        from server.routes.auth import login, LoginRequest
        import asyncio

        with patch("core.auth_db.JWT_SECRET_KEY", secret):
            result = asyncio.run(login(LoginRequest(username="admin", password="MyStr0ng!Pass")))
            return result["access_token"]

    def test_csrf_endpoint_returns_token(self):
        """GET /api/auth/csrf-token should return a CSRF token."""
        from server.routes.auth import csrf_token
        from unittest.mock import patch, MagicMock
        import asyncio

        token = self._get_token()
        request = MagicMock()
        request.headers = {"Authorization": f"Bearer {token}"}

        with patch("core.auth_db.JWT_SECRET_KEY", "test-jwt-secret"):
            result = asyncio.run(csrf_token(request))
            assert "csrf_token" in result
            assert result["token_type"] == "csrf"
            assert result["expires_in"] == 3600
            assert len(result["csrf_token"]) > 10

    def test_csrf_endpoint_requires_auth(self):
        """GET /api/auth/csrf-token without auth should fail."""
        from fastapi import HTTPException
        from server.routes.auth import csrf_token
        from unittest.mock import MagicMock
        import asyncio

        request = MagicMock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc:
            asyncio.run(csrf_token(request))
        assert exc.value.status_code == 401

    def test_generated_token_works_with_middleware(self):
        """CSRF token from endpoint should work with middleware."""
        from server.security import CsrfMiddleware
        from unittest.mock import patch, MagicMock
        import asyncio

        token = self._get_token()
        request = MagicMock()
        request.headers = {"Authorization": f"Bearer {token}"}

        with patch("core.auth_db.JWT_SECRET_KEY", "test-jwt-secret"):
            from server.routes.auth import csrf_token

            result = asyncio.run(csrf_token(request))
            csrf = result["csrf_token"]
            assert CsrfMiddleware.validate_token(csrf, "test-jwt-secret")

    def test_csrf_endpoint_503_without_jwt_secret(self):
        """CSRF endpoint returns 503 when JWT secret is not configured."""
        from fastapi import HTTPException
        from server.routes.auth import csrf_token
        from unittest.mock import MagicMock, patch
        import asyncio

        request = MagicMock()
        request.headers = {"Authorization": "Bearer some-token"}

        with patch("server.routes.auth._get_current_user") as mock_auth:
            mock_auth.return_value = {"sub": "admin", "role": "admin"}
            with patch("core.auth_db.JWT_SECRET_KEY", ""):
                with pytest.raises(HTTPException) as exc:
                    asyncio.run(csrf_token(request))
                assert exc.value.status_code == 503
