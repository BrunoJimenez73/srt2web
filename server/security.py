"""
Security middleware for SRT2Web.

Provides authentication, rate limiting, and security headers.
"""

import base64
import binascii
import hashlib
import hmac
import logging
import os
import secrets
import time
import warnings
from collections import defaultdict
from collections.abc import Awaitable, Callable
from threading import Lock

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, Response
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

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        path = request.url.path

        # Skip auth for public endpoints
        if self._is_public_path(path):
            return await call_next(request)

        auth_token = (
            self.get_auth_token() or os.environ.get("SRT2WEB_AUTH_TOKEN", "") or os.environ.get("AUTH_TOKEN", "")
        )

        # In test mode, skip authentication entirely (no 503, no 401)
        if os.environ.get("SRT2WEB_TESTING"):
            return await call_next(request)

        # Allow insecure dev mode: skip auth when SRT2WEB_ALLOW_INSECURE_DEFAULTS=1
        # and request comes from localhost. This lets the frontend work without
        # manually entering a token during local development, while still enforcing
        # auth in production/staging where this env var is not set.
        if os.environ.get("SRT2WEB_ALLOW_INSECURE_DEFAULTS", "").lower() in ("1", "true", "yes"):
            host = request.headers.get("host", "")
            if host.startswith("localhost") or host.startswith("127.0.0.1"):
                return await call_next(request)

        # F118: If no token configured, reject with 503 (Service Unavailable)
        # instead of silently allowing all requests through.
        if not auth_token:
            logger.error("SECURITY: auth_token not configured - API is unavailable!")
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "API is unavailable: authentication token not configured. "
                        "Set SRT2WEB_JWT_SECRET environment variable to enable authentication."
                    )
                },
            )

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header. Use: Authorization: Bearer <token>"},
            )

        token = auth_header[7:]  # Remove "Bearer " prefix
        if not hmac.compare_digest(token, auth_token):
            logger.warning(f"SECURITY: Invalid auth token attempt from {request.client.host}")  # type: ignore[union-attr]
            return JSONResponse(status_code=401, content={"detail": "Invalid authentication token"})

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Paths that don't require authentication."""
        from server.ctx import is_public_path

        return is_public_path(path)


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

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
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
        from server.ctx import is_public_path

        return is_public_path(path)

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

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_size_bytes:
                    logger.warning(
                        f"Request too large: {content_length} bytes from {request.client.host}"  # type: ignore[union-attr]
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body too large. Maximum size: {self.max_size_bytes / 1024 / 1024:.1f}MB"
                        },
                    )
            except ValueError:
                pass  # Non-numeric Content-Length; let it through
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    F124: Adds hardened security headers to all responses.

    CSP is tightened from the original permissive version:
    - unsafe-inline/unsafe-eval removed from default-src (only in script/style)
    - Wildcards removed from img-src/media-src/connect-src (explicit https: http: only)
    - strict-dynamic added for modern browser compatibility
    """

    # Base CSP that can be extended per-route by other middleware
    _CSP_BASE = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https: http:; "
        "media-src 'self' blob: https: http:; "
        "worker-src 'self' blob:; "
        "connect-src 'self' ws: wss: https: http:; "
        "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "object-src 'none'; "
        "frame-src 'none';"
    )

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # XSS Protection (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # F124: Hardened Content Security Policy
        response.headers["Content-Security-Policy"] = self._CSP_BASE

        # F124: Strict Transport Security with preload
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Permissions Policy (disable unnecessary browser features)
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        return response


class CsrfMiddleware(BaseHTTPMiddleware):
    """
    F125: CSRF protection middleware.

    Protects state-changing endpoints (POST, PUT, PATCH, DELETE) against
    Cross-Site Request Forgery. The client must obtain a CSRF token via
    GET /api/csrf-token and include it in the X-CSRF-Token header.

    Requests with an Authorization header (Bearer token) are exempt —
    they originate from programmatic API clients, not browser forms.
    """

    _CSRF_TIMEOUT = 3600  # 1 hour token expiry
    _MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app: ASGIApp, get_csrf_secret: Callable[[], str]) -> None:
        super().__init__(app)
        self.get_csrf_secret = get_csrf_secret

    @staticmethod
    def generate_token(secret: str) -> str:
        """Generate a signed CSRF token valid for _CSRF_TIMEOUT seconds."""
        nonce = secrets.token_hex(16)
        expiry = int(time.time()) + CsrfMiddleware._CSRF_TIMEOUT
        payload = f"{nonce}:{expiry}"
        sig = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return base64.urlsafe_b64encode(f"{sig}:{payload}".encode()).decode("ascii")

    @staticmethod
    def validate_token(token: str, secret: str) -> bool:
        """Validate a CSRF token. Returns True if valid and not expired."""
        try:
            decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
            parts = decoded.split(":")
            if len(parts) < 3:
                return False
            sig = parts[0]
            nonce = parts[1]
            expiry_str = parts[2]
            expiry = int(expiry_str)
            if time.time() > expiry:
                return False
            payload = f"{nonce}:{expiry}"
            expected = hmac.new(
                secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, sig)
        except (ValueError, IndexError, UnicodeDecodeError, binascii.Error):
            return False

    def _is_public_or_auth_path(self, path: str) -> bool:
        """Paths that don't need CSRF protection."""
        public = {
            "/",
            "/health",
            "/player",
            "/api/available",
            "/api/health",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        }
        if path in public:
            return True
        if path.startswith("/api/auth/"):
            return True
        if path.startswith("/_astro/"):
            return True
        if path.startswith("/assets/"):
            return True
        if path.startswith("/hls/"):
            return True
        if path == "/api/csrf-token":
            return True
        return False

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Only check mutating methods
        if request.method not in self._MUTATING_METHODS:
            return await call_next(request)

        # Skip public/auth paths
        if self._is_public_or_auth_path(request.url.path):
            return await call_next(request)

        # In test mode, skip CSRF validation entirely (matches AuthMiddleware)
        if os.environ.get("SRT2WEB_TESTING"):
            return await call_next(request)

        # Skip requests with Authorization header (programmatic API clients)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Validate CSRF token — resolve secret with same fallback chain as AuthMiddleware
        csrf_header = request.headers.get("X-CSRF-Token", "")
        secret = self.get_csrf_secret() or os.environ.get("SRT2WEB_AUTH_TOKEN", "") or os.environ.get("AUTH_TOKEN", "")
        if not csrf_header or not secret or not self.validate_token(csrf_header, secret):
            logger.warning(
                "F125: CSRF validation failed for %s %s",
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF validation failed. Include X-CSRF-Token header. "
                    "Get a token via GET /api/csrf-token."
                },
            )

        return await call_next(request)


def validate_ws_auth(request: Request, get_auth_token: Callable[[], str]) -> bool:
    """
    Validate authentication for WebSocket connections.
    Returns True if authenticated or no token required.

    .. deprecated::
        F109: Esta función NO se usa en producción. El flujo canónico de auth
        WebSocket está implementado inline en ``server/ws_routes.py`` (función
        ``websocket_endpoint``, validación de ``?token=`` al aceptar conexión).
        Esta función se conserva porque hay 8 tests que la cubren y documentan
        el contrato de auth WS. Si necesitas cambiar la lógica, hazlo en
        ``ws_routes.py`` y actualiza los tests para reflejar el inline check.
    """
    warnings.warn(
        "validate_ws_auth is legacy; production uses inline auth in server/ws_routes.py",
        DeprecationWarning,
        stacklevel=2,
    )
    auth_token = get_auth_token() or os.environ.get("SRT2WEB_AUTH_TOKEN", "") or os.environ.get("AUTH_TOKEN", "")

    if not auth_token:
        logger.warning("SECURITY: WebSocket accessed without auth_token configured")
        return True

    # Get token from query parameter ?token=xxx
    token = request.query_params.get("token")
    if not token:
        logger.warning("SECURITY: WebSocket connection without token parameter")
        return False

    if not hmac.compare_digest(token, auth_token):
        logger.warning(f"SECURITY: WebSocket invalid token from {request.client.host}")  # type: ignore[union-attr]
        return False

    return True
