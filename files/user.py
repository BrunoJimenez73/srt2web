"""Entidad de dominio: User."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Entidad de usuario del dominio.

    Representa un usuario del sistema con sus datos esenciales.
    Esta entidad es independiente de la infraestructura (no conoce
    SQLAlchemy, FastAPI ni ningún framework externo).

    Attributes:
        email: Dirección de correo electrónico única del usuario.
        name: Nombre completo del usuario.
        id: Identificador único asignado al persistir en BD.
        password_hash: Hash bcrypt de la contraseña (opcional en lectura).
        is_active: Estado activo/inactivo del usuario.
        created_at: Fecha de creación.
        updated_at: Fecha de última actualización.
    """

    email: str
    name: str
    id: Optional[int] = field(default=None)
    password_hash: Optional[str] = field(default=None, repr=False)
    is_active: bool = field(default=True)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validaciones de dominio al construir la entidad."""
        if not self.email or not self.email.strip():
            raise ValueError("El email no puede estar vacío.")
        if not self.name or not self.name.strip():
            raise ValueError("El nombre no puede estar vacío.")
        self.email = self.email.strip().lower()
        self.name = self.name.strip()

    def deactivate(self) -> None:
        """Desactiva el usuario."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activa el usuario."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def update_name(self, new_name: str) -> None:
        """Actualiza el nombre del usuario.

        Args:
            new_name: Nuevo nombre a asignar.

        Raises:
            ValueError: Si el nombre es vacío.
        """
        if not new_name.strip():
            raise ValueError("El nombre no puede estar vacío.")
        self.name = new_name.strip()
        self.updated_at = datetime.utcnow()
