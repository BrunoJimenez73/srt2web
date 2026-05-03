"""Interfaz abstracta del repositorio de usuarios."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Optional

from src.domain.entities.user import User


class IUserRepository(ABC):
    """Puerto (interfaz) para el repositorio de usuarios.

    Define las operaciones que la capa de aplicación puede realizar
    sobre usuarios, sin acoplarse a ningún detalle de infraestructura.
    """

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Devuelve un usuario por su ID, o None si no existe.

        Args:
            user_id: Identificador único del usuario.

        Returns:
            User si se encontró, None en caso contrario.
        """

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Devuelve un usuario por su email, o None si no existe.

        Args:
            email: Correo electrónico del usuario.

        Returns:
            User si se encontró, None en caso contrario.
        """

    @abstractmethod
    async def list_all(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        only_active: bool = False,
    ) -> Sequence[User]:
        """Lista usuarios con paginación.

        Args:
            skip: Número de registros a omitir (offset).
            limit: Número máximo de registros a retornar.
            only_active: Si True, retorna sólo usuarios activos.

        Returns:
            Secuencia (potencialmente vacía) de usuarios.
        """

    @abstractmethod
    async def save(self, user: User) -> User:
        """Persiste un usuario nuevo o actualiza uno existente.

        Si user.id es None, crea un nuevo registro y asigna el id.
        Si user.id existe, actualiza el registro correspondiente.

        Args:
            user: Entidad de usuario a persistir.

        Returns:
            User con id asignado (o actualizado).
        """

    @abstractmethod
    async def delete(self, user_id: int) -> None:
        """Elimina (o desactiva) un usuario.

        Args:
            user_id: ID del usuario a eliminar.

        Raises:
            UserNotFoundError: Si el usuario no existe.
        """

    @abstractmethod
    async def count(self, *, only_active: bool = False) -> int:
        """Retorna el total de usuarios.

        Args:
            only_active: Si True, cuenta sólo usuarios activos.

        Returns:
            Número total de usuarios.
        """
