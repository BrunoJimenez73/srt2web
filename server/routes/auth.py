"""
Authentication routes for SRT2Web.

Provides login, logout, register, user management endpoints.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import core.auth_db

logger = logging.getLogger("srt2web.api.auth")

router = APIRouter(tags=["auth"])


def _get_auth_db() -> core.auth_db.AuthDB:
    """Return the current auth_db singleton.
    Uses module-level import so tests can monkeypatch core.auth_db.auth_db.
    """
    return core.auth_db.auth_db


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)
    role: str = Field(default="viewer")


class RoleUpdateRequest(BaseModel):
    role: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


def _get_current_user(request: Request) -> dict[str, Any]:
    """Extract JWT user from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    token = auth_header[7:]
    user = _get_auth_db().decode_token(token)
    if user is None:
        raise HTTPException(401, "Invalid or expired token")
    return user


def _require_role(required_role: str) -> Any:
    """Dependency factory for role-based access."""

    async def role_dependency(request: Request) -> dict[str, Any]:
        user = _get_current_user(request)
        if not _get_auth_db().has_permission(user["role"], required_role):
            raise HTTPException(403, f"Role '{user['role']}' cannot perform this action")
        return user

    return role_dependency


require_admin = _require_role("admin")
require_operator = _require_role("operator")


@router.get("/auth/setup")
async def get_setup_status() -> dict[str, Any]:
    """Check if initial setup is needed (no users exist)."""
    return {"needs_setup": not _get_auth_db().has_users()}


@router.post("/auth/setup")
async def setup_first_admin(body: LoginRequest) -> dict[str, Any]:
    """Create the first admin user. Only works when no users exist."""
    ok, msg = _get_auth_db().setup_first_admin(body.password)
    if not ok:
        raise HTTPException(400, msg)
    # Auto-login after setup
    tokens = _get_auth_db().authenticate_full("admin", body.password)
    user = _get_auth_db().get_user("admin")
    if tokens:
        return {**tokens, "user": user}
    return {"user": user}


@router.post("/auth/login")
async def login(body: LoginRequest) -> dict[str, Any]:
    """Login with username/password, returns access + refresh tokens.

    F122: Returns 423 if account is locked.
    F123: Returns token pair with short-lived access token and long-lived refresh token.
    """
    if _get_auth_db().is_locked(body.username):
        raise HTTPException(423, "Account locked due to too many failed attempts. Try again later.")
    tokens = _get_auth_db().authenticate_full(body.username, body.password)
    if tokens is None:
        raise HTTPException(401, "Invalid username or password")
    user = _get_auth_db().get_user(body.username)
    return {**tokens, "user": user}


@router.post("/auth/logout")
async def logout(request: Request) -> dict[str, Any]:
    """Logout: revoke the current access token (server-side blacklist).

    F123: Token with matching jti is blacklisted and cannot be used again.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        _get_auth_db().revoke_token(token)
    return {"status": "logged_out"}


@router.post("/auth/refresh")
async def refresh_token(body: RefreshTokenRequest) -> dict[str, Any]:
    """Exchange a refresh token for a new token pair (rotation).

    F123: Old refresh token is revoked; new access + refresh tokens issued.
    """
    tokens = _get_auth_db().refresh_token(body.refresh_token)
    if tokens is None:
        raise HTTPException(401, "Invalid or expired refresh token")
    return tokens


@router.get("/auth/me")
async def get_me(request: Request) -> dict[str, Any]:
    """Get current user info from token."""
    user = _get_current_user(request)
    user_info = _get_auth_db().get_user(user["sub"])
    if user_info is None:
        raise HTTPException(404, "User not found")
    return user_info


@router.post("/auth/register")
async def register(body: RegisterRequest, request: Request) -> dict[str, Any]:
    """Register a new user (admin only)."""
    _get_current_user(request)  # Verify auth
    admin = _get_current_user(request)
    if not _get_auth_db().has_permission(admin["role"], "admin"):
        raise HTTPException(403, "Only admins can register new users")
    ok, msg = _get_auth_db().create_user(body.username, body.password, body.role)
    if not ok:
        raise HTTPException(400, msg)
    return {"status": "created", "username": body.username, "role": body.role}


@router.get("/auth/users")
async def list_users(request: Request) -> dict[str, Any]:
    """List all users (admin only)."""
    _get_current_user(request)  # Verify auth
    admin = _get_current_user(request)
    if not _get_auth_db().has_permission(admin["role"], "admin"):
        raise HTTPException(403, "Only admins can list users")
    return {"users": _get_auth_db().list_users()}


@router.delete("/auth/users/{username}")
async def delete_user(username: str, request: Request) -> dict[str, Any]:
    """Delete a user (admin only)."""
    admin = _get_current_user(request)
    if not _get_auth_db().has_permission(admin["role"], "admin"):
        raise HTTPException(403, "Only admins can delete users")
    if not _get_auth_db().delete_user(username):
        raise HTTPException(400, f"Cannot delete user '{username}'")
    return {"status": "deleted", "username": username}


@router.put("/auth/users/{username}/role")
async def update_role(username: str, body: RoleUpdateRequest, request: Request) -> dict[str, Any]:
    """Update a user's role (admin only)."""
    admin = _get_current_user(request)
    if not _get_auth_db().has_permission(admin["role"], "admin"):
        raise HTTPException(403, "Only admins can change roles")
    if not _get_auth_db().update_role(username, body.role):
        raise HTTPException(400, f"Cannot update role for '{username}'")
    return {"status": "updated", "username": username, "role": body.role}


@router.put("/auth/password")
async def change_password(body: ChangePasswordRequest, request: Request) -> dict[str, Any]:
    """Change current user's password (authenticated)."""
    user = _get_current_user(request)
    ok, msg = _get_auth_db().change_password(user["sub"], body.old_password, body.new_password)
    if not ok:
        raise HTTPException(400, msg)
    return {"status": "password_changed"}


@router.post("/auth/users/{username}/unlock")
async def unlock_user(username: str, request: Request) -> dict[str, Any]:
    """Unlock a user account (admin only). F122."""
    admin = _get_current_user(request)
    if not _get_auth_db().has_permission(admin["role"], "admin"):
        raise HTTPException(403, "Only admins can unlock accounts")
    if not _get_auth_db().unlock_user(username):
        raise HTTPException(404, f"User '{username}' not found")
    return {"status": "unlocked", "username": username}
