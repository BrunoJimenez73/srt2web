"""
Security middleware for SRT2Web.

Provides authentication, rate limiting, and security headers.
"""

import logging
import time
from typing import Optional, Callable
from collections import defaultdict
from threading import Lock

from fastapi import Request, HTTPException, WebSocket, Depends
from fastapi.responses import Response, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("srt2web.security")


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.
    Thread-safe for concurrent access.
    """

    def __init__(self, requests_per_minute: int = 60) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_ms = 60_000  # 1 minute in ms
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _cleanup_old(self, key: str, now: float) -> None:
        """Remove requests older than the window."""
        cutoff = now - (self.window_ms / 1000)
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """
        Check if request is allowed and record it.
        Returns (allowed, remaining_requests).
        """
        now = time.time()
        with self._lock:
            self._cleanup_old(key, now)
            count = len(self._requests[key])
            if count >= self.requests_per_minute:
                return False, 0
            self._requests[key].append(now)
            return True, self.requests_per_minute - count - 1

    def get_retry_after(self, key: str) -> int:
        """Get seconds until next request is allowed."""
        now = time.time()
        with self._lock:
            if not self._requests[key]:
                return 0
            oldest = min(self._requests[key])
            retry_after = int(oldest + (self.window_ms / 1000) - now) + 1
            return max(1, retry_after)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware using Bearer token.
    Skips /health, /api/available, and static files.
    """

    def __init__(self, app: ASGIApp, get_auth_token: Callable[[], str]) -> None:
        super().__init__(app)
        self.get_auth_token = get_auth_token

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip auth for public endpoints
        if self._is_public_path(path):
            return await call_next(request)

        auth_token = self.get_auth_token()

        # If no token configured, allow all (backwards compatibility warning)
        if not auth_token:
            logger.warning(
                "SECURITY: auth_token not configured - API is unprotected!"
            )
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header. Use: Authorization: Bearer <token>"}
            )

        token = auth_header[7:]  # Remove "Bearer " prefix
        if token != auth_token:
            logger.warning(f"SECURITY: Invalid auth token attempt from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication token"}
            )

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Paths that don't require authentication."""
        public_paths = {
            "/",
            "/health",
            "/player",
            "/api/available",
            "/api/health",
            "/hls/",
            "/ws/logs",  # WebSocket has its own auth
        }
        if path in public_paths:
            return True
        if path.startswith("/_astro/"):  # Astro build assets
            return True
        if path.startswith("/assets/"):
            return True
        if path.startswith("/hls/"):
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    Rate limits by IP address for unauthenticated requests,
    or by token for authenticated requests.
    """

    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: RateLimiter,
        get_auth_token: Callable[[], str],
    ) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.get_auth_token = get_auth_token

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip rate limiting for public endpoints
        if self._is_public_path(path):
            return await call_next(request)

        # Determine rate limit key
        auth_token = self.get_auth_token()
        if auth_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                key = f"token:{auth_header[7:]}"
            else:
                key = f"ip:{self._get_client_ip(request)}"
        else:
            key = f"ip:{self._get_client_ip(request)}"

        allowed, remaining = self.rate_limiter.is_allowed(key)
        if not allowed:
            retry_after = self.rate_limiter.get_retry_after(key)
            logger.warning(f"RATE LIMIT: {key} exceeded limit")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
        return response

    def _is_public_path(self, path: str) -> bool:
        public_paths = {"/", "/health", "/player", "/api/available", "/api/health"}
        if path in public_paths:
            return True
        if path.startswith("/_astro/"):
            return True
        if path.startswith("/assets/"):
            return True
        if path.startswith("/hls/"):
            return True
        return False

    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP, considering proxies."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limits the size of incoming request bodies to prevent memory exhaustion.
    """

    def __init__(self, app: ASGIApp, max_size_bytes: int = 1_048_576) -> None:  # 1MB default
        super().__init__(app)
        self.max_size_bytes = max_size_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size_bytes:
            logger.warning(
                f"Request too large: {content_length} bytes from {request.client.host}"
            )
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large. Maximum size: {self.max_size_bytes / 1024 / 1024:.1f}MB"}
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # XSS Protection (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (permissive for HLS playback and Google Fonts)
        csp = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob: http://* https://*; "
            "media-src 'self' blob: http://* https://*; "
            "worker-src 'self' blob:; "
            "connect-src 'self' ws://* wss://* http://* https://*; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "object-src 'none'; "
            "frame-src 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        # Strict Transport Security (only for HTTPS, but safe to include)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Permissions Policy (disable unnecessary browser features)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        return response


def validate_ws_auth(request: Request, get_auth_token: Callable[[], str]) -> bool:
    """
    Validate authentication for WebSocket connections.
    Returns True if authenticated or no token required.
    """
    auth_token = get_auth_token()

    if not auth_token:
        logger.warning("SECURITY: WebSocket accessed without auth_token configured")
        return True

    # Get token from query parameter ?token=xxx
    token = request.query_params.get("token")
    if not token:
        logger.warning("SECURITY: WebSocket connection without token parameter")
        return False

    if token != auth_token:
        logger.warning(f"SECURITY: WebSocket invalid token from {request.client.host}")
        return False

    return True
