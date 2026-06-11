"""
F122: Account lockout tests.

Tests that after _MAX_FAILED_ATTEMPTS (5) failed logins within a window,
the account is locked for _LOCKOUT_DURATION_SECONDS (30 min).
"""

import time
from unittest.mock import patch

import pytest


def _make_db():
    """Create a fresh AuthDB with a user for testing."""
    from core.auth_db import AuthDB

    db = AuthDB()
    # Ensure we have a user
    if not db.has_users():
        db.setup_first_admin("MyStr0ng!Pass")
    return db


class TestIsLocked:
    """Unit tests for AuthDB.is_locked()."""

    def teardown_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def test_is_locked_returns_false_for_unknown_user(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        assert db.is_locked("nonexistent") is False

    def test_is_locked_returns_false_for_unlocked_user(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        assert db.is_locked("admin") is False


class TestLockoutAfterFailures:
    """Test that account locks after _MAX_FAILED_ATTEMPTS failures."""

    def setup_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def teardown_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def _make(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        return db

    def test_lockout_after_5_failed_attempts(self):
        db = self._make()
        PASSWORD = "MyStr0ng!Pass"

        # 5 failed attempts should lock the account
        for i in range(5):
            token = db.authenticate("admin", "WrongPass1!")
            assert token is None, f"Attempt {i+1} should fail"
            if i < 4:
                assert db.is_locked("admin") is False, f"Not locked yet at attempt {i+1}"
            else:
                assert db.is_locked("admin") is True, "Should be locked after 5 attempts"

    def test_lock_prevents_successful_login(self):
        db = self._make()
        PASSWORD = "MyStr0ng!Pass"

        for _ in range(5):
            db.authenticate("admin", "WrongPass1!")
        assert db.is_locked("admin") is True

        # Even correct password should be rejected while locked
        token = db.authenticate("admin", PASSWORD)
        assert token is None

    def test_successful_login_before_lock_resets_counter(self):
        db = self._make()
        PASSWORD = "MyStr0ng!Pass"

        # 3 failures, then success
        for _ in range(3):
            db.authenticate("admin", "WrongPass1!")
        assert db.is_locked("admin") is False

        token = db.authenticate("admin", PASSWORD)
        assert token is not None

        # Counter reset; another 5 failures needed to lock
        for _ in range(5):
            db.authenticate("admin", "WrongPass1!")
        assert db.is_locked("admin") is True

    def test_different_user_not_affected(self):
        db = self._make()
        db.create_user("user2", "MyStr0ng!Pass", "viewer")

        # Lock admin
        for _ in range(5):
            db.authenticate("admin", "WrongPass1!")
        assert db.is_locked("admin") is True
        assert db.is_locked("user2") is False

    def test_unlock_user_works(self):
        db = self._make()
        PASSWORD = "MyStr0ng!Pass"

        for _ in range(5):
            db.authenticate("admin", "WrongPass1!")
        assert db.is_locked("admin") is True

        ok = db.unlock_user("admin")
        assert ok is True
        assert db.is_locked("admin") is False

        # Can login after unlock
        token = db.authenticate("admin", PASSWORD)
        assert token is not None

    def test_unlock_unknown_user_returns_false(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        assert db.unlock_user("nonexistent") is False

    def test_change_password_resets_lockout(self):
        db = self._make()
        PASSWORD = "MyStr0ng!Pass"

        for _ in range(5):
            db.authenticate("admin", "WrongPass1!")
        assert db.is_locked("admin") is True

        # Change password should reset lockout
        db.change_password("admin", PASSWORD, "N3wStr0ng!Pass")
        assert db.is_locked("admin") is False

        # New password works
        token = db.authenticate("admin", "N3wStr0ng!Pass")
        assert token is not None


class TestLockoutAutoExpiry:
    """Test that lockout auto-expires after _LOCKOUT_DURATION_SECONDS."""

    def setup_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def teardown_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def test_auto_expiry_after_duration(self):
        """Use mocked time to verify lockout expires."""
        from core.auth_db import AuthDB, _LOCKOUT_DURATION_SECONDS

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        PASSWORD = "MyStr0ng!Pass"
        now = time.time()

        with patch("time.time") as mock_time:
            # Start at a fixed point
            mock_time.return_value = now

            # Trigger lockout
            for _ in range(5):
                db.authenticate("admin", "WrongPass1!")
            assert db.is_locked("admin") is True

            # Jump forward past lockout duration
            mock_time.return_value = now + _LOCKOUT_DURATION_SECONDS + 1

            # Lock should be auto-expired now — authenticate resets it
            assert db.is_locked("admin") is False

            # Can login again
            token = db.authenticate("admin", PASSWORD)
            assert token is not None

    def test_partial_time_not_enough(self):
        """Just before expiry, account is still locked."""
        from core.auth_db import AuthDB, _LOCKOUT_DURATION_SECONDS

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        PASSWORD = "MyStr0ng!Pass"
        now = time.time()

        with patch("time.time") as mock_time:
            mock_time.return_value = now

            for _ in range(5):
                db.authenticate("admin", "WrongPass1!")
            assert db.is_locked("admin") is True

            # Jump forward halfway through lockout — still locked
            mock_time.return_value = now + _LOCKOUT_DURATION_SECONDS // 2
            assert db.is_locked("admin") is True

            # authenticate still rejects
            token = db.authenticate("admin", PASSWORD)
            assert token is None


class TestLoginRoute:
    """Integration tests for the login route returning 423."""

    def setup_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def teardown_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    @pytest.fixture(autouse=True)
    def _setup_db(self):
        from core.auth_db import auth_db

        auth_db._users.clear()
        auth_db.setup_first_admin("MyStr0ng!Pass")
        yield

    def test_login_returns_423_when_locked(self):
        from fastapi import HTTPException
        from server.routes.auth import login
        from server.routes.auth import LoginRequest

        # Lock the account
        auth_db = pytest.importorskip("core.auth_db").auth_db
        for _ in range(5):
            auth_db.authenticate("admin", "WrongPass1!")

        with pytest.raises(HTTPException) as exc:
            import asyncio

            asyncio.run(login(LoginRequest(username="admin", password="MyStr0ng!Pass")))
        assert exc.value.status_code == 423
        assert "locked" in exc.value.detail.lower()

    def test_login_returns_401_for_wrong_password(self):
        from fastapi import HTTPException
        from server.routes.auth import login
        from server.routes.auth import LoginRequest

        with pytest.raises(HTTPException) as exc:
            import asyncio

            asyncio.run(login(LoginRequest(username="admin", password="WrongPass1!")))
        assert exc.value.status_code == 401

    def test_login_returns_token_for_correct_password(self):
        from server.routes.auth import login
        from server.routes.auth import LoginRequest

        import asyncio

        result = asyncio.run(login(LoginRequest(username="admin", password="MyStr0ng!Pass")))
        assert "token" in result
        assert result["token"] is not None


class TestUnlockRoute:
    """Test the POST /auth/users/{username}/unlock endpoint."""

    def setup_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def teardown_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    @pytest.fixture(autouse=True)
    def _setup_db(self):
        from core.auth_db import auth_db

        auth_db._users.clear()
        auth_db.setup_first_admin("MyStr0ng!Pass")
        yield

    def _make_request_with_admin_role(self):
        """Create a mock Request with admin JWT."""
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {"Authorization": "Bearer dummy"}
        return request

    def _make_token(self, username="admin", role="admin"):
        """Generate a valid JWT for testing."""
        from core.auth_db import auth_db

        with patch.object(auth_db, "decode_token", return_value={"sub": username, "role": role}):
            return auth_db.decode_token

    def test_unlock_endpoint_returns_404_for_unknown_user(self):
        from fastapi import HTTPException
        from server.routes.auth import unlock_user

        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {"Authorization": "Bearer dummy"}

        with patch("server.routes.auth._get_auth_db") as mock_get_db:
            mock_db = mock_get_db.return_value
            mock_db.decode_token.return_value = {"sub": "admin", "role": "admin"}
            mock_db.has_permission.return_value = True
            mock_db.unlock_user.return_value = False

            with pytest.raises(HTTPException) as exc:
                import asyncio

                asyncio.run(unlock_user("nonexistent", request))
            assert exc.value.status_code == 404

    def test_unlock_endpoint_returns_403_for_non_admin(self):
        from fastapi import HTTPException
        from server.routes.auth import unlock_user

        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {"Authorization": "Bearer dummy"}

        with patch("server.routes.auth._get_auth_db") as mock_get_db:
            mock_db = mock_get_db.return_value
            mock_db.decode_token.return_value = {"sub": "viewer", "role": "viewer"}
            mock_db.has_permission.return_value = False

            with pytest.raises(HTTPException) as exc:
                import asyncio

                asyncio.run(unlock_user("admin", request))
            assert exc.value.status_code == 403

    def test_unlock_endpoint_success(self):
        from server.routes.auth import unlock_user

        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {"Authorization": "Bearer dummy"}

        with patch("server.routes.auth._get_auth_db") as mock_get_db:
            mock_db = mock_get_db.return_value
            mock_db.decode_token.return_value = {"sub": "admin", "role": "admin"}
            mock_db.has_permission.return_value = True
            mock_db.unlock_user.return_value = True

            import asyncio

            result = asyncio.run(unlock_user("admin", request))
            assert result["status"] == "unlocked"
            assert result["username"] == "admin"


class TestCreateUserLockoutFields:
    """Test that new users include lockout tracking fields."""

    def setup_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def teardown_method(self):
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def test_new_user_has_lockout_fields(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        db.create_user("user2", "MyStr0ng!Pass", "viewer")
        user = db.get_user("user2")
        assert user is not None
        assert "failed_attempts" in user
        assert user["failed_attempts"] == 0
        assert "locked_until" in user
        assert user["locked_until"] == 0.0
