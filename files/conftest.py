"""Fixtures globales de pytest."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from src.domain.entities.user import User
from src.infrastructure.database.config import Base, get_db_session
from src.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from src.infrastructure.security.password import BcryptPasswordHasher
from src.presentation.main import create_app

# ─── Database fixtures ────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Motor SQLite en memoria (compartido por toda la sesión de tests)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Sesión de BD en transacción que se revierte al finalizar cada test."""
    async with test_engine.connect() as conn:
        await conn.begin_nested()
        session_factory = async_sessionmaker(bind=conn, expire_on_commit=False)
        async with session_factory() as session:
            yield session
            await session.rollback()


# ─── Repository fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def user_repository(db_session: AsyncSession) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(db_session)


@pytest.fixture
def password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


# ─── Domain fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_user() -> User:
    return User(
        email="test@example.com",
        name="Test User",
        password_hash=BcryptPasswordHasher().hash("Password1"),
    )


@pytest.fixture
def another_user() -> User:
    return User(
        email="other@example.com",
        name="Other User",
        password_hash=BcryptPasswordHasher().hash("Password1"),
    )


# ─── HTTP client ──────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP asíncrono con BD de test inyectada."""
    app = create_app()

    # Sobreescribir la dependencia de BD para usar la BD de test
    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
