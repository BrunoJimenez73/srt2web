"""Router de usuarios."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.application.dtos.user_dto import (
    PaginationParams,
    UserCreateDTO,
    UserListResponseDTO,
    UserResponseDTO,
    UserUpdateDTO,
)
from src.application.services.user_service import UserService
from src.infrastructure.database.config import get_db_session
from src.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from src.infrastructure.security.password import BcryptPasswordHasher
from src.presentation.api.dependencies import get_current_user

router = APIRouter()


# ─── DI helpers ───────────────────────────────────────────────────────────────


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserService:
    """Construye el UserService con sus dependencias."""
    repo = SQLAlchemyUserRepository(session)
    hasher = BcryptPasswordHasher()
    return UserService(user_repo=repo, password_hasher=hasher)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
CurrentUser = Annotated[UserResponseDTO, Depends(get_current_user)]


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=UserResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
)
async def create_user(
    dto: UserCreateDTO,
    service: UserServiceDep,
) -> UserResponseDTO:
    """Crea un nuevo usuario en el sistema.

    - **email**: Debe ser único en el sistema.
    - **name**: Mínimo 2 caracteres.
    - **password**: Mínimo 8 chars, al menos 1 número y 1 mayúscula.
    """
    return await service.create_user(dto)


@router.get(
    "/",
    response_model=UserListResponseDTO,
    summary="Listar usuarios",
)
async def list_users(
    params: Annotated[PaginationParams, Depends()],
    service: UserServiceDep,
    _current: CurrentUser,
) -> UserListResponseDTO:
    """Lista usuarios con paginación. Requiere autenticación."""
    return await service.list_users(params)


@router.get(
    "/{user_id}",
    response_model=UserResponseDTO,
    summary="Obtener usuario por ID",
)
async def get_user(
    user_id: int,
    service: UserServiceDep,
    _current: CurrentUser,
) -> UserResponseDTO:
    """Obtiene los datos de un usuario por su ID."""
    return await service.get_user(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponseDTO,
    summary="Actualizar usuario",
)
async def update_user(
    user_id: int,
    dto: UserUpdateDTO,
    service: UserServiceDep,
    current: CurrentUser,
) -> UserResponseDTO:
    """Actualiza datos de un usuario. Solo el propio usuario o admin."""
    if current.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return await service.update_user(user_id, dto)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario",
)
async def delete_user(
    user_id: int,
    service: UserServiceDep,
    current: CurrentUser,
) -> None:
    """Elimina un usuario. Solo el propio usuario o admin."""
    if current.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    await service.delete_user(user_id)
