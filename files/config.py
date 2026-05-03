"""Configuración de base de datos (SQLAlchemy async)."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from src.infrastructure.config.settings import get_settings

_settings = get_settings()


# ─── Engine ───────────────────────────────────────────────────────────────────


def _build_engine() -> AsyncEngine:
    """Construye el motor de BD con configuración óptima."""
    return create_async_engine(
        _settings.DATABASE_URL,
        echo=_settings.DB_ECHO,
        pool_size=_settings.DB_POOL_SIZE,
        max_overflow=_settings.DB_MAX_OVERFLOW,
        pool_recycle=_settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,  # Detecta conexiones muertas
    )


engine: AsyncEngine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ─── Base declarativa ─────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    """Clase base para todos los modelos ORM."""

    pass


# ─── Dependency (FastAPI) ─────────────────────────────────────────────────────


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Proveedor de sesión de BD para inyección de dependencias en FastAPI.

    Hace commit si no hay excepción, rollback en caso contrario.
    Siempre cierra la sesión.

    Yields:
        AsyncSession: Sesión de base de datos activa.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
