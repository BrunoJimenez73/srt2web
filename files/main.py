"""Punto de entrada de la aplicación FastAPI."""
from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from src.domain.exceptions import (
    DomainException,
    EmailAlreadyExistsError,
    UnauthorizedError,
    UserNotFoundError,
)
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.config import Base, engine
from src.presentation.api.routes import auth, health, users

logger = logging.getLogger(__name__)
_settings = get_settings()


# ─── Lifespan ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestiona el ciclo de vida de la aplicación."""
    logger.info("🚀 Iniciando %s v%s...", _settings.APP_NAME, _settings.APP_VERSION)

    # Crear tablas en desarrollo (en producción usar Alembic)
    if _settings.is_development:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    logger.info("🛑 Apagando la aplicación...")
    await engine.dispose()


# ─── App ──────────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Factory de la aplicación FastAPI.

    Centraliza toda la configuración para facilitar tests.
    """
    app = FastAPI(
        title=_settings.APP_NAME,
        version=_settings.APP_VERSION,
        description="API REST moderna con Clean Architecture.",
        docs_url="/docs" if not _settings.is_production else None,
        redoc_url="/redoc" if not _settings.is_production else None,
        openapi_url="/openapi.json" if not _settings.is_production else None,
        lifespan=lifespan,
    )

    _register_middleware(app)
    _register_exception_handlers(app)
    _register_routers(app)

    return app


# ─── Middleware ───────────────────────────────────────────────────────────────


def _register_middleware(app: FastAPI) -> None:
    """Registra todos los middleware."""

    # Compresión gzip (reducir tamaño de respuestas)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Hosts permitidos (evitar host header injection)
    if _settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com", "*.example.com"],
        )

    # Middleware de logging de requests
    @app.middleware("http")
    async def log_requests(request: Request, call_next: object) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[operator]
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "HTTP %s %s → %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        return response

    # Security headers
    @app.middleware("http")
    async def security_headers(request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if _settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# ─── Exception handlers ───────────────────────────────────────────────────────


def _register_exception_handlers(app: FastAPI) -> None:
    """Centraliza el manejo de errores."""

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(_: Request, exc: UserNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(EmailAlreadyExistsError)
    async def email_exists_handler(_: Request, exc: EmailAlreadyExistsError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(_: Request, exc: UnauthorizedError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(DomainException)
    async def domain_exception_handler(_: Request, exc: DomainException) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": exc.code, "message": exc.message},
        )


# ─── Routers ──────────────────────────────────────────────────────────────────


def _register_routers(app: FastAPI) -> None:
    """Registra todos los routers de la API."""
    app.include_router(health.router, tags=["Health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])


# ─── Instancia global ─────────────────────────────────────────────────────────

app = create_app()
