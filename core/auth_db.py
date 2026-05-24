"""
AuthDB - Almacenamiento de usuarios con JSON + JWT.

Sin dependencias externas: usa hashlib para contraseñas y PyJWT para tokens.
Los usuarios se persisten en config/users.json.
"""

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, cast

import jwt

JWT_SECRET_KEY = os.environ.get("SRT2WEB_JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

ROLES = {"admin": 100, "operator": 50, "viewer": 10}

USERS_FILE = Path(__file__).parent.parent / "config" / "users.json"


@dataclass
class User:
    username: str
    password_hash: str
    password_salt: str
    role: str  # admin, operator, viewer
    enabled: bool = True
    created_at: float = 0.0
    last_login: float = 0.0


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt


def _load_users() -> dict[str, Any]:
    if USERS_FILE.exists():
        try:
            result = json.loads(USERS_FILE.read_text(encoding="utf-8"))
            return cast(dict[str, Any], result)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_users(users: dict[str, dict[str, Any]]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


class AuthDB:
    """Thread-safe user database backed by JSON file."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._users: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        with self._lock:
            self._users = _load_users()
            if not self._users:
                self._seed_default_admin()

    def _seed_default_admin(self) -> None:
        h, salt = _hash_password("admin")
        self._users["admin"] = {
            "password_hash": h,
            "password_salt": salt,
            "role": "admin",
            "enabled": True,
            "created_at": time.time(),
            "last_login": 0.0,
        }
        _save_users(self._users)

    def authenticate(self, username: str, password: str) -> str | None:
        """Verify credentials and return JWT token, or None if invalid."""
        with self._lock:
            user = self._users.get(username)
            if not user or not user.get("enabled", True):
                return None

            h, _ = _hash_password(password, user["password_salt"])
            if h != user["password_hash"]:
                return None

            user["last_login"] = time.time()
            _save_users(self._users)

            payload = {
                "sub": username,
                "role": user["role"],
                "iat": int(time.time()),
                "exp": int(time.time()) + JWT_EXPIRY_HOURS * 3600,
            }
            return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def get_user(self, username: str) -> dict[str, Any] | None:
        with self._lock:
            user = self._users.get(username)
            if user:
                return {k: v for k, v in user.items() if k not in ("password_hash", "password_salt")}
            return None

    def list_users(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {k: v for k, v in u.items() if k not in ("password_hash", "password_salt")}
                for u in self._users.values()
            ]

    def create_user(self, username: str, password: str, role: str = "viewer") -> bool:
        if role not in ROLES:
            return False
        with self._lock:
            if username in self._users:
                return False
            h, salt = _hash_password(password)
            self._users[username] = {
                "password_hash": h,
                "password_salt": salt,
                "role": role,
                "enabled": True,
                "created_at": time.time(),
                "last_login": 0.0,
            }
            _save_users(self._users)
            return True

    def delete_user(self, username: str) -> bool:
        if username == "admin":
            return False  # Can't delete default admin
        with self._lock:
            return self._users.pop(username, None) is not None

    def update_role(self, username: str, role: str) -> bool:
        if role not in ROLES:
            return False
        with self._lock:
            if username not in self._users:
                return False
            self._users[username]["role"] = role
            _save_users(self._users)
            return True

    def has_permission(self, role: str, required_role: str) -> bool:
        return ROLES.get(role, 0) >= ROLES.get(required_role, 0)

    def decode_token(self, token: str) -> dict[str, Any] | None:
        try:
            return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


# Singleton
auth_db = AuthDB()
