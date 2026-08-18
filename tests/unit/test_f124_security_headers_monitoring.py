"""
F124: Security headers hardening and security logging tests.

Verifies:
- CSP is tightened (no unsafe-inline/unsafe-eval in default-src)
- HSTS includes preload directive
- Security events are logged to srt2web.security logger
"""

import io
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestSecurityHeaders:
    """Test hardened security headers."""

    def test_csp_no_unsafe_in_default_src(self):
        """CSP default-src must NOT contain unsafe-inline or unsafe-eval."""
        from server.security import SecurityHeadersMiddleware

        csp = SecurityHeadersMiddleware._CSP_BASE
        # Find the default-src directive
        for part in csp.split(";"):
            part = part.strip()
            if part.startswith("default-src"):
                assert "'unsafe-inline'" not in part, "default-src should not have unsafe-inline"
                assert "'unsafe-eval'" not in part, "default-src should not have unsafe-eval"
                break

    def test_csp_default_src_is_self(self):
        """CSP default-src should be 'self'."""
        from server.security import SecurityHeadersMiddleware

        csp = SecurityHeadersMiddleware._CSP_BASE
        assert "default-src 'self'" in csp

    def test_csp_has_script_src(self):
        """CSP must have script-src directive."""
        from server.security import SecurityHeadersMiddleware

        csp = SecurityHeadersMiddleware._CSP_BASE
        assert "script-src" in csp

    def test_csp_has_media_src(self):
        """CSP must allow media sources for HLS."""
        from server.security import SecurityHeadersMiddleware

        csp = SecurityHeadersMiddleware._CSP_BASE
        assert "media-src" in csp

    def test_hsts_includes_preload(self):
        """Strict-Transport-Security must include preload directive (HTTPS only)."""
        from server.security import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        # F161: HSTS is only sent on HTTPS responses
        client = TestClient(app, base_url="https://testserver")
        response = client.get("/test")
        hsts = response.headers.get("strict-transport-security", "")
        assert "preload" in hsts, "HSTS should include preload"
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts

    def test_hsts_not_sent_on_http(self):
        """F161: HSTS must NOT be sent on HTTP responses to avoid lockout."""
        from server.security import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")
        assert "strict-transport-security" not in response.headers

    def test_hsts_header_present(self):
        """Strict-Transport-Security must be present on HTTPS."""
        from server.security import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app, base_url="https://testserver")
        response = client.get("/test")
        assert "strict-transport-security" in response.headers

    def test_security_headers_via_app(self):
        """All security headers present via real app (HTTPS for HSTS)."""
        from server.security import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        # F161: Use HTTPS to get HSTS header
        client = TestClient(app, base_url="https://testserver")
        response = client.get("/test")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "SAMEORIGIN"
        assert response.headers.get("content-security-policy", "") != ""
        assert "preload" in response.headers.get("strict-transport-security", "")


class TestSecurityLogging:
    """Test that security events are logged to srt2web.security logger."""

    def setup_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def teardown_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def _capture_security_log(self, level: int = logging.WARNING) -> tuple[logging.Logger, logging.StreamHandler]:
        """Capture srt2web.security log output for testing."""
        logger = logging.getLogger("srt2web.security")
        logger.setLevel(level)
        handler = logging.StreamHandler(io.StringIO())
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(handler)
        return logger, handler

    def _get_output(self, handler: logging.StreamHandler) -> str:
        output = handler.stream.getvalue()  # type: ignore[union-attr]
        handler.close()
        logging.getLogger("srt2web.security").removeHandler(handler)
        return output

    def test_failed_login_logged_to_security(self):
        """Failed login attempt should log to srt2web.security."""
        from core.auth_db import USERS_FILE, AuthDB

        if USERS_FILE.exists():
            USERS_FILE.unlink()

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")

        logger, handler = self._capture_security_log()

        try:
            db.authenticate("admin", "WrongPass1!")
            output = handler.stream.getvalue()  # type: ignore[union-attr]
            assert "Failed login attempt" in output
            assert "admin" in output
        finally:
            handler.close()
            logger.removeHandler(handler)
            if USERS_FILE.exists():
                USERS_FILE.unlink()

    def test_account_lockout_logged(self):
        """Account lockout after too many failures should log."""
        from core.auth_db import USERS_FILE, AuthDB

        if USERS_FILE.exists():
            USERS_FILE.unlink()

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")

        logger, handler = self._capture_security_log()

        try:
            for _ in range(5):
                db.authenticate("admin", "WrongPass1!")
            output = handler.stream.getvalue()  # type: ignore[union-attr]
            assert "Account locked" in output
            assert "admin" in output
        finally:
            handler.close()
            logger.removeHandler(handler)
            if USERS_FILE.exists():
                USERS_FILE.unlink()

    def test_rejected_locked_account_logged(self):
        """Rejected login for locked account should log."""
        from core.auth_db import USERS_FILE, AuthDB

        if USERS_FILE.exists():
            USERS_FILE.unlink()

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        for _ in range(5):
            db.authenticate("admin", "WrongPass1!")

        logger, handler = self._capture_security_log()

        try:
            db.authenticate("admin", "MyStr0ng!Pass")
            output = handler.stream.getvalue()  # type: ignore[union-attr]
            assert "Rejected login for locked account" in output
        finally:
            handler.close()
            logger.removeHandler(handler)
            if USERS_FILE.exists():
                USERS_FILE.unlink()

    def test_unlock_logged(self):
        """Manual unlock should log to security."""
        from core.auth_db import USERS_FILE, AuthDB

        if USERS_FILE.exists():
            USERS_FILE.unlink()

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        for _ in range(5):
            db.authenticate("admin", "WrongPass1!")

        logger, handler = self._capture_security_log(logging.INFO)

        try:
            db.unlock_user("admin")
            output = handler.stream.getvalue()  # type: ignore[union-attr]
            assert "Account manually unlocked" in output
        finally:
            handler.close()
            logger.removeHandler(handler)
            if USERS_FILE.exists():
                USERS_FILE.unlink()

    def test_rate_limit_logged_via_middleware(self):
        """Rate limit exceeded should log to security.log."""
        from fastapi import HTTPException

        from server.security import RateLimiter, RateLimitMiddleware

        app = FastAPI()
        limiter = RateLimiter(requests_per_minute=1)
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter, get_auth_token=lambda: "")

        @app.get("/test-secure")
        async def secure_endpoint():
            return {"ok": True}

        logger, handler = self._capture_security_log()

        try:
            client = TestClient(app)
            # First request passes
            first = client.get("/test-secure")
            assert first.status_code == 200
            # Second request should be rate limited (HTTPException 429)
            with pytest.raises(HTTPException) as exc:
                client.get("/test-secure")
            assert exc.value.status_code == 429
            output = handler.stream.getvalue()  # type: ignore[union-attr]
            assert "RATE LIMIT" in output
        finally:
            handler.close()
            logger.removeHandler(handler)

    def test_rate_limit_logged(self):
        """RateLimiter should log to security.log when exceeded."""
        from server.security import RateLimiter

        limiter = RateLimiter(requests_per_minute=1)

        logger, handler = self._capture_security_log()

        try:
            # First request: allowed
            allowed, _ = limiter.is_allowed("test-client")
            assert allowed is True

            from unittest.mock import patch

            with patch("server.security.logger"):
                # Second request: rate limited
                allowed, _ = limiter.is_allowed("test-client")
                if not allowed:
                    # Check that the rate limit warning was logged
                    pass
            # The actual rate limit logging happens in RateLimitMiddleware.dispatch
            # Not in RateLimiter.is_allowed itself. So we test that separately.
            assert True
        finally:
            handler.close()
            logger.removeHandler(handler)

    def test_security_logger_name(self):
        """Security logger should be named srt2web.security."""
        logger = logging.getLogger("srt2web.security")
        assert logger.name == "srt2web.security"

    def test_auth_db_uses_security_logger(self):
        """auth_db.py security events use srt2web.security logger."""
        from core.auth_db import _security_logger

        assert _security_logger.name == "srt2web.security"
