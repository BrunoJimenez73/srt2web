"""
F121: Password policy tests.

Validates that validate_password_strength() enforces:
- Minimum 8 characters
- At least 1 uppercase, 1 lowercase, 1 digit, 1 special character
- Rejects common passwords (top-100 list)
- Integration with create_user, setup_first_admin, change_password
"""

import pytest


class TestValidatePasswordStrength:
    """Unit tests for validate_password_strength()."""

    def test_valid_password(self):
        from core.auth_db import validate_password_strength

        ok, msg = validate_password_strength("MyStr0ng!Pass")
        assert ok is True
        assert "válida" in msg.lower()

    def test_too_short(self):
        from core.auth_db import validate_password_strength

        ok, msg = validate_password_strength("Ab1!")
        assert ok is False
        assert "8 caracteres" in msg

    def test_no_uppercase(self):
        from core.auth_db import validate_password_strength

        ok, msg = validate_password_strength("mystr0ng!pass")
        assert ok is False
        assert "mayúscula" in msg

    def test_no_lowercase(self):
        from core.auth_db import validate_password_strength

        ok, msg = validate_password_strength("MYSTR0NG!PASS")
        assert ok is False
        assert "minúscula" in msg

    def test_no_digit(self):
        from core.auth_db import validate_password_strength

        ok, msg = validate_password_strength("MyStrong!Pass")
        assert ok is False
        assert "dígito" in msg

    def test_no_special_char(self):
        from core.auth_db import validate_password_strength

        ok, msg = validate_password_strength("MyStr0ngPass")
        assert ok is False
        assert "especial" in msg

    def test_common_password_rejected(self):
        from core.auth_db import validate_password_strength

        # "password" is in the common list
        ok, msg = validate_password_strength("password")
        assert ok is False
        assert "común" in msg.lower()

    def test_common_password_123456(self):
        from core.auth_db import validate_password_strength

        # "123456" is in the common list
        ok, msg = validate_password_strength("123456")
        assert ok is False
        assert "común" in msg.lower()

    def test_special_chars_accepted(self):
        from core.auth_db import validate_password_strength

        for special in "!@#$%^&*":
            ok, _ = validate_password_strength(f"Test123{special}")
            assert ok is True, f"Character '{special}' should be accepted"

    def test_exact_8_chars_valid(self):
        from core.auth_db import validate_password_strength

        ok, _ = validate_password_strength("Abcdef1!")
        assert ok is True

    def test_7_chars_invalid(self):
        from core.auth_db import validate_password_strength

        ok, msg = validate_password_strength("Abcdef1")
        assert ok is False
        assert "8 caracteres" in msg


class TestPasswordPolicyIntegration:
    """Integration tests: password policy applied in create_user, setup_first_admin, change_password."""

    def setup_method(self):
        """Clean up users.json before each test."""
        import json
        from pathlib import Path

        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def teardown_method(self):
        """Clean up after tests."""
        from core.auth_db import USERS_FILE

        if USERS_FILE.exists():
            USERS_FILE.unlink()

    def test_create_user_weak_password_rejected(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        ok, msg = db.create_user("testuser", "weak")
        assert ok is False
        assert "8 caracteres" in msg

    def test_create_user_strong_password_accepted(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        ok, msg = db.create_user("testuser", "MyStr0ng!Pass")
        assert ok is True
        assert "created" in msg.lower()

    def test_setup_first_admin_weak_password_rejected(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        ok, msg = db.setup_first_admin("admin")
        assert ok is False
        assert "común" in msg.lower() or "8 caracteres" in msg

    def test_setup_first_admin_strong_password_accepted(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        ok, msg = db.setup_first_admin("MyStr0ng!Pass")
        assert ok is True

    def test_change_password_weak_rejected(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        ok, msg = db.change_password("admin", "MyStr0ng!Pass", "weak")
        assert ok is False

    def test_change_password_strong_accepted(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        ok, msg = db.change_password("admin", "MyStr0ng!Pass", "N3wStr0ng!Pass")
        assert ok is True
        # Verify new password works
        token = db.authenticate("admin", "N3wStr0ng!Pass")
        assert token is not None

    def test_change_password_wrong_old_password_rejected(self):
        from core.auth_db import AuthDB

        db = AuthDB()
        db.setup_first_admin("MyStr0ng!Pass")
        ok, msg = db.change_password("admin", "WrongOld!1", "N3wStr0ng!Pass")
        assert ok is False
        assert "incorrect" in msg.lower()
