"""
Authentication routes for SRT2Web multi-user system (F46).

Provides login, logout, and user management endpoints
with JWT token-based sessions and role-based permissions.
"""

import logging
import os
import time
from typing import Any
from urllib.parse import parse_qs

import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

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

logger = logging.getLogger("srt2web.api.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

JWT_SECRET = os.environ.get("SRT2WEB_JWT_SECRET", "srt2web-default-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = 86400  # 24 hours


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"


@router.on_event("startup")
def startup() -> None:
    init_db()
    if not has_users():
        create_user("admin", "admin", "admin")
        logger.info("Created default admin user (change password immediately)")


@router.post("/login")
async def login(body: LoginRequest) -> dict[str, str]:
    user = verify_user(body.username, body.password)
    if user is None:
        raise HTTPException(401, "Invalid username or password")
    now = int(time.time())
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "iat": now,
        "exp": now + JWT_EXPIRY,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"token": token, "username": user["username"], "role": user["role"]}


@router.post("/register")
async def register(request: Request, body: RegisterRequest) -> dict[str, Any]:
    ctx = request.app.state.ctx
    config = ctx.get("config", {})
    auth_token = config.get("server.auth_token", "") if hasattr(config, "get") else ""

    if not auth_token and has_users():
        raise HTTPException(403, "Registration disabled: use existing admin account")

    token_str = request.headers.get("Authorization", "")
    if token_str.startswith("Bearer "):
        token_val = token_str[7:]
        if token_val != auth_token:
            pass

    if body.role != "viewer":
        allowed = False
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                decoded = jwt.decode(auth_header[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
                allowed = UserRole.has_permission(decoded.get("role", "viewer"), "admin")
            except jwt.InvalidTokenError:
                pass
        if not allowed:
            raise HTTPException(403, "Only admins can create non-viewer users")

    try:
        result = create_user(body.username, body.password, body.role)
        return {"status": "created", "user": result}
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/users")
async def users(request: Request) -> dict[str, Any]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing authorization token")
    try:
        decoded = jwt.decode(auth_header[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if decoded.get("role") != "admin":
            raise HTTPException(403, "Admin role required")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    return {"users": list_users()}


@router.delete("/users/{username}")
async def delete_user_endpoint(request: Request, username: str) -> dict[str, str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing authorization token")
    try:
        decoded = jwt.decode(auth_header[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if decoded.get("role") != "admin":
            raise HTTPException(403, "Admin role required")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    delete_user(username)
    return {"status": "deleted", "username": username}


@router.get("/me")
async def me(request: Request) -> dict[str, str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        decoded = jwt.decode(auth_header[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"username": decoded["sub"], "role": decoded["role"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")