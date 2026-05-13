"""
SQLite database for SRT2Web multi-user authentication.

Provides user storage, password hashing, and role management
for the multi-user auth system (F46).
"""

import hashlib
import logging
import os
import sqlite3
import threading
from typing import Any, Optional

logger = logging.getLogger("srt2web.database")

DB_PATH = os.environ.get("SRT2WEB_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "srt2web.db"))

_local = threading.local()


class UserRole:
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

    ALL = (ADMIN, OPERATOR, VIEWER)

    HIERARCHY = {
        ADMIN: 100,
        OPERATOR: 50,
        VIEWER: 10,
    }

    @classmethod
    def has_permission(cls, role: str, required_role: str) -> bool:
        return cls.HIERARCHY.get(role, 0) >= cls.HIERARCHY.get(required_role, 0)


def _get_connection() -> Any:
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db() -> None:
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            active INTEGER DEFAULT 1
        )
    """)
    conn.commit()


def _hash_password(password: str, salt: str = "") -> tuple[str, str]:
    if not salt:
        salt = os.urandom(32).hex()
    h = hashlib.sha256()
    h.update(salt.encode())
    h.update(password.encode())
    for _ in range(1000):
        h.update(h.digest())
    return h.hexdigest(), salt


def create_user(username: str, password: str, role: str = "viewer") -> dict[str, str]:
    if role not in ("admin", "operator", "viewer"):
        role = "viewer"
    password_hash, salt = _hash_password(password)
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            (username, password_hash, salt, role),
        )
        conn.commit()
        return {"username": username, "role": role}
    except sqlite3.IntegrityError:
        raise ValueError(f"User '{username}' already exists")


def verify_user(username: str, password: str) -> dict[str, str] | None:
    conn = _get_connection()
    row = conn.execute(
        "SELECT username, password_hash, salt, role, active FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None or not row["active"]:
        return None
    hash_check, _ = _hash_password(password, row["salt"])
    if hash_check != row["password_hash"]:
        return None
    conn.execute(
        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
        (username,),
    )
    conn.commit()
    return {"username": row["username"], "role": row["role"]}


def get_user(username: str) -> dict[str, str | bool] | None:
    conn = _get_connection()
    row = conn.execute(
        "SELECT username, role, active FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        return None
    return {"username": row["username"], "role": row["role"], "active": bool(row["active"])}


def list_users() -> list[dict[str, str | bool]]:
    conn = _get_connection()
    rows = conn.execute("SELECT username, role, active, created_at FROM users ORDER BY created_at").fetchall()
    return [
        {
            "username": row["username"],
            "role": row["role"],
            "active": bool(row["active"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def delete_user(username: str) -> None:
    conn = _get_connection()
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()


def has_users() -> bool:
    conn = _get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    return bool(row["cnt"])