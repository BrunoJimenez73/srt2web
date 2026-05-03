"""Servicio de aplicación: UserService.

Orquesta los casos de uso del dominio de usuarios. Depende de
abstracciones (IUserRepository), no de implementaciones concretas.
"""
from __future__ import annotations

import logging

from src.application.dtos.user_dto import (
    PaginationParams,
    UserCreateDTO,
    UserListResponseDTO,
    UserResponseDTO,
    UserUpdateDTO,
)
from src.domain.entities.user import User
from src.domain.exceptions import (
    EmailAlreadyExistsError,
    UserNotFoundError,
)
from src.domain.repositories.user_repository import IUserRepository
from src.infrastructure.security.password import IPasswordHasher

logger = logging.getLogger(__name__)


class UserService:
    """Servicio que implementa los casos de uso de gestión de usuarios.

    Args:
        user_repo: Repositorio de usuarios (inyectado).
        password_hasher: Servicio de hashing de contraseñas (inyectado).
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
    ) -> None:
        self._repo = user_repo
        self._hasher = password_hasher

    # ── Creación ──────────────────────────────────────────────────────────────

    async def create_user(self, dto: UserCreateDTO) -> UserResponseDTO:
        """Crea un nuevo usuario.

        Args:
            dto: Datos validados del nuevo usuario.

        Returns:
            Representación pública del usuario creado.

        Raises:
            EmailAlreadyExistsError: Si el email ya está registrado.
        """
        logger.info("Creando usuario con email=%s", dto.email)

        existing = await self._repo.get_by_email(dto.email)
        if existing is not None:
            raise EmailAlreadyExistsError(dto.email)

        user = User(
            email=dto.email,
            name=dto.name,
            password_hash=self._hasher.hash(dto.password),
        )
        saved = await self._repo.save(user)

        logger.info("Usuario creado con id=%s", saved.id)
        return UserResponseDTO.model_validate(saved)

    # ── Consulta ──────────────────────────────────────────────────────────────

    async def get_user(self, user_id: int) -> UserResponseDTO:
        """Obtiene un usuario por su ID.

        Raises:
            UserNotFoundError: Si no existe ningún usuario con ese ID.
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return UserResponseDTO.model_validate(user)

    async def list_users(self, params: PaginationParams) -> UserListResponseDTO:
        """Lista usuarios con paginación.

        Args:
            params: Parámetros de paginación y filtros.

        Returns:
            Respuesta paginada de usuarios.
        """
        users = await self._repo.list_all(
            skip=params.skip,
            limit=params.limit,
            only_active=params.only_active,
        )
        total = await self._repo.count(only_active=params.only_active)
        items = [UserResponseDTO.model_validate(u) for u in users]

        return UserListResponseDTO.build(
            items=items,
            total=total,
            skip=params.skip,
            limit=params.limit,
        )

    # ── Actualización ─────────────────────────────────────────────────────────

    async def update_user(self, user_id: int, dto: UserUpdateDTO) -> UserResponseDTO:
        """Actualiza datos de un usuario.

        Raises:
            UserNotFoundError: Si el usuario no existe.
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        if dto.name is not None:
            user.update_name(dto.name)
        if dto.is_active is not None:
            user.activate() if dto.is_active else user.deactivate()

        saved = await self._repo.save(user)
        logger.info("Usuario id=%s actualizado", user_id)
        return UserResponseDTO.model_validate(saved)

    # ── Eliminación ───────────────────────────────────────────────────────────

    async def delete_user(self, user_id: int) -> None:
        """Elimina (desactiva) un usuario.

        Raises:
            UserNotFoundError: Si el usuario no existe.
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        await self._repo.delete(user_id)
        logger.info("Usuario id=%s eliminado", user_id)
