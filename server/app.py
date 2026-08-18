"""
FastAPI application for SRT2Web.

Serves the web GUI, HLS segments, and API endpoints.
"""

import asyncio
import logging
import os
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles variant that disables every layer of HTTP caching.

    Used for live HLS segments and subtitle files: their filenames are reused
    across pipeline sessions (``seg_000000.ts``, ``subs.vtt``…), so any cached
    response from a previous session would replay stale content in the player.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        if path.endswith(".ts") and self.directory:
            try:
                full_path = os.path.join(str(self.directory), path)
                response.headers["Content-Length"] = str(os.path.getsize(full_path))
                if "content-encoding" in response.headers:
                    del response.headers["content-encoding"]
            except (OSError, TypeError, KeyError):
                pass
        return response


from server.api_routes import create_api_router  # noqa: E402
from server.ctx import get_auth_token  # noqa: E402
from server.routes.auth import router as auth_router  # noqa: E402
from server.routes.metrics import router as metrics_router  # noqa: E402
from server.routes.recordings import router as recordings_router  # noqa: E402
from server.security import (  # noqa: E402
    AuthMiddleware,
    RateLimiter,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from server.webrtc_routes import create_webrtc_router  # noqa: E402
from server.ws_routes import create_ws_router  # noqa: E402

logger = logging.getLogger("srt2web.server")

from core.paths import get_output_dir, get_project_root, get_static_dir  # noqa: E402

PROJECT_ROOT = get_project_root()
OUTPUT_DIR = get_output_dir()
FRONTEND_DIR = get_static_dir()
WEB_DIR = PROJECT_ROOT / "web"


def _get_version() -> str:
    """Read version from pyproject.toml via importlib.metadata."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("srt2web")
    except (PackageNotFoundError, ImportError):
        return "0.6.8"


_DOCS_STUB_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sección en construcción | SRT2Web Docs</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: #0b0b10;
    color: #e0e0e8;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
  .card {
    max-width: 480px;
    background: #1a1a26;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 40px 32px;
    text-align: center;
  }
  .icon { font-size: 56px; margin-bottom: 16px; }
  h1 {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 12px;
    color: #fff;
  }
  p {
    color: #8888a0;
    line-height: 1.6;
    margin-bottom: 24px;
    font-size: 14px;
  }
  .actions { display: flex; gap: 12px; justify-content: center; }
  .btn {
    display: inline-flex;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.2s;
  }
  .btn-primary { background: #6366f1; color: #fff; }
  .btn-primary:hover { background: #7c7ff7; }
</style>
</head>
<body>
<div class="card">
  <div class="icon">📄</div>
  <h1>Sección en construcción</h1>
  <p>Esta página de la documentación aún no se ha publicado.
     Vuelve al inicio para explorar las secciones disponibles.</p>
  <div class="actions">
    <a href="/docs/" class="btn btn-primary">← Volver al inicio</a>
  </div>
</div>
</body>
</html>"""


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

    allowed_origins: list[str] = []
    origin_regex_parts: list[str] = []
    for origin in cors_origins:
        if "*" in origin:
            escaped = re.escape(origin).replace(r"\*", r"[^:]*")
            origin_regex_parts.append(escaped)
        else:
            allowed_origins.append(origin)

    origin_regex = "|".join(origin_regex_parts) if origin_regex_parts else None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins if allowed_origins else [],
        allow_origin_regex=origin_regex,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-CSRF-Token"],
        allow_credentials=True,
        max_age=3600,
    )

    @app.middleware("http")
    async def add_vary_origin(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        if "origin" in request.headers:
            vary = response.headers.get("vary", "")
            if "origin" not in vary.lower():
                response.headers["Vary"] = ", ".join(filter(None, [vary, "Origin"]))
        return response

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
        get_auth_token=lambda: get_auth_token(config),
    )

    # Authentication
    app.add_middleware(
        AuthMiddleware,
        get_auth_token=lambda: get_auth_token(config),
    )

    # F125: CSRF protection (innermost, runs after auth).
    # Enabled now — the frontend sends X-CSRF-Token on mutating requests.
    # See /api/auth/csrf-token endpoint.
    from server.security import CsrfMiddleware

    app.add_middleware(
        CsrfMiddleware,
        get_csrf_secret=lambda: get_auth_token(config),
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
    async def readiness() -> Response:
        """Readiness probe for deployments.
        Returns 200 only when the pipeline is running and producing output.
        """
        from fastapi.responses import JSONResponse

        ctx = app.state.ctx
        pipeline = ctx.get("pipeline")
        if not pipeline:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "no_pipeline"},
            )
        if not pipeline.is_running:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "pipeline_not_running"},
            )
        status = pipeline.get_status()
        state = status.get("state", "idle")
        if state != "running":
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": f"pipeline_state_{state}"},
            )
        return JSONResponse(content={"status": "ready", "state": state, "chunks_processed": pipeline.chunks_processed})

    @app.get("/live")
    async def liveness() -> dict[str, Any]:
        """Liveness probe for deployments."""
        return {"status": "alive"}

    hls_dir = OUTPUT_DIR / "hls"
    hls_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Mounting /hls at: {hls_dir}")
    app.mount("/hls", NoCacheStaticFiles(directory=str(hls_dir), html=False), name="hls")

    subtitles_dir = OUTPUT_DIR / "subtitles"
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Mounting /subtitles at: {subtitles_dir}")
    app.mount(
        "/subtitles",
        NoCacheStaticFiles(directory=str(subtitles_dir), html=False),
        name="subtitles",
    )

    # ── Explicit page routes (registered BEFORE the static mount so they win
    # the routing race against the catch-all `app.mount("/", ...)` below).
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

    @app.get("/docs/{path:path}")
    async def serve_docs_fallback(path: str) -> Any:
        """Serve a 'coming soon' page for any docs subpath that doesn't have
        its own static HTML yet. The main /docs/ page is served by the
        static mount; this only fires for /docs/anything-else."""
        # F151: Prevent path traversal — reject any path with '..' or absolute components
        from pathlib import PurePosixPath

        sanitized = PurePosixPath(path)
        if ".." in sanitized.parts or sanitized.is_absolute():
            return HTMLResponse(content="Not found", status_code=404)
        docs_dir = FRONTEND_DIR / "docs"
        target = (docs_dir / path / "index.html").resolve()
        if target.exists() and str(target).startswith(str(docs_dir.resolve())):
            return FileResponse(str(target), media_type="text/html")
        target = (docs_dir / f"{path}.html").resolve()
        if target.exists() and str(target).startswith(str(docs_dir.resolve())):
            return FileResponse(str(target), media_type="text/html")

        return HTMLResponse(
            content=_DOCS_STUB_HTML,
            status_code=200,
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
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

    return app
