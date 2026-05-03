"""Implementación SQLAlchemy del IUserRepository."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.user import User
from src.domain.exceptions import UserNotFoundError
from src.domain.repositories.user_repository import IUserRepository
from src.infrastructure.database.models.user_model import UserModel


class SQLAlchemyUserRepository(IUserRepository):
    """Adaptador: implementa IUserRepository usando SQLAlchemy async.

    Args:
        session: Sesión de BD inyectada (gestionada externamente).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        """Mapea fila de BD → entidad de dominio."""
        user = User.__new__(User)  # Evita validaciones del __post_init__
        user.id = model.id
        user.email = model.email
        user.name = model.name
        user.password_hash = model.password_hash
        user.is_active = model.is_active
        user.created_at = model.created_at
        user.updated_at = model.updated_at
        return user

    @staticmethod
    def _to_model(user: User) -> UserModel:
        """Mapea entidad de dominio → fila de BD (para insert)."""
        return UserModel(
            email=user.email,
            name=user.name,
            password_hash=user.password_hash or "",
            is_active=user.is_active,
        )

    # ── IUserRepository ───────────────────────────────────────────────────────

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self._session.get(UserModel, user_id)
        return self._to_domain(result) if result else None

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.email == email.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_all(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        only_active: bool = False,
    ) -> Sequence[User]:
        stmt = select(UserModel).offset(skip).limit(limit).order_by(UserModel.id)
        if only_active:
            stmt = stmt.where(UserModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def save(self, user: User) -> User:
        if user.id is None:
            # INSERT
            model = self._to_model(user)
            self._session.add(model)
            await self._session.flush()  # Obtiene el id sin commit
            user.id = model.id
        else:
            # UPDATE
            model = await self._session.get(UserModel, user.id)
            if model is None:
                raise UserNotFoundError(user.id)
            model.name = user.name
            model.is_active = user.is_active
            model.password_hash = user.password_hash or model.password_hash
            await self._session.flush()
        return user

    async def delete(self, user_id: int) -> None:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            raise UserNotFoundError(user_id)
        await self._session.delete(model)
        await self._session.flush()

    async def count(self, *, only_active: bool = False) -> int:
        stmt = select(func.count()).select_from(UserModel)
        if only_active:
            stmt = stmt.where(UserModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalar_one()
