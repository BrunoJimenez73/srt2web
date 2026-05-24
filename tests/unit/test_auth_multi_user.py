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


class TestAuthDB:
    def test_default_admin_created(self) -> None:
        """Default admin user should be auto-created."""
        from core.auth_db import auth_db

        user = auth_db.get_user("admin")
        assert user is not None
        assert user["role"] == "admin"

    def test_authenticate_valid(self) -> None:
        """Valid credentials should return a JWT token."""
        from core.auth_db import auth_db

        token = auth_db.authenticate("admin", "admin")
        assert token is not None
        decoded = auth_db.decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "admin"

    def test_authenticate_invalid_password(self) -> None:
        """Invalid password should return None."""
        from core.auth_db import auth_db

        assert auth_db.authenticate("admin", "wrong") is None

    def test_authenticate_nonexistent_user(self) -> None:
        """Non-existent user should return None."""
        from core.auth_db import auth_db

        assert auth_db.authenticate("nobody", "pwd") is None

    def test_create_and_authenticate_user(self) -> None:
        """Create a user then authenticate."""
        from core.auth_db import auth_db

        assert auth_db.create_user("testuser", "test123", "viewer")
        token = auth_db.authenticate("testuser", "test123")
        assert token is not None
        assert auth_db.decode_token(token)["role"] == "viewer"

    def test_duplicate_user(self) -> None:
        """Creating duplicate user returns False."""
        from core.auth_db import auth_db

        assert not auth_db.create_user("admin", "x")  # already exists

    def test_delete_user(self) -> None:
        """Delete a non-admin user."""
        from core.auth_db import auth_db

        auth_db.create_user("tempuser", "pwd", "viewer")
        assert auth_db.delete_user("tempuser")
        assert auth_db.get_user("tempuser") is None

    def test_cannot_delete_admin(self) -> None:
        """Admin user cannot be deleted."""
        from core.auth_db import auth_db

        assert not auth_db.delete_user("admin")

    def test_update_role(self) -> None:
        """Update user role."""
        from core.auth_db import auth_db

        auth_db.create_user("user1", "pwd", "viewer")
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


class TestAuthAPI:
    @pytest.fixture
    def client(self) -> TestClient:
        from server.app import create_app

        app = create_app({"config": None, "pipeline": None, "input_source": None, "log_broadcast": None})
        return TestClient(app)

    def test_login_valid(self, client: TestClient) -> None:
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"

    def test_login_invalid(self, client: TestClient) -> None:
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_missing_fields(self, client: TestClient) -> None:
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 422  # Validation error

    def test_me_with_token(self, client: TestClient) -> None:
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        token = login.json()["token"]
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_me_without_token(self, client: TestClient) -> None:
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_register_admin_only(self, client: TestClient) -> None:
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        token = login.json()["token"]
        resp = client.post(
            "/api/auth/register",
            json={"username": "op1", "password": "pass123", "role": "operator"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        # Verify can login as new user
        resp2 = client.post("/api/auth/login", json={"username": "op1", "password": "pass123"})
        assert resp2.status_code == 200
