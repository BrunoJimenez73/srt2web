import json
import os
import tempfile

import jwt
import pytest

from core.database import (
    UserRole,
    create_user,
    delete_user,
    get_user,
    has_users,
    init_db,
    list_users,
    verify_user,
)


@pytest.fixture(autouse=True)
def setup_db():
    import core.database as db
    test_db = tempfile.mktemp(suffix=".db")
    db.DB_PATH = test_db
    db._local.conn = None
    init_db()
    yield
    try:
        os.remove(test_db)
    except OSError:
        pass


class TestUserRole:
    def test_hierarchy(self) -> None:
        assert UserRole.has_permission("admin", "viewer")
        assert UserRole.has_permission("admin", "operator")
        assert UserRole.has_permission("admin", "admin")
        assert UserRole.has_permission("operator", "viewer")
        assert not UserRole.has_permission("viewer", "operator")
        assert not UserRole.has_permission("viewer", "admin")

    def test_all_roles(self) -> None:
        assert "admin" in UserRole.ALL
        assert "operator" in UserRole.ALL
        assert "viewer" in UserRole.ALL


class TestDatabase:
    def test_init_db_creates_table(self) -> None:
        assert has_users() is False

    def test_create_user(self) -> None:
        result = create_user("testuser", "testpass", "viewer")
        assert result["username"] == "testuser"
        assert result["role"] == "viewer"

    def test_create_duplicate_user(self) -> None:
        create_user("dup", "pass1", "viewer")
        with pytest.raises(ValueError):
            create_user("dup", "pass2", "viewer")

    def test_verify_user_valid(self) -> None:
        create_user("alice", "secret", "operator")
        result = verify_user("alice", "secret")
        assert result is not None
        assert result["username"] == "alice"
        assert result["role"] == "operator"

    def test_verify_user_wrong_password(self) -> None:
        create_user("bob", "correct", "viewer")
        result = verify_user("bob", "wrong")
        assert result is None

    def test_verify_user_nonexistent(self) -> None:
        result = verify_user("nonexistent", "pass")
        assert result is None

    def test_get_user(self) -> None:
        create_user("charlie", "pass", "admin")
        user = get_user("charlie")
        assert user is not None
        assert user["username"] == "charlie"
        assert user["role"] == "admin"

    def test_list_users(self) -> None:
        create_user("u1", "p1", "admin")
        create_user("u2", "p2", "viewer")
        users = list_users()
        assert len(users) == 2

    def test_delete_user(self) -> None:
        create_user("temp", "pass", "viewer")
        delete_user("temp")
        assert get_user("temp") is None

    def test_create_user_invalid_role_defaults_to_viewer(self) -> None:
        result = create_user("badrole", "pass", "superadmin")
        assert result["role"] == "viewer"


class TestJWTAuth:
    SECRET = "test-secret-key-for-testing-only-min-length-ok"

    def test_token_creation(self) -> None:
        payload = {"sub": "admin", "role": "admin", "iat": 0, "exp": 9999999999}
        token = jwt.encode(payload, self.SECRET, algorithm="HS256")
        decoded = jwt.decode(token, self.SECRET, algorithms=["HS256"])
        assert decoded["sub"] == "admin"
        assert decoded["role"] == "admin"

    def test_expired_token(self) -> None:
        import time
        payload = {"sub": "user", "role": "viewer", "iat": 0, "exp": int(time.time()) - 1}
        token = jwt.encode(payload, self.SECRET, algorithm="HS256")
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, self.SECRET, algorithms=["HS256"])

    def test_invalid_signature(self) -> None:
        payload = {"sub": "user", "role": "viewer", "iat": 0, "exp": 9999999999}
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, self.SECRET, algorithms=["HS256"])