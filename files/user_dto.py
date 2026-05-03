"""DTOs (Data Transfer Objects) de usuario.

Usan Pydantic v2 para validación automática de inputs y serialización
de outputs. No contienen lógica de negocio.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# ─── Request DTOs ─────────────────────────────────────────────────────────────


class UserCreateDTO(BaseModel):
    """Payload para crear un usuario."""

    email: EmailStr = Field(..., description="Email único del usuario")
    name: str = Field(..., min_length=2, max_length=120, description="Nombre completo")
    password: str = Field(..., min_length=8, description="Contraseña (mín. 8 chars)")

    @field_validator("name")
    @classmethod
    def name_no_whitespace_only(cls, v: str) -> str:
        """Rechaza nombres que son sólo espacios en blanco."""
        if not v.strip():
            raise ValueError("El nombre no puede ser sólo espacios.")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Valida fuerza mínima de contraseña."""
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número.")
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una mayúscula.")
        return v

    model_config = {"str_strip_whitespace": True}


class UserUpdateDTO(BaseModel):
    """Payload para actualizar un usuario (todos los campos opcionales)."""

    name: Optional[str] = Field(None, min_length=2, max_length=120)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("El nombre no puede estar vacío.")
        return v.strip() if v else v

    model_config = {"str_strip_whitespace": True}


class UserLoginDTO(BaseModel):
    """Payload para autenticación."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class PaginationParams(BaseModel):
    """Parámetros de paginación reutilizables."""

    skip: int = Field(default=0, ge=0, description="Registros a omitir")
    limit: int = Field(default=20, ge=1, le=100, description="Máx. registros")
    only_active: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_pagination(self) -> PaginationParams:
        if self.skip > 10_000:
            raise ValueError("skip no puede superar 10.000.")
        return self


# ─── Response DTOs ────────────────────────────────────────────────────────────


class UserResponseDTO(BaseModel):
    """Representación pública de un usuario (sin contraseña)."""

    id: int
    email: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponseDTO(BaseModel):
    """Respuesta paginada de lista de usuarios."""

    items: list[UserResponseDTO]
    total: int
    skip: int
    limit: int
    has_more: bool

    @classmethod
    def build(
        cls,
        items: list[UserResponseDTO],
        total: int,
        skip: int,
        limit: int,
    ) -> UserListResponseDTO:
        """Construye la respuesta paginada."""
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + len(items)) < total,
        )


class TokenResponseDTO(BaseModel):
    """Respuesta de autenticación con token JWT."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos hasta expiración")
