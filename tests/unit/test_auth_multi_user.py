"""
Tests for multi-user authentication system.
"""

import os
import tempfile
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def users_file() -> Path:
    """Use a temp file for users.json to avoid polluting real config."""
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.write(b"{}")
    tmp.close()
    yield Path(tmp.name)
    os.unlink(tmp.name)


@pytest.fixture(autouse=True)
def override_users_file(users_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Override USERS_FILE in auth_db module."""
    import core.auth_db

    monkeypatch.setattr(core.auth_db, "USERS_FILE", users_file)
    # Reset singleton
    monkeypatch.setattr(core.auth_db, "auth_db", core.auth_db.AuthDB())


_TEST_PASSWORD = "T3st!Str0ngP@ss"


@pytest.fixture
def seeded_admin() -> None:
    """F120: Create admin user for tests that need it."""
    from core.auth_db import auth_db

    auth_db.setup_first_admin(_TEST_PASSWORD)


class TestAuthDB:
    def test_default_admin_created(self, seeded_admin: None) -> None:
        """F120: setup_first_admin creates the admin user."""
        from core.auth_db import auth_db

        user = auth_db.get_user("admin")
        assert user is not None
        assert user["role"] == "admin"

    def test_setup_first_admin_only_once(self) -> None:
        """F120: setup_first_admin returns (False, msg) if users already exist."""
        from core.auth_db import auth_db

        ok1, _ = auth_db.setup_first_admin("Pass1!Str0ng")
        assert ok1 is True
        ok2, _ = auth_db.setup_first_admin("Pass2!Str0ng")
        assert ok2 is False

    def test_authenticate_valid(self, seeded_admin: None) -> None:
        """Valid credentials should return a JWT token."""
        from core.auth_db import auth_db

        token = auth_db.authenticate("admin", _TEST_PASSWORD)
        assert token is not None
        decoded = auth_db.decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "admin"

    def test_authenticate_invalid_password(self, seeded_admin: None) -> None:
        """Invalid password should return None."""
        from core.auth_db import auth_db

        assert auth_db.authenticate("admin", "wrong") is None

    def test_authenticate_nonexistent_user(self) -> None:
        """Non-existent user should return None."""
        from core.auth_db import auth_db

        assert auth_db.authenticate("nobody", "pwd") is None

    def test_create_and_authenticate_user(self, seeded_admin: None) -> None:
        """Create a user then authenticate."""
        from core.auth_db import auth_db

        ok, _ = auth_db.create_user("testuser", "T3st!Str0ng", "viewer")
        assert ok is True
        token = auth_db.authenticate("testuser", "T3st!Str0ng")
        assert token is not None
        assert auth_db.decode_token(token)["role"] == "viewer"

    def test_duplicate_user(self, seeded_admin: None) -> None:
        """Creating duplicate user returns False."""
        from core.auth_db import auth_db

        ok, _ = auth_db.create_user("admin", "X!Str0ng1", "viewer")
        assert ok is False  # already exists

    def test_delete_user(self, seeded_admin: None) -> None:
        """Delete a non-admin user."""
        from core.auth_db import auth_db

        ok, _ = auth_db.create_user("tempuser", "Pwd!Str0ng1", "viewer")
        assert ok is True
        assert auth_db.delete_user("tempuser")
        assert auth_db.get_user("tempuser") is None

    def test_cannot_delete_last_admin(self, seeded_admin: None) -> None:
        """F120: Last admin cannot be deleted."""
        from core.auth_db import auth_db

        assert not auth_db.delete_user("admin")

    def test_can_delete_admin_if_other_admin_exists(self, seeded_admin: None) -> None:
        """F120: Can delete admin if another admin exists."""
        from core.auth_db import auth_db

        ok, _ = auth_db.create_user("admin2", "P4ss!Str0ng", "admin")
        assert ok is True
        assert auth_db.delete_user("admin")
        assert auth_db.get_user("admin") is None
        assert auth_db.get_user("admin2") is not None

    def test_has_users_false_when_empty(self) -> None:
        """F120: has_users returns False when no users."""
        from core.auth_db import auth_db

        assert not auth_db.has_users()

    def test_has_users_true_after_setup(self, seeded_admin: None) -> None:
        """F120: has_users returns True after setup."""
        from core.auth_db import auth_db

        assert auth_db.has_users()

    def test_env_var_creates_admin(self, users_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """F120: SRT2WEB_ADMIN_PASSWORD env var auto-creates admin."""
        import core.auth_db

        monkeypatch.setenv("SRT2WEB_ADMIN_PASSWORD", "Env4dm!Str0ng")
        monkeypatch.setattr(core.auth_db, "USERS_FILE", users_file)
        monkeypatch.setattr(core.auth_db, "auth_db", core.auth_db.AuthDB())
        user = core.auth_db.auth_db.get_user("admin")
        assert user is not None
        assert user["role"] == "admin"
        token = core.auth_db.auth_db.authenticate("admin", "Env4dm!Str0ng")
        assert token is not None

    def test_update_role(self) -> None:
        """Update user role."""
        from core.auth_db import auth_db

        ok, _ = auth_db.create_user("user1", "Pwd!Str0ng1", "viewer")
        assert ok is True
        assert auth_db.update_role("user1", "operator")
        assert auth_db.get_user("user1")["role"] == "operator"

    def test_has_permission(self) -> None:
        """Role hierarchy: admin > operator > viewer."""
        from core.auth_db import auth_db

        assert auth_db.has_permission("admin", "admin")
        assert auth_db.has_permission("admin", "operator")
        assert auth_db.has_permission("operator", "viewer")
        assert not auth_db.has_permission("viewer", "operator")
        assert not auth_db.has_permission("operator", "admin")

    def test_expired_token(self) -> None:
        """Expired token should return None."""
        import time

        from core.auth_db import JWT_ALGORITHM, JWT_SECRET_KEY, auth_db

        expired = jwt.encode(
            {"sub": "admin", "role": "admin", "exp": int(time.time()) - 3600},
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        assert auth_db.decode_token(expired) is None


@pytest.fixture
def _client_factory() -> TestClient:
    """Create a test client with mock config."""
    from server.app import create_app

    class _MockConfig:
        def get(self, key, default=None):
            if key == "server.auth_token":
                return "test-token-12345"
            return default

    app = create_app({"config": _MockConfig(), "pipeline": None, "input_source": None, "log_broadcast": None})
    return TestClient(app)


class TestAuthAPI:
    """F120: API tests WITH admin seeded via setup_first_admin by the first test that logs in."""

    @pytest.fixture
    def client(self, _client_factory: TestClient) -> TestClient:
        return _client_factory

    def test_login_valid_setup_first(self, client: TestClient) -> None:
        """Login works after setup_first_admin."""
        resp = client.post("/api/auth/setup", json={"username": "admin", "password": "Adm1n!Str0ng"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_login_invalid(self, client: TestClient) -> None:
        """Invalid login returns 401 even without seed (no admin exists)."""
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_missing_fields(self, client: TestClient) -> None:
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 422  # Validation error

    def test_me_without_token(self, client: TestClient) -> None:
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


class TestAuthSetup:
    """F120: Setup endpoint tests — no admin pre-seeded."""

    @pytest.fixture
    def client(self, _client_factory: TestClient) -> TestClient:
        return _client_factory

    def test_setup_endpoint_returns_needs_setup_true(self, client: TestClient) -> None:
        """GET /api/auth/setup returns needs_setup=true before any seeding."""
        resp = client.get("/api/auth/setup")
        assert resp.status_code == 200
        assert resp.json()["needs_setup"] is True

    def test_setup_endpoint_creates_admin(self, client: TestClient) -> None:
        """POST /api/auth/setup creates admin and returns token."""
        resp = client.post("/api/auth/setup", json={"username": "admin", "password": "Adm1n!Str0ng"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        # After setup, POST /api/auth/setup should be rejected
        resp2 = client.post("/api/auth/setup", json={"username": "admin", "password": "Other!Str0ng"})
        assert resp2.status_code == 400
        # GET should reflect that
        resp3 = client.get("/api/auth/setup")
        assert resp3.json()["needs_setup"] is False

    def test_setup_endpoint_already_exists_rejected(self, client: TestClient) -> None:
        """POST /api/auth/setup returns 400 after setup is done (password validation or already exists)."""
        client.post("/api/auth/setup", json={"username": "admin", "password": "Adm1n!Str0ng"})
        resp = client.post("/api/auth/setup", json={"username": "admin", "password": "Other!Str0ng"})
        assert resp.status_code == 400

    def test_login_fails_before_setup(self, client: TestClient) -> None:
        """Login returns 401 if no admin exists."""
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "Adm1n!Str0ng"})
        assert resp.status_code == 401
