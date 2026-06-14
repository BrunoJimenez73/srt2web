"""Shared server utilities for extracting app context and path checks."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request


def get_ctx(request: Request) -> dict[str, Any]:
    """Extract the app context dict from a FastAPI request.

    All route modules need access to the shared app context (config,
    pipeline, input_source, etc.). This function centralises the
    extraction so routes don't duplicate a local ``_ctx()`` helper.
    """
    return request.app.state.ctx  # type: ignore[no-any-return]


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
        "/ws/logs",
    }
)

_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/api/auth/",
    "/_astro/",
    "/assets/",
    "/hls/",
    "/api/docs",
)


def is_public_path(path: str) -> bool:
    """Return True if *path* should bypass authentication and security headers."""
    if path in _PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)
