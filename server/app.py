"""
FastAPI application for SRT2Web.

Serves the web GUI, HLS segments, and API endpoints.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.api_routes import create_api_router
from server.routes.auth import router as auth_router
from server.routes.metrics import router as metrics_router
from server.routes.recordings import router as recordings_router
from server.security import (
    AuthMiddleware,
    RateLimiter,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from server.webrtc_routes import create_webrtc_router
from server.ws_routes import create_ws_router

logger = logging.getLogger("srt2web.server")

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
FRONTEND_DIR = PROJECT_ROOT / "server" / "static"
WEB_DIR = PROJECT_ROOT / "web"


def _get_version() -> str:
    """Read version from pyproject.toml via importlib.metadata."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("srt2web")
    except (PackageNotFoundError, ImportError):
        return "0.6.8"


def create_app(app_context: dict[str, Any]) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        app_context: Shared context dict containing:
            - "config": ConfigManager instance
            - "pipeline": Pipeline instance
            - "input_source": input source instance
            - "log_broadcast": broadcast callable
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Gestiona el ciclo de vida del pipeline junto con FastAPI."""
        # Setup log_broadcaster loop for WebSocket broadcasting
        from server.ws_routes import log_broadcaster

        try:
            loop = asyncio.get_running_loop()
            log_broadcaster.set_loop(loop)
            logger.info("Log broadcaster event loop configured")
        except RuntimeError:
            logger.debug("No running loop during startup")

        # Setup output health broadcaster
        from core.output_sink import set_output_health_broadcaster

        set_output_health_broadcaster(log_broadcaster)

        # No arrancamos el pipeline aquí — lo arranca el usuario desde la UI.
        # Solo nos aseguramos de hacer shutdown limpio al cerrar.
        yield
        # Shutdown: detener pipeline si está corriendo
        pipeline = app_context.get("pipeline")
        if pipeline and pipeline.is_running:
            try:
                await pipeline.stop()
            except Exception as e:
                logger.error(f"Error stopping pipeline on shutdown: {e}")

    app = FastAPI(
        title="SRT2Web",
        description="Modular SRT Stream Processor",
        version=_get_version(),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    config = app_context.get("config")

    # CORS must be the outermost middleware (executes before auth/rate-limit)
    cors_origins = []
    if config:
        cors_origins = config.get("server.cors_origins", [])
    if not cors_origins:
        from core.config_schema import ServerConfig

        cors_origins = ServerConfig().cors_origins

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

    # GZip compression for responses (min_size=1000 to compress responses > 1KB)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Request size limit
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size_bytes=config.get("server.max_request_size_mb", 1) * 1_048_576 if config else 1_048_576,
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiting
    rate_limiter = RateLimiter(requests_per_minute=config.get("server.rate_limit_rpm", 60) if config else 60)
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

    app.state.ctx = app_context

    api_router = create_api_router()
    app.include_router(api_router, prefix="/api")

    ws_router = create_ws_router()
    app.include_router(ws_router)

    webrtc_router = create_webrtc_router()
    app.include_router(webrtc_router)

    app.include_router(recordings_router, prefix="/api")
    app.include_router(metrics_router)
    app.include_router(auth_router, prefix="/api")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/ready")
    async def readiness() -> dict[str, Any]:
        """Readiness probe for deployments."""
        ctx = app.state.ctx
        pipeline = ctx.get("pipeline")
        if pipeline and pipeline.is_running:
            return {"status": "ready"}
        # If pipeline not running, still return ready but maybe with warning?
        # For simplicity, return ready anyway.
        return {"status": "ready"}

    @app.get("/live")
    async def liveness() -> dict[str, Any]:
        """Liveness probe for deployments."""
        return {"status": "alive"}

    hls_dir = OUTPUT_DIR / "hls"
    hls_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Mounting /hls at: {hls_dir}")
    app.mount("/hls", StaticFiles(directory=str(hls_dir), html=False), name="hls")

    subtitles_dir = OUTPUT_DIR / "subtitles"
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Mounting /subtitles at: {subtitles_dir}")
    app.mount(
        "/subtitles",
        StaticFiles(directory=str(subtitles_dir), html=False),
        name="subtitles",
    )

    if FRONTEND_DIR.exists():
        static_files = StaticFiles(directory=str(FRONTEND_DIR), html=True)

        async def frontend_scope_aware(scope: Any, receive: Any, send: Any) -> None:
            if scope["type"] == "websocket":
                # WebSocket connections should be handled by websocket routes
                # Close the connection without accepting (let websocket routes handle it)
                try:
                    await send({"type": "websocket.close", "code": 1003})
                except Exception as e:
                    logger.debug("Suppressed error: %s", e, exc_info=True)
                return
            await static_files(scope, receive, send)

        app.mount("/", frontend_scope_aware, name="frontend")

    @app.get("/")
    async def serve_index() -> Any:
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")

        index_path = WEB_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")

        return {"error": "index.html not found"}

    @app.get("/player")
    async def serve_player() -> Any:
        player_path = FRONTEND_DIR / "player" / "index.html"
        if player_path.exists():
            return FileResponse(str(player_path), media_type="text/html")

        player_path = WEB_DIR / "player.html"
        if player_path.exists():
            return FileResponse(str(player_path), media_type="text/html")

        return {"error": "player.html not found"}

    @app.get("/webrtc-player")
    async def serve_webrtc_player() -> Any:
        player_path = FRONTEND_DIR / "webrtc-player" / "index.html"
        if player_path.exists():
            return FileResponse(str(player_path), media_type="text/html")

        return {"error": "webrtc-player.html not found"}

    return app
