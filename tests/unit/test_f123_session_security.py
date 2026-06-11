"""
F123: Session security tests.

Tests for JWT token expiry, refresh token rotation, and token blacklist/revocation.
"""

import time
from unittest.mock import patch

import jwt as pyjwt
import pytest


def _clean_db():
    from core.auth_db import USERS_FILE

    if USERS_FILE.exists():
        USERS_FILE.unlink()


def _create_expired_token(sub: str = "admin", role: str = "admin") -> str:
    """Create a token that expired 1 hour ago for testing."""
    from core.auth_db import JWT_SECRET_KEY, JWT_ALGORITHM

    now = int(time.time())
    payload = {
        "sub": sub,
        "role": role,
        "type": "access",
        "iat": now - 7200,
        "exp": now - 3600,
        "jti": "expired-test-jti",
    }
    return pyjwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


class TestAccessToken:
    """Test access token generation and properties."""

    def setup_method(self):
        _clean_db()

    def teardown_method(self):
        _clean_db()

    def test_access_token_has_correct_type(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        token = db.authenticate("admin", "MyStr0ng!Pass")
        assert token is not None
        payload = db.decode_token(token)
        assert payload is not None
        assert payload.get("type") == "access"
        assert payload.get("sub") == "admin"
        assert payload.get("role") == "admin"

    def test_access_token_has_jti(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        token = db.authenticate("admin", "MyStr0ng!Pass")
        payload = db.decode_token(token)
        assert payload is not None
        assert "jti" in payload
        assert len(payload["jti"]) > 8

    def test_access_token_has_exp_claim(self):
        from core.auth_db import AuthDB, _ACCESS_TOKEN_MINUTES

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        token = db.authenticate("admin", "MyStr0ng!Pass")
        payload = pyjwt.decode(token, options={"verify_signature": False})
        assert "exp" in payload
        assert payload["exp"] > int(time.time())

    def test_expired_token_rejected(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        expired = _create_expired_token()
        assert db.decode_token(expired) is None

    def test_each_login_gets_different_jti(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        t1 = db.authenticate("admin", "MyStr0ng!Pass")
        t2 = db.authenticate("admin", "MyStr0ng!Pass")
        p1 = pyjwt.decode(t1, options={"verify_signature": False})
        p2 = pyjwt.decode(t2, options={"verify_signature": False})
        assert p1["jti"] != p2["jti"]


class TestRefreshToken:
    """Test refresh token generation and refresh endpoint."""

    def setup_method(self):
        _clean_db()

    def teardown_method(self):
        _clean_db()

    def _setup(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        return db

    def test_authenticate_full_returns_both_tokens(self):
        db = self._setup()
        result = db.authenticate_full("admin", "MyStr0ng!Pass")
        assert result is not None
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert result["access_token"] != result["refresh_token"]

    def test_refresh_token_has_correct_type(self):
        db = self._setup()
        result = db.authenticate_full("admin", "MyStr0ng!Pass")
        payload = db.decode_token(result["refresh_token"])
        assert payload is not None
        assert payload.get("type") == "refresh"
        assert payload.get("sub") == "admin"

    def test_refresh_token_has_long_expiry(self):
        from core.auth_db import _REFRESH_TOKEN_DAYS

        db = self._setup()
        result = db.authenticate_full("admin", "MyStr0ng!Pass")
        payload = pyjwt.decode(result["refresh_token"], options={"verify_signature": False})
        assert "exp" in payload
        assert payload["exp"] > int(time.time()) + (_REFRESH_TOKEN_DAYS - 1) * 86400

    def test_refresh_returns_new_token_pair(self):
        db = self._setup()
        result = db.authenticate_full("admin", "MyStr0ng!Pass")
        old_refresh = result["refresh_token"]
        old_access = result["access_token"]

        new_pair = db.refresh_token(old_refresh)
        assert new_pair is not None
        assert new_pair["access_token"] != old_access
        assert new_pair["refresh_token"] != old_refresh

    def test_old_refresh_revoked_after_rotation(self):
        db = self._setup()
        result = db.authenticate_full("admin", "MyStr0ng!Pass")
        old_refresh = result["refresh_token"]

        assert db.refresh_token(old_refresh) is not None
        assert db.refresh_token(old_refresh) is None

    def test_refresh_rejects_access_token(self):
        db = self._setup()
        result = db.authenticate_full("admin", "MyStr0ng!Pass")
        assert db.refresh_token(result["access_token"]) is None

    def test_refresh_rejects_expired_token(self):
        db = self._setup()
        expired = _create_expired_token()
        assert db.refresh_token(expired) is None

    def test_refresh_returns_new_valid_access_token(self):
        db = self._setup()
        result = db.authenticate_full("admin", "MyStr0ng!Pass")
        new_pair = db.refresh_token(result["refresh_token"])
        assert new_pair is not None
        payload = db.decode_token(new_pair["access_token"])
        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["type"] == "access"

    def test_refresh_for_disabled_user_returns_none(self):
        db = self._setup()
        result = db.authenticate_full("admin", "MyStr0ng!Pass")
        refresh = result["refresh_token"]
        db._users["admin"]["enabled"] = False
        assert db.refresh_token(refresh) is None

    def test_refresh_for_deleted_user_returns_none(self):
        db = self._setup()
        # Create a non-admin user so we can delete it
        db.create_user("operator1", "MyStr0ng!Pass", "operator")
        result = db.authenticate_full("operator1", "MyStr0ng!Pass")
        refresh = result["refresh_token"]
        db.delete_user("operator1")
        assert db.refresh_token(refresh) is None


class TestTokenBlacklist:
    """Test token blacklist and revocation."""

    def setup_method(self):
        _clean_db()

    def teardown_method(self):
        _clean_db()

    def test_revoke_token_returns_true(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        token = db.authenticate("admin", "MyStr0ng!Pass")
        assert db.revoke_token(token) is True

    def test_revoked_token_decode_returns_none(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        token = db.authenticate("admin", "MyStr0ng!Pass")
        assert db.decode_token(token) is not None
        db.revoke_token(token)
        assert db.decode_token(token) is None

    def test_revoke_invalid_token_returns_false(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        assert db.revoke_token("invalid-token") is False

    def test_revoke_expired_token_returns_false(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        expired = _create_expired_token()
        assert db.revoke_token(expired) is False

    def test_revoke_then_refresh_still_works(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        result = db.authenticate_full("admin", "MyStr0ng!Pass")
        db.revoke_token(result["access_token"])
        new_pair = db.refresh_token(result["refresh_token"])
        assert new_pair is not None

    def test_multiple_revoked_tokens(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")

        tokens = [db.authenticate("admin", "MyStr0ng!Pass") for _ in range(5)]
        for t in tokens:
            db.revoke_token(t)
        for t in tokens:
            assert db.decode_token(t) is None

    def test_unaffected_tokens_still_work(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")

        t1 = db.authenticate("admin", "MyStr0ng!Pass")
        t2 = db.authenticate("admin", "MyStr0ng!Pass")

        db.revoke_token(t1)
        assert db.decode_token(t1) is None
        assert db.decode_token(t2) is not None

    def test_revoke_returns_false_for_malformed_token(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        assert db.revoke_token("") is False
        assert db.revoke_token("abc.def") is False
        assert db.revoke_token("a.b.c") is False


class TestLogoutRoute:
    """Test that logout revokes the token via API."""

    def setup_method(self):
        _clean_db()

    def teardown_method(self):
        _clean_db()

    @pytest.fixture(autouse=True)
    def _setup_db(self):
        from core.auth_db import auth_db

        auth_db._users.clear()
        auth_db._blacklist.clear()
        auth_db.setup_first_admin("MyStr0ng!Pass")
        yield

    def test_logout_revokes_token(self):
        from core.auth_db import auth_db
        from server.routes.auth import logout

        from unittest.mock import MagicMock

        request = MagicMock()
        token = auth_db.authenticate("admin", "MyStr0ng!Pass")
        request.headers = {"Authorization": f"Bearer {token}"}

        assert auth_db.decode_token(token) is not None

        import asyncio

        asyncio.run(logout(request))

        assert auth_db.decode_token(token) is None

    def test_logout_without_token_does_not_crash(self):
        from server.routes.auth import logout

        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {}

        import asyncio

        result = asyncio.run(logout(request))
        assert result["status"] == "logged_out"


class TestRefreshRoute:
    """Test the POST /auth/refresh endpoint."""

    def setup_method(self):
        _clean_db()

    def teardown_method(self):
        _clean_db()

    @pytest.fixture(autouse=True)
    def _setup_db(self):
        from core.auth_db import auth_db

        auth_db._users.clear()
        auth_db._blacklist.clear()
        auth_db.setup_first_admin("MyStr0ng!Pass")
        yield

    def test_refresh_route_returns_new_tokens(self):
        from core.auth_db import auth_db
        from server.routes.auth import refresh_token, RefreshTokenRequest

        result = auth_db.authenticate_full("admin", "MyStr0ng!Pass")
        import asyncio

        response = asyncio.run(refresh_token(RefreshTokenRequest(refresh_token=result["refresh_token"])))
        assert "access_token" in response
        assert "refresh_token" in response
        assert response["token_type"] == "bearer"

    def test_refresh_route_rejects_invalid_token(self):
        from fastapi import HTTPException
        from server.routes.auth import refresh_token, RefreshTokenRequest

        import asyncio

        with pytest.raises(HTTPException) as exc:
            asyncio.run(refresh_token(RefreshTokenRequest(refresh_token="invalid")))
        assert exc.value.status_code == 401

    def test_refresh_route_rejects_reused_token(self):
        from fastapi import HTTPException
        from core.auth_db import auth_db
        from server.routes.auth import refresh_token, RefreshTokenRequest

        result = auth_db.authenticate_full("admin", "MyStr0ng!Pass")
        import asyncio

        resp1 = asyncio.run(refresh_token(RefreshTokenRequest(refresh_token=result["refresh_token"])))
        assert "access_token" in resp1

        with pytest.raises(HTTPException) as exc:
            asyncio.run(refresh_token(RefreshTokenRequest(refresh_token=result["refresh_token"])))
        assert exc.value.status_code == 401


class TestLoginRouteTokens:
    """Test that login route returns both tokens."""

    def setup_method(self):
        _clean_db()

    def teardown_method(self):
        _clean_db()

    @pytest.fixture(autouse=True)
    def _setup_db(self):
        from core.auth_db import auth_db

        auth_db._users.clear()
        auth_db._blacklist.clear()
        auth_db.setup_first_admin("MyStr0ng!Pass")
        yield

    def test_login_returns_access_and_refresh(self):
        from server.routes.auth import login, LoginRequest
        import asyncio

        result = asyncio.run(login(LoginRequest(username="admin", password="MyStr0ng!Pass")))
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert "user" in result

    def test_setup_returns_both_tokens(self):
        from core.auth_db import auth_db

        auth_db._users.clear()
        auth_db._blacklist.clear()

        from server.routes.auth import setup_first_admin, LoginRequest
        import asyncio

        result = asyncio.run(setup_first_admin(LoginRequest(username="admin", password="MyStr0ng!Pass")))
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
