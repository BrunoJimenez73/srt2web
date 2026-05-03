"""Tests unitarios del UserService."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from src.application.dtos.user_dto import (
    PaginationParams,
    UserCreateDTO,
    UserUpdateDTO,
)
from src.application.services.user_service import UserService
from src.domain.entities.user import User
from src.domain.exceptions import (
    EmailAlreadyExistsError,
    UserNotFoundError,
)
from src.infrastructure.security.password import BcryptPasswordHasher

# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_service(
    existing_user: User | None = None,
    user_list: list[User] | None = None,
    total: int = 0,
) -> UserService:
    """Construye un UserService con repositorio mockeado."""
    repo = AsyncMock()
    repo.get_by_email.return_value = existing_user
    repo.get_by_id.return_value = existing_user
    repo.save.side_effect = lambda u: (setattr(u, "id", 1) or u)
    repo.list_all.return_value = user_list or []
    repo.count.return_value = total

    hasher = BcryptPasswordHasher()
    return UserService(user_repo=repo, password_hasher=hasher)


# ─── create_user ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCreateUser:
    async def test_success(self) -> None:
        """Crear usuario con datos válidos retorna DTO."""
        service = make_service(existing_user=None)
        dto = UserCreateDTO(email="new@example.com", name="New User", password="Pass1234")

        result = await service.create_user(dto)

        assert result.email == "new@example.com"
        assert result.name == "New User"
        assert result.id == 1

    async def test_raises_if_email_exists(self) -> None:
        """Si el email ya existe, lanza EmailAlreadyExistsError."""
        existing = User(email="taken@example.com", name="Existing")
        service = make_service(existing_user=existing)
        dto = UserCreateDTO(email="taken@example.com", name="X", password="Pass1234")

        with pytest.raises(EmailAlreadyExistsError) as exc_info:
            await service.create_user(dto)

        assert exc_info.value.email == "taken@example.com"

    async def test_password_is_hashed(self) -> None:
        """La contraseña se guarda hasheada, no en texto plano."""
        saved_user: list[User] = []
        repo = AsyncMock()
        repo.get_by_email.return_value = None

        def capture_save(u: User) -> User:
            u.id = 99
            saved_user.append(u)
            return u

        repo.save.side_effect = capture_save
        service = UserService(user_repo=repo, password_hasher=BcryptPasswordHasher())

        dto = UserCreateDTO(email="a@b.com", name="A", password="Pass1234")
        await service.create_user(dto)

        assert saved_user[0].password_hash != "Pass1234"
        assert saved_user[0].password_hash is not None


# ─── get_user ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetUser:
    async def test_found(self) -> None:
        user = User(email="u@e.com", name="U", id=5)
        service = make_service(existing_user=user)

        result = await service.get_user(5)

        assert result.id == 5
        assert result.email == "u@e.com"

    async def test_not_found(self) -> None:
        service = make_service(existing_user=None)

        with pytest.raises(UserNotFoundError) as exc_info:
            await service.get_user(999)

        assert exc_info.value.identifier == 999


# ─── list_users ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListUsers:
    async def test_returns_paginated_response(self) -> None:
        users = [User(email=f"u{i}@e.com", name=f"User {i}", id=i) for i in range(3)]
        service = make_service(user_list=users, total=10)
        params = PaginationParams(skip=0, limit=3)

        result = await service.list_users(params)

        assert len(result.items) == 3
        assert result.total == 10
        assert result.has_more is True


# ─── update_user ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestUpdateUser:
    async def test_update_name(self) -> None:
        user = User(email="u@e.com", name="Old Name", id=1)
        service = make_service(existing_user=user)

        result = await service.update_user(1, UserUpdateDTO(name="New Name"))

        assert result.name == "New Name"

    async def test_not_found_raises(self) -> None:
        service = make_service(existing_user=None)

        with pytest.raises(UserNotFoundError):
            await service.update_user(99, UserUpdateDTO(name="X"))


# ─── Domain value objects ─────────────────────────────────────────────────────


class TestUserEntity:
    def test_email_normalized_to_lowercase(self) -> None:
        user = User(email="UPPER@EXAMPLE.COM", name="Test")
        assert user.email == "upper@example.com"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="nombre"):
            User(email="a@b.com", name="  ")

    def test_deactivate_sets_is_active_false(self) -> None:
        user = User(email="a@b.com", name="Test")
        user.deactivate()
        assert user.is_active is False

    def test_activate_sets_is_active_true(self) -> None:
        user = User(email="a@b.com", name="Test", is_active=False)
        user.activate()
        assert user.is_active is True
