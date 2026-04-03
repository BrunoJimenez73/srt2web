"""
FastAPI application for SRT2Web.

Serves the web GUI, HLS segments, and API endpoints.
"""

import os
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from server.api_routes import create_api_router
from server.ws_routes import create_ws_router
from server.webrtc_routes import create_webrtc_router
from server.security import (
    AuthMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RateLimiter,
    RequestSizeLimitMiddleware,
)

logger = logging.getLogger("srt2web.server")

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
FRONTEND_DIR = PROJECT_ROOT / "server" / "static"
WEB_DIR = PROJECT_ROOT / "web"


def create_app(app_context: dict) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        app_context: Shared context dict containing:
            - "config": ConfigManager instance
            - "pipeline": Pipeline instance
            - "srt_ingest": SRTIngest instance
            - "log_subscribers": list of WebSocket log subscribers
    """
    app = FastAPI(
        title="SRT2Web",
        description="Modular SRT Stream Processor",
        version="0.4.0",
    )

    config = app_context.get("config")

    # GZip compression for responses (min_size=1000 to compress responses > 1KB)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Request size limit - first after security headers
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size_bytes=config.get("server.max_request_size_mb", 1) * 1_048_576
        if config else 1_048_576,
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiting
    rate_limiter = RateLimiter(
        requests_per_minute=config.get("server.rate_limit_rpm", 60)
        if config else 60
    )
    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=rate_limiter,
        get_auth_token=lambda: config.get("server.auth_token", "") if config else "",
    )

    # Authentication
    app.add_middleware(
        AuthMiddleware,
        get_auth_token=lambda: config.get("server.auth_token", "") if config else "",
    )

    # CORS
    cors_origins = [
        "http://localhost:8080",
        "http://localhost:8089",
        "http://localhost:9999",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8089",
        "http://127.0.0.1:9999",
    ]
    if config:
        configured_origins = config.get("server.cors_origins", [])
        if configured_origins:
            cors_origins = configured_origins

    allowed_origins = []
    for origin in cors_origins:
        if "*" in origin:
            base = origin.replace(":*", "")
            for port in [3000, 5173, 8080, 8089, 8000, 9999]:
                allowed_origins.append(f"{base}:{port}")
        else:
            allowed_origins.append(origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        allow_credentials=True,
    )

    app.state.ctx = app_context

    api_router = create_api_router()
    app.include_router(api_router, prefix="/api")

    ws_router = create_ws_router()
    app.include_router(ws_router)

    webrtc_router = create_webrtc_router()
    app.include_router(webrtc_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    hls_dir = OUTPUT_DIR / "hls"
    hls_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/hls", StaticFiles(directory=str(hls_dir)), name="hls")

    if FRONTEND_DIR.exists():
        app.mount(
            "/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend"
        )

    @app.get("/")
    async def serve_index():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")

        index_path = WEB_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")

        return {"error": "index.html not found"}

    @app.get("/player")
    async def serve_player():
        player_path = FRONTEND_DIR / "player" / "index.html"
        if player_path.exists():
            return FileResponse(str(player_path), media_type="text/html")

        player_path = WEB_DIR / "player.html"
        if player_path.exists():
            return FileResponse(str(player_path), media_type="text/html")

        return {"error": "player.html not found"}

    @app.get("/webrtc-player")
    async def serve_webrtc_player():
        player_path = FRONTEND_DIR / "webrtc-player" / "index.html"
        if player_path.exists():
            return FileResponse(str(player_path), media_type="text/html")

        return {"error": "webrtc-player.html not found"}

    return app
