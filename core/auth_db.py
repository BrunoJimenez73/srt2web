"""
AuthDB - Almacenamiento de usuarios con JSON + JWT.

Sin dependencias externas: usa hashlib para contraseñas y PyJWT para tokens.
Los usuarios se persisten en config/users.json.

F118: Password hashing upgraded from SHA-256 to PBKDF2-HMAC-SHA256 with
600K iterations. Existing SHA-256 hashes are auto-migrated on login.
"""

import contextlib
import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, cast

import jwt

from core.paths import atomic_replace, get_user_config_dir

logger = logging.getLogger(__name__)

# F124: Security audit logger — always goes to security.log
_security_logger = logging.getLogger("srt2web.security")

# F118: No hardcoded fallback. validate_secrets() in main.py blocks startup
# if SRT2WEB_JWT_SECRET is empty. The empty string here is intentional — it
# means "no secret configured" and will fail jwt.encode/decode.
JWT_SECRET_KEY = os.environ.get("SRT2WEB_JWT_SECRET", "")
JWT_ALGORITHM = "HS256"

if not JWT_SECRET_KEY:
    _security_logger.warning(
        "SRT2WEB_JWT_SECRET is empty — JWT tokens will be unsigned. "
        "Set SRT2WEB_JWT_SECRET environment variable for production use."
    )

# F123: Access token (short-lived) and refresh token (long-lived)
_ACCESS_TOKEN_MINUTES = 15
_REFRESH_TOKEN_DAYS = 7

# F118: PBKDF2 parameters (NIST SP 800-132 recommends ≥600K for SHA-256)
_PBKDF2_ITERATIONS = 600_000
_PBKDF2_HASH_NAME = "sha256"
_PBKDF2_KEY_LENGTH = 32

# Detect legacy SHA-256 hashes (64 hex chars = 32 bytes)
_LEGACY_SHA256_LENGTH = 64

# F121: Password policy
_MIN_PASSWORD_LENGTH = 8
_PASSWORD_SPECIAL_CHARS = set("!@#$%^&*()_+-=[]{}|;':\",./<>?`~")

# F122: Account lockout
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_WINDOW_SECONDS = 15 * 60  # 15 minutes
_LOCKOUT_DURATION_SECONDS = 30 * 60  # 30 minutes

# Top-100 common passwords (subset for inline check)
_COMMON_PASSWORDS: set[str] = {
    "password",
    "123456",
    "12345678",
    "qwerty",
    "abc123",
    "monkey",
    "master",
    "dragon",
    "login",
    "princess",
    "football",
    "shadow",
    "sunshine",
    "trustno1",
    "iloveyou",
    "batman",
    "access",
    "hello",
    "charlie",
    "donald",
    "password1",
    "letmein",
    "welcome",
    "admin",
    "passw0rd",
    "pass",
    "test",
    "guest",
    "1234567",
    "1234567890",
    "12345",
    "1234",
    "123456789",
    "qwerty123",
    "000000",
    "111111",
    "123123",
    "666666",
    "7777777",
    "fuckyou",
    "121212",
    "qazwsx",
    "michael",
    "ashley",
    "jessica",
    "bailey",
    "ranger",
    "matrix",
    "summer",
    "hunter",
    "thomas",
    "soccer",
    "hockey",
    "george",
    "andrew",
    "flower",
    "pepper",
    "jordan",
    "joshua",
    "nicole",
    "daniel",
    "madison",
    "william",
    "nathan",
    "austin",
    "matthew",
    "robert",
    "david",
    "samsung",
    "phoenix",
    "tigger",
    "orange",
    "merlin",
    "corvette",
    "coffee",
    "spider",
    "birdie",
    "silver",
    "banana",
    "purple",
    "london",
    "turtle",
    "diamond",
    "falcon",
    "cookie",
    "jennifer",
    "amanda",
    "james",
    "jonathan",
    "joseph",
    "ryan",
    "patrick",
    "samuel",
}

ROLES = {"admin": 100, "operator": 50, "viewer": 10}

USERS_FILE = get_user_config_dir() / "users.json"
BLACKLIST_FILE = get_user_config_dir() / "token_blacklist.json"


@dataclass
class User:
    username: str
    password_hash: str
    password_salt: str
    role: str  # admin, operator, viewer
    enabled: bool = True
    created_at: float = 0.0
    last_login: float = 0.0
    failed_attempts: int = 0
    locked_until: float = 0.0


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """F118: Hash password using PBKDF2-HMAC-SHA256 with 600K iterations."""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH_NAME,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
        _PBKDF2_KEY_LENGTH,
    ).hex()
    return h, salt


def _is_legacy_sha256(hash_hex: str) -> bool:
    """Detect if a hash was created with the old SHA-256 method (64 hex chars)."""
    return len(hash_hex) == _LEGACY_SHA256_LENGTH and all(c in "0123456789abcdef" for c in hash_hex)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """F121: Validate password strength. Returns (ok, message).

    Policy:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    - Not in top-100 common passwords list
    """
    # Check common passwords first (before complexity)
    if password.lower() in _COMMON_PASSWORDS:
        return False, "Esta contraseña es demasiado común. Elige una más segura"

    if len(password) < _MIN_PASSWORD_LENGTH:
        return False, f"La contraseña debe tener al menos {_MIN_PASSWORD_LENGTH} caracteres"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in _PASSWORD_SPECIAL_CHARS for c in password)

    missing = []
    if not has_upper:
        missing.append("1 mayúscula")
    if not has_lower:
        missing.append("1 minúscula")
    if not has_digit:
        missing.append("1 dígito")
    if not has_special:
        missing.append("1 carácter especial")

    if missing:
        return False, f"La contraseña debe contener: {', '.join(missing)}"

    return True, "Contraseña válida"


def _load_users() -> dict[str, Any]:
    if USERS_FILE.exists():
        try:
            result = json.loads(USERS_FILE.read_text(encoding="utf-8"))
            return cast(dict[str, Any], result)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_users(users: dict[str, dict[str, Any]]) -> None:
    """F118: Atomic save using temp file + atomic_replace()."""
    import tempfile

    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=str(USERS_FILE.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
        atomic_replace(temp_path, str(USERS_FILE))
    except Exception as e:
        logger.debug("Failed to persist users, cleaning up temp file: %s", e)
        with contextlib.suppress(OSError):
            os.unlink(temp_path)
        raise


class AuthDB:
    """Thread-safe user database backed by JSON file."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._users: dict[str, dict[str, Any]] = {}
        self._blacklist: set[str] = set()
        self._blacklist_lock = Lock()
        self._load()

    def _load(self) -> None:
        with self._lock:
            self._users = _load_users()
            self._load_blacklist()
            # F120: No default admin. First admin must be created via
            # setup_first_admin() or SRT2WEB_ADMIN_PASSWORD env var.
            # Check env var for automated deployment.
            if not self._users:
                self._try_create_admin_from_env()

    def _load_blacklist(self) -> None:
        try:
            if BLACKLIST_FILE.exists():
                data = json.loads(BLACKLIST_FILE.read_text(encoding="utf-8"))
                self._blacklist = set(data.get("blacklist", []))
        except (json.JSONDecodeError, OSError):
            self._blacklist = set()

    def _save_blacklist(self) -> None:
        try:
            BLACKLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
            import tempfile

            fd, temp_path = tempfile.mkstemp(dir=str(BLACKLIST_FILE.parent), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"blacklist": list(self._blacklist)}, f)
            atomic_replace(temp_path, str(BLACKLIST_FILE))
        except Exception as e:
            logger.warning("Failed to persist token blacklist: %s", e)

    def _try_create_admin_from_env(self) -> None:
        """Create admin from SRT2WEB_ADMIN_PASSWORD env var if set."""
        admin_pass = os.environ.get("SRT2WEB_ADMIN_PASSWORD", "")
        if admin_pass:
            h, salt = _hash_password(admin_pass)
            self._users["admin"] = {
                "password_hash": h,
                "password_salt": salt,
                "role": "admin",
                "enabled": True,
                "created_at": time.time(),
                "last_login": 0.0,
                "failed_attempts": 0,
                "locked_until": 0.0,
                "token_version": 0,
            }
            _save_users(self._users)
            logger.info("F120: Created admin user from SRT2WEB_ADMIN_PASSWORD env var")

    def setup_first_admin(self, password: str, username: str = "admin") -> tuple[bool, str]:
        """Create the first admin user. Only works if no users exist.
        Returns (ok, message) — F121: validates password strength.
        SEC-03: uses the provided username instead of hardcoding \"admin\".
        """
        ok, msg = validate_password_strength(password)
        if not ok:
            return False, msg
        with self._lock:
            if self._users:
                return False, "Users already exist"
            h, salt = _hash_password(password)
            self._users[username] = {
                "password_hash": h,
                "password_salt": salt,
                "role": "admin",
                "enabled": True,
                "created_at": time.time(),
                "last_login": 0.0,
                "failed_attempts": 0,
                "locked_until": 0.0,
                "token_version": 0,
            }
            _save_users(self._users)
            return True, "Admin created"

    def has_users(self) -> bool:
        """Check if any users exist."""
        with self._lock:
            return bool(self._users)

    def _get_token_version(self, username: str) -> int:
        """Get the current token_version for a user (DT-08)."""
        user = self._users.get(username, {})
        tv: int = user.get("token_version", 0)
        return tv

    def _generate_access_token(self, username: str, role: str) -> str:
        """F123: Generate a short-lived access token with unique jti."""
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": username,
            "role": role,
            "iat": now,
            "exp": now + _ACCESS_TOKEN_MINUTES * 60,
            "type": "access",
            "jti": secrets.token_hex(16),
            "token_version": self._get_token_version(username),
        }
        return str(jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM))

    def _generate_refresh_token(self, username: str) -> str:
        """F123: Generate a long-lived refresh token."""
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": username,
            "iat": now,
            "exp": now + _REFRESH_TOKEN_DAYS * 86400,
            "type": "refresh",
            "jti": secrets.token_hex(16),
            "token_version": self._get_token_version(username),
        }
        return str(jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM))

    def authenticate(self, username: str, password: str) -> str | None:
        """Verify credentials and return JWT access token, or None if invalid.

        F118: Uses timing-safe comparison (secrets.compare_digest) and
        auto-migrates legacy SHA-256 hashes to PBKDF2 on successful login.

        F122: Tracks failed attempts and locks account after _MAX_FAILED_ATTEMPTS.

        F123: Returns a short-lived (15 min) access token.
        For refresh token, call authenticate_full() or refresh_token().
        """
        with self._lock:
            user = self._users.get(username)
            if not user or not user.get("enabled", True):
                return None

            # F122: Check if account is locked
            now = time.time()
            locked_until = user.get("locked_until", 0.0)
            if locked_until > now:
                logger.debug(f"F122: Login rejected for locked account '{username}'")
                _security_logger.warning(
                    "Rejected login for locked account '%s' (locked %ds remaining)",
                    username,
                    int(locked_until - now),
                )
                return None

            # F122 / DT-06: Auto-expire lock if time passed
            if locked_until:
                user["locked_until"] = 0.0
                user["failed_attempts"] = 0
                user["_attempt_timestamps"] = []

            # F118: Try PBKDF2 first (current method)
            h_pbkdf2, _ = _hash_password(password, user["password_salt"])
            matched = secrets.compare_digest(h_pbkdf2, user["password_hash"])

            # F118: If no match and stored hash looks like legacy SHA-256,
            # try the old method to allow migration
            if not matched and _is_legacy_sha256(user["password_hash"]):
                h_legacy = hashlib.sha256((user["password_salt"] + password).encode()).hexdigest()
                if secrets.compare_digest(h_legacy, user["password_hash"]):
                    matched = True
                    # Migrate to PBKDF2
                    new_hash, new_salt = _hash_password(password)
                    user["password_hash"] = new_hash
                    user["password_salt"] = new_salt
                    logger.info(f"Migrated user '{username}' from SHA-256 to PBKDF2")

            if not matched:
                # F122 / DT-06: Sliding-window lockout — only count
                # attempts within the last _LOCKOUT_WINDOW_SECONDS.
                now_float = time.time()
                attempt_timestamps: list[float] = user.get("_attempt_timestamps", [])
                cutoff_ts = now_float - _LOCKOUT_WINDOW_SECONDS
                attempt_timestamps = [t for t in attempt_timestamps if t > cutoff_ts]
                attempt_timestamps.append(now_float)
                user["_attempt_timestamps"] = attempt_timestamps
                attempts = len(attempt_timestamps)
                user["failed_attempts"] = attempts
                # F124: Log security event
                _security_logger.warning(
                    "Failed login attempt for '%s' (attempt %d/%d)",
                    username,
                    attempts,
                    _MAX_FAILED_ATTEMPTS,
                )
                if attempts >= _MAX_FAILED_ATTEMPTS:
                    user["locked_until"] = now + _LOCKOUT_DURATION_SECONDS
                    logger.warning(
                        f"F122: Account '{username}' locked for {_LOCKOUT_DURATION_SECONDS}s"
                        f" after {attempts} failed attempts"
                    )
                    _security_logger.warning(
                        "Account locked: '%s' for %ds after %d failed attempts",
                        username,
                        _LOCKOUT_DURATION_SECONDS,
                        attempts,
                    )
                _save_users(self._users)
                return None

            # F122 / DT-06: Reset lockout on successful login
            user["failed_attempts"] = 0
            user["locked_until"] = 0.0
            user["_attempt_timestamps"] = []
            user["last_login"] = time.time()
            _save_users(self._users)

            return self._generate_access_token(username, user["role"])

    def authenticate_full(self, username: str, password: str) -> dict[str, Any] | None:
        """F123: Verify credentials and return both access + refresh tokens.

        Returns {"access_token": ..., "refresh_token": ..., "token_type": "bearer"}
        or None if credentials are invalid.
        """
        access_token = self.authenticate(username, password)
        if access_token is None:
            return None
        return {
            "access_token": access_token,
            "refresh_token": self._generate_refresh_token(username),
            "token_type": "bearer",
        }

    def get_user(self, username: str) -> dict[str, Any] | None:
        with self._lock:
            user = self._users.get(username)
            if user:
                return {k: v for k, v in user.items() if k not in ("password_hash", "password_salt")}
            return None

    def is_locked(self, username: str) -> bool:
        """F122: Check if an account is currently locked."""
        with self._lock:
            user = self._users.get(username)
            if not user:
                return False
            locked_until: float = user.get("locked_until", 0.0)
            return locked_until > time.time()

    def unlock_user(self, username: str) -> bool:
        """F122: Unlock a locked account. Returns True if user existed."""
        with self._lock:
            user = self._users.get(username)
            if not user:
                return False
            user["failed_attempts"] = 0
            user["locked_until"] = 0.0
            _save_users(self._users)
            logger.info(f"F122: Account '{username}' manually unlocked")
            _security_logger.info("Account manually unlocked: '%s'", username)
            return True

    def list_users(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {k: v for k, v in u.items() if k not in ("password_hash", "password_salt")}
                for u in self._users.values()
            ]

    def create_user(self, username: str, password: str, role: str = "viewer") -> tuple[bool, str]:
        """Create a new user. F121: validates password strength."""
        ok, msg = validate_password_strength(password)
        if not ok:
            return False, msg
        if role not in ROLES:
            return False, f"Invalid role: {role}"
        with self._lock:
            if username in self._users:
                return False, f"User '{username}' already exists"
            h, salt = _hash_password(password)
            self._users[username] = {
                "password_hash": h,
                "password_salt": salt,
                "role": role,
                "enabled": True,
                "created_at": time.time(),
                "last_login": 0.0,
                "failed_attempts": 0,
                "locked_until": 0.0,
                "token_version": 0,
            }
            _save_users(self._users)
            return True, "User created"

    def delete_user(self, username: str) -> bool:
        with self._lock:
            if username not in self._users:
                return False
            # F120: Don't delete the last admin
            admin_count = sum(1 for u in self._users.values() if u.get("role") == "admin")
            if self._users[username].get("role") == "admin" and admin_count <= 1:
                return False
            # Invalidate any existing tokens by bumping token_version
            self._users[username]["token_version"] = self._users[username].get("token_version", 0) + 1
            del self._users[username]
            _save_users(self._users)
        return True

    def update_role(self, username: str, role: str) -> bool:
        if role not in ROLES:
            return False
        with self._lock:
            if username not in self._users:
                return False
            self._users[username]["role"] = role
            self._users[username]["token_version"] = self._users[username].get("token_version", 0) + 1
            _save_users(self._users)
            logger.info(
                "DT-08: Role for '%s' changed to '%s' (token_version=%d)",
                username,
                role,
                self._users[username]["token_version"],
            )
            return True

    def has_permission(self, role: str, required_role: str) -> bool:
        return ROLES.get(role, 0) >= ROLES.get(required_role, 0)

    def change_password(self, username: str, old_password: str, new_password: str) -> tuple[bool, str]:
        """F121: Change user password with validation."""
        ok, msg = validate_password_strength(new_password)
        if not ok:
            return False, msg
        with self._lock:
            user = self._users.get(username)
            if not user:
                return False, "User not found"
            # Verify old password
            h_old, _ = _hash_password(old_password, user["password_salt"])
            if not secrets.compare_digest(h_old, user["password_hash"]):
                return False, "Current password is incorrect"
            h_new, salt_new = _hash_password(new_password)
            user["password_hash"] = h_new
            user["password_salt"] = salt_new
            # F122: Reset lockout on password change
            user["failed_attempts"] = 0
            user["locked_until"] = 0.0
            _save_users(self._users)
            return True, "Password changed"

    def decode_token(self, token: str) -> dict[str, Any] | None:
        """F123: Decode and verify a token. Checks expiration AND blacklist."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

        # F123: Check blacklist
        jti = payload.get("jti")
        if jti and self._is_blacklisted(jti):
            logger.debug("F123: Rejected blacklisted token")
            return None

        # DT-08: Check token_version against current user version.
        # If the user's role was changed (token_version incremented),
        # all tokens issued before that change are rejected.
        username = payload.get("sub", "")
        token_ver = payload.get("token_version", 0)
        current_ver = self._get_token_version(username)
        if token_ver < current_ver:
            logger.debug("DT-08: Rejected stale token for '%s' (ver %d < %d)", username, token_ver, current_ver)
            return None

        if not isinstance(payload, dict):
            return None

        return payload

    def _is_blacklisted(self, jti: str) -> bool:
        """F123: Check if a token jti is blacklisted."""
        with self._blacklist_lock:
            return jti in self._blacklist

    def revoke_token(self, token: str) -> bool:
        """F123: Revoke a token by adding its jti to the blacklist.
        Returns True if the token was valid and revoked.
        """
        payload = self.decode_token(token)
        if payload is None:
            return False
        jti = payload.get("jti")
        if not jti:
            return False
        with self._blacklist_lock:
            self._blacklist.add(jti)
            self._save_blacklist()
        logger.debug(f"F123: Revoked token jti={jti}")
        return True

    def refresh_token(self, refresh_token_str: str) -> dict[str, Any] | None:
        """F123: Validate a refresh token and return a new token pair.

        Accepts only tokens with type="refresh". Revokes the old refresh
        token and returns a fresh pair (rotation).
        Returns {"access_token": ..., "refresh_token": ..., "token_type": "bearer"}
        or None if the refresh token is invalid/expired/revoked.
        """
        payload = self.decode_token(refresh_token_str)
        if payload is None:
            return None
        if payload.get("type") != "refresh":
            logger.debug("F123: Token is not a refresh token")
            return None

        username = payload.get("sub", "")
        with self._lock:
            user = self._users.get(username)
            if not user or not user.get("enabled", True):
                return None

        # Revoke old refresh token (rotation)
        jti = payload.get("jti", "")
        if jti:
            with self._blacklist_lock:
                self._blacklist.add(jti)
                self._save_blacklist()

        return {
            "access_token": self._generate_access_token(username, user["role"]),
            "refresh_token": self._generate_refresh_token(username),
            "token_type": "bearer",
        }


# Singleton
auth_db = AuthDB()
