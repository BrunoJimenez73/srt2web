"""Shared server utilities for extracting app context and path checks."""

from __future__ import annotations

import os
from typing import Any

from starlette.requests import Request


def get_ctx(request: Request) -> dict[str, Any]:
    """Extract the app context dict from a FastAPI request.

    All route modules need access to the shared app context (config,
    pipeline, input_source, etc.). This function centralises the
    extraction so routes don't duplicate a local ``_ctx()`` helper.
    """
    return request.app.state.ctx  # type: ignore[no-any-return]


def get_auth_token(config: object | None = None) -> str:
    """Resolve the shared static API/WebSocket token.

    Configuration values take precedence for backwards compatibility, while
    environment variables provide the secure deployment path when the token
    is intentionally omitted from ``config.yaml``.
    """
    configured = ""
    getter = getattr(config, "get", None)
    if callable(getter):
        try:
            value = getter("server.auth_token", "")
        except Exception:
            value = ""
        if isinstance(value, str):
            configured = value.strip()
    return configured or os.environ.get("SRT2WEB_AUTH_TOKEN", "") or os.environ.get("AUTH_TOKEN", "")


# Paths that bypass both auth and security headers.
_PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/health",
        "/player",
        "/api/available",
        "/api/health",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/hls/",
        "/subtitles/",
        "/ws/logs",
    }
)

_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/api/auth/",
    "/_astro/",
    "/assets/",
    "/hls/",
    "/subtitles/",
    "/api/docs",
)


def is_public_path(path: str) -> bool:
    """Return True if *path* should bypass authentication and security headers."""
    if path in _PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)
