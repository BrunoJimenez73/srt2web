"""
Authentication routes for SRT2Web.

Provides login, logout, register, user management endpoints.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth_db import auth_db

logger = logging.getLogger("srt2web.api.auth")

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=4, max_length=128)
    role: str = Field(default="viewer")


class RoleUpdateRequest(BaseModel):
    role: str


def _get_current_user(request: Request) -> dict[str, Any]:
    """Extract JWT user from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    token = auth_header[7:]
    user = auth_db.decode_token(token)
    if user is None:
        raise HTTPException(401, "Invalid or expired token")
    return user


def _require_role(required_role: str) -> Any:
    """Dependency factory for role-based access."""
    async def role_dependency(request: Request) -> dict[str, Any]:
        user = _get_current_user(request)
        if not auth_db.has_permission(user["role"], required_role):
            raise HTTPException(403, f"Role '{user['role']}' cannot perform this action")
        return user
    return role_dependency


require_admin = _require_role("admin")
require_operator = _require_role("operator")


@router.post("/auth/login")
async def login(body: LoginRequest) -> dict[str, Any]:
    """Login with username/password, returns JWT token."""
    token = auth_db.authenticate(body.username, body.password)
    if token is None:
        raise HTTPException(401, "Invalid username or password")
    user = auth_db.get_user(body.username)
    return {"token": token, "user": user}


@router.post("/auth/logout")
async def logout() -> dict[str, Any]:
    """Logout (client-side: discard token)."""
    return {"status": "logged_out"}


@router.get("/auth/me")
async def get_me(request: Request) -> dict[str, Any]:
    """Get current user info from token."""
    user = _get_current_user(request)
    user_info = auth_db.get_user(user["sub"])
    if user_info is None:
        raise HTTPException(404, "User not found")
    return user_info


@router.post("/auth/register")
async def register(body: RegisterRequest, request: Request) -> dict[str, Any]:
    """Register a new user (admin only)."""
    _get_current_user(request)  # Verify auth
    admin = _get_current_user(request)
    if not auth_db.has_permission(admin["role"], "admin"):
        raise HTTPException(403, "Only admins can register new users")
    ok = auth_db.create_user(body.username, body.password, body.role)
    if not ok:
        raise HTTPException(409, f"User '{body.username}' already exists or invalid role")
    return {"status": "created", "username": body.username, "role": body.role}


@router.get("/auth/users")
async def list_users(request: Request) -> dict[str, Any]:
    """List all users (admin only)."""
    _get_current_user(request)  # Verify auth
    admin = _get_current_user(request)
    if not auth_db.has_permission(admin["role"], "admin"):
        raise HTTPException(403, "Only admins can list users")
    return {"users": auth_db.list_users()}


@router.delete("/auth/users/{username}")
async def delete_user(username: str, request: Request) -> dict[str, Any]:
    """Delete a user (admin only)."""
    admin = _get_current_user(request)
    if not auth_db.has_permission(admin["role"], "admin"):
        raise HTTPException(403, "Only admins can delete users")
    if not auth_db.delete_user(username):
        raise HTTPException(400, f"Cannot delete user '{username}'")
    return {"status": "deleted", "username": username}


@router.put("/auth/users/{username}/role")
async def update_role(username: str, body: RoleUpdateRequest, request: Request) -> dict[str, Any]:
    """Update a user's role (admin only)."""
    admin = _get_current_user(request)
    if not auth_db.has_permission(admin["role"], "admin"):
        raise HTTPException(403, "Only admins can change roles")
    if not auth_db.update_role(username, body.role):
        raise HTTPException(400, f"Cannot update role for '{username}'")
    return {"status": "updated", "username": username, "role": body.role}
