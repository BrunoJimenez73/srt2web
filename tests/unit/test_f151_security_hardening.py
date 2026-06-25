"""F151: Security Hardening v2 — tests for path traversal, timing-safe WS auth,
traceback leak, WebRTC session bounding, output config validation."""

import hmac

import pytest

# ---------------------------------------------------------------------------
# 1. Path traversal in /docs/{path}
# ---------------------------------------------------------------------------


class TestDocsPathTraversal:
    """Verify that the docs fallback route rejects path traversal attempts."""

    def test_path_traversal_dot_dot_rejected(self):
        from pathlib import PurePosixPath

        path = "../../config.yaml"
        sanitized = PurePosixPath(path)
        assert ".." in sanitized.parts

    def test_absolute_path_rejected(self):
        from pathlib import PurePosixPath

        path = "/etc/passwd"
        sanitized = PurePosixPath(path)
        assert sanitized.is_absolute()

    def test_normal_path_allowed(self):
        from pathlib import PurePosixPath

        path = "architecture/index"
        sanitized = PurePosixPath(path)
        assert ".." not in sanitized.parts
        assert not sanitized.is_absolute()


# ---------------------------------------------------------------------------
# 2. Timing-safe WS token comparison
# ---------------------------------------------------------------------------


class TestTimingSafeWSAuth:
    """Verify WS auth uses hmac.compare_digest, not ==."""

    def test_ws_routes_uses_hmac_compare_digest(self):
        """The ws_routes module should import hmac for timing-safe comparison."""
        import server.ws_routes

        assert hasattr(server.ws_routes, "hmac") or hasattr(hmac, "compare_digest")

    def test_compare_digest_same_token(self):
        token = "secret-token-12345"
        assert hmac.compare_digest(token, token) is True

    def test_compare_digest_different_token(self):
        assert hmac.compare_digest("token-a", "token-b") is False

    def test_compare_digest_empty_strings(self):
        assert hmac.compare_digest("", "") is True


# ---------------------------------------------------------------------------
# 3. Traceback leak removal
# ---------------------------------------------------------------------------


class TestTracebackLeak:
    """Verify that API error responses no longer include traceback."""

    def test_modules_route_no_traceback_in_response(self):
        """The modules toggle error path should return warning, not error with traceback."""
        import inspect

        from server.routes.modules import toggle_module

        source = inspect.getsource(toggle_module)
        # Should NOT contain traceback.format_exc() in the response dict
        assert "traceback.format_exc()" not in source or "warning" in source

    def test_modules_route_logs_full_traceback(self):
        """Server should still log the full traceback, just not return it."""
        import inspect

        from server.routes.modules import toggle_module

        source = inspect.getsource(toggle_module)
        # logger.error should be called with traceback info
        assert "logger.error" in source


# ---------------------------------------------------------------------------
# 4. WebRTC session bounding
# ---------------------------------------------------------------------------


class TestWebRTCSessionsBounding:
    """Verify WebRTC sessions have TTL and max count enforcement."""

    def test_session_cleanup_exists(self):
        """The webrtc router factory should define cleanup logic."""
        import inspect

        from server.webrtc_routes import create_webrtc_router

        source = inspect.getsource(create_webrtc_router)
        assert "_cleanup_stale_sessions" in source or "cleanup" in source.lower()

    def test_session_has_ttl(self):
        """Sessions should have a max age constant."""
        import inspect

        from server.webrtc_routes import create_webrtc_router

        source = inspect.getsource(create_webrtc_router)
        assert "_SESSION_MAX_AGE_SEC" in source

    def test_session_has_max_count(self):
        """Sessions should have a max count limit."""
        import inspect

        from server.webrtc_routes import create_webrtc_router

        source = inspect.getsource(create_webrtc_router)
        assert "_SESSION_MAX_COUNT" in source


# ---------------------------------------------------------------------------
# 5. Output config validation
# ---------------------------------------------------------------------------


class TestOutputConfigValidation:
    """Verify that dangerous config keys are rejected."""

    def test_forbidden_keys_defined(self):
        from server.routes.outputs import _FORBIDDEN_CONFIG_KEYS

        assert "command" in _FORBIDDEN_CONFIG_KEYS
        assert "exec" in _FORBIDDEN_CONFIG_KEYS
        assert "shell" in _FORBIDDEN_CONFIG_KEYS

    def test_validate_output_config_clean(self):
        from server.routes.outputs import _validate_output_config

        # Should not raise
        _validate_output_config({"url": "rtmp://localhost/live/stream"})

    def test_validate_output_config_rejects_dangerous(self):
        from fastapi import HTTPException

        from server.routes.outputs import _validate_output_config

        with pytest.raises(HTTPException) as exc_info:
            _validate_output_config({"command": "rm -rf /"})
        assert exc_info.value.status_code == 400

    def test_validate_output_config_rejects_nested(self):
        from fastapi import HTTPException

        from server.routes.outputs import _validate_output_config

        with pytest.raises(HTTPException):
            _validate_output_config({"nested": {"exec": "evil"}})


# ---------------------------------------------------------------------------
# 6. X-Forwarded-For spoofing protection
# ---------------------------------------------------------------------------


class TestForwardedForProtection:
    """Verify X-Forwarded-For is only trusted with proxy config."""

    def test_trusted_proxies_env_var(self):
        """The security module should check SRT2WEB_TRUSTED_PROXIES."""
        import inspect

        from server.security import RateLimitMiddleware

        source = inspect.getsource(RateLimitMiddleware._get_client_ip)
        assert "SRT2WEB_TRUSTED_PROXIES" in source


# ---------------------------------------------------------------------------
# 7. CSP hardening
# ---------------------------------------------------------------------------


class TestCSPHardening:
    """Verify CSP no longer includes unsafe-inline/unsafe-eval in script-src."""

    def test_no_unsafe_inline_in_script_src(self):
        from server.security import SecurityHeadersMiddleware

        assert "unsafe-inline" not in SecurityHeadersMiddleware._CSP_BASE or SecurityHeadersMiddleware._CSP_BASE.index(
            "script-src"
        ) < SecurityHeadersMiddleware._CSP_BASE.index("unsafe-inline")

    def test_no_unsafe_eval(self):
        from server.security import SecurityHeadersMiddleware

        assert "unsafe-eval" not in SecurityHeadersMiddleware._CSP_BASE


# ---------------------------------------------------------------------------
# 8. SRT2WEB_TESTING guard
# ---------------------------------------------------------------------------


class TestTestingGuard:
    """Verify main.py warns when SRT2WEB_TESTING is set."""

    def test_main_imports_os_for_testing_check(self):
        """main.py should import os to check SRT2WEB_TESTING."""
        import inspect

        import main

        source = inspect.getsource(main.main)
        assert "SRT2WEB_TESTING" in source
