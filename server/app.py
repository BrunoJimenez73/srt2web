"""
FastAPI application for SRT2Web.

Serves the web GUI, HLS segments, and API endpoints.
"""

import os
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from server.api_routes import create_api_router
from server.ws_routes import create_ws_router

logger = logging.getLogger("srt2web.server")

# Resolve paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
WEB_DIR = PROJECT_ROOT / "web"
OUTPUT_DIR = PROJECT_ROOT / "output"


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
        version="0.1.0",
    )

    # CORS - use configurable origins or default to restrictive list
    config = app_context.get("config")
    cors_origins = [
        "http://localhost:8080",
        "http://localhost:8089",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8089",
    ]
    if config:
        configured_origins = config.get("server.cors_origins", [])
        if configured_origins:
            cors_origins = configured_origins

    # Replace wildcards with actual allowed origins for development
    allowed_origins = []
    for origin in cors_origins:
        if "*" in origin:
            # Convert localhost:* patterns to actual available ports
            base = origin.replace(":*", "")
            for port in [3000, 5173, 8080, 8089, 8000]:
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

    # Store context for route handlers
    app.state.ctx = app_context

    # API routes
    api_router = create_api_router()
    app.include_router(api_router, prefix="/api")

    # WebSocket routes
    ws_router = create_ws_router()
    app.include_router(ws_router)

    # Serve HLS output files
    hls_dir = OUTPUT_DIR / "hls"
    hls_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/hls", StaticFiles(directory=str(hls_dir)), name="hls")

    # Serve static web files (CSS, JS)
    if WEB_DIR.exists():
        app.mount("/css", StaticFiles(directory=str(WEB_DIR / "css")), name="css")
        app.mount("/js", StaticFiles(directory=str(WEB_DIR / "js")), name="js")

    # Root — serve index.html
    @app.get("/")
    async def serve_index():
        index_path = WEB_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")
        return {"error": "index.html not found"}

    # Clean player page
    @app.get("/player")
    async def serve_player():
        player_path = WEB_DIR / "player.html"
        if player_path.exists():
            return FileResponse(str(player_path), media_type="text/html")
        return {"error": "player.html not found"}

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
