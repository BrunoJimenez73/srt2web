"""Dependencias de autenticación para inyección en FastAPI."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from src.application.dtos.user_dto import UserResponseDTO
from src.infrastructure.database.config import get_db_session
from src.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from src.infrastructure.security.password import JWTService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
_jwt_service = JWTService()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponseDTO:
    """Extrae y valida el usuario autenticado del token JWT.

    Raises:
        HTTPException 401: Si el token es inválido o el usuario no existe.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado o token expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = int(_jwt_service.get_subject(token))
    except (JWTError, ValueError):
        raise credentials_exception

    repo = SQLAlchemyUserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return UserResponseDTO.model_validate(user)
