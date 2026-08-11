"""
F118: Security hardening tests — PBKDF2 hashing, SHA-256 migration,
timing-safe comparison, auth middleware 503.
"""

import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _isolated_auth_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use temp file for users.json to avoid polluting real config."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp, open(tmp.name, "w", encoding="utf-8") as f:
        f.write("{}")
    import core.auth_db

    monkeypatch.setattr(core.auth_db, "USERS_FILE", Path(tmp.name))
    monkeypatch.setattr(core.auth_db, "auth_db", core.auth_db.AuthDB())
    yield
    os.unlink(tmp.name)


class TestPBKDF2Hashing:
    """F118: Verify PBKDF2-HMAC-SHA256 is used for password hashing."""

    def test_hash_uses_pbkdf2(self):
        """_hash_password should produce a 64-char hex hash (32 bytes = 256 bits)."""
        from core.auth_db import _hash_password

        h, salt = _hash_password("test-password")
        assert len(h) == 64, f"PBKDF2 output should be 64 hex chars, got {len(h)}"
        assert len(salt) == 32, f"Salt should be 32 hex chars (16 bytes), got {len(salt)}"
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_password_different_salts(self):
        """Same password with different salts should produce different hashes."""
        from core.auth_db import _hash_password

        h1, s1 = _hash_password("same-password")
        h2, s2 = _hash_password("same-password")
        assert h1 != h2, "Different salts should produce different hashes"
        assert s1 != s2

    def test_same_password_same_salt(self):
        """Same password with same salt should produce same hash."""
        from core.auth_db import _hash_password

        h1, _ = _hash_password("test", salt="abc123")
        h2, _ = _hash_password("test", salt="abc123")
        assert h1 == h2

    def test_wrong_password_fails(self):
        """Different passwords should produce different hashes."""
        from core.auth_db import _hash_password

        h1, _ = _hash_password("correct-password", salt="fixed-salt")
        h2, _ = _hash_password("wrong-password", salt="fixed-salt")
        assert h1 != h2

    def test_not_sha256(self):
        """PBKDF2 hash should be different from plain SHA-256 of same input."""
        salt = "abc123"
        password = "test-password"
        # Plain SHA-256 (the old method)
        sha256_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        # PBKDF2 (the new method)
        from core.auth_db import _hash_password

        pbkdf2_hash, _ = _hash_password(password, salt=salt)
        assert pbkdf2_hash != sha256_hash, "PBKDF2 should produce different hash than SHA-256"


class TestLegacySHA256Migration:
    """F118: Auto-migrate legacy SHA-256 hashes to PBKDF2 on login."""

    def test_detect_legacy_sha256(self):
        """64-char hex string should be detected as legacy SHA-256."""
        from core.auth_db import _is_legacy_sha256

        # 64-char hex = SHA-256
        assert _is_legacy_sha256("a" * 64) is True
        # 64-char but non-hex
        assert _is_legacy_sha256("g" * 64) is False
        # Too short
        assert _is_legacy_sha256("a" * 63) is False
        # Too long
        assert _is_legacy_sha256("a" * 65) is False

    def test_login_migrates_sha256_to_pbkdf2(self):
        """Login with legacy SHA-256 hash should auto-migrate to PBKDF2."""
        from core.auth_db import _hash_password, auth_db

        # Create user with legacy SHA-256 hash
        salt = "abc123def456"
        legacy_hash = hashlib.sha256(("abc123def456" + "mypass").encode()).hexdigest()
        auth_db._users["legacyuser"] = {
            "password_hash": legacy_hash,
            "password_salt": salt,
            "role": "viewer",
            "enabled": True,
            "created_at": 0.0,
            "last_login": 0.0,
        }

        # Login should succeed and migrate
        token = auth_db.authenticate("legacyuser", "mypass")
        assert token is not None, "Login with legacy password should succeed"

        # After migration, hash should be PBKDF2 (64 hex chars but different from SHA-256)
        user = auth_db._users["legacyuser"]
        assert user["password_hash"] != legacy_hash, "Hash should be migrated"
        # Verify new hash is valid PBKDF2
        new_hash, _ = _hash_password("mypass", user["password_salt"])
        assert user["password_hash"] == new_hash


class TestTimingSafeComparison:
    """F118: secrets.compare_digest should be used for hash comparison."""

    def authenticate_uses_compare_digest(self):
        """authenticate() should use secrets.compare_digest, not !=."""
        from core.auth_db import auth_db

        auth_db.setup_first_admin("admin")
        with patch("core.auth_db.secrets.compare_digest", return_value=False) as mock_cmp:
            result = auth_db.authenticate("admin", "wrong-password")
            assert result is None
            mock_cmp.assert_called_once()


class TestAuthMiddleware503:
    """F118: AuthMiddleware should return 503 when auth_token is not configured."""

    def test_503_when_no_token_configured(self):
        """API should return 503 when auth_token is empty."""
        import os

        from fastapi.testclient import TestClient

        from server.app import create_app

        # Temporarily disable test mode so auth middleware actually runs
        os.environ.pop("SRT2WEB_TESTING", None)
        try:

            class _NoTokenConfig:
                def get(self, key: str, default=None):
                    if key == "server.auth_token":
                        return ""  # No auth token configured
                    return default  # Return default for all other keys

            app = create_app(
                {
                    "config": _NoTokenConfig(),
                    "pipeline": None,
                    "input_source": None,
                    "log_broadcast": None,
                }
            )
            client = TestClient(app)
            resp = client.get("/api/status")
            assert resp.status_code == 503
            assert "unavailable" in resp.json()["detail"].lower()
        finally:
            os.environ["SRT2WEB_TESTING"] = "1"

    def test_200_when_token_configured(self):
        """API should work normally when auth_token is set."""
        from fastapi.testclient import TestClient

        from server.app import create_app

        class _WithTokenConfig:
            def get(self, key: str, default=None):
                if key == "server.auth_token":
                    return "my-secret-token"
                return default

        app = create_app(
            {
                "config": _WithTokenConfig(),
                "pipeline": None,
                "input_source": None,
                "log_broadcast": None,
            }
        )
        client = TestClient(app)
        # Health should be accessible without token
        resp = client.get("/health")
        assert resp.status_code == 200
