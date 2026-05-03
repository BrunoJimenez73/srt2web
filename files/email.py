"""Value Objects del dominio."""
from __future__ import annotations

import re
from dataclasses import dataclass

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


@dataclass(frozen=True)
class Email:
    """Value Object para emails válidos.

    Inmutable y auto-validado al crear.
    Dos instancias con el mismo valor son iguales (por ser frozen dataclass).

    Attributes:
        value: Dirección de email normalizada (lowercase).

    Example:
        >>> email = Email("USER@EXAMPLE.COM")
        >>> email.value
        'user@example.com'
        >>> Email("no-es-un-email")
        ValueError: Email inválido: no-es-un-email
    """

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _EMAIL_REGEX.match(normalized):
            raise ValueError(f"Email inválido: {self.value}")
        # frozen=True impide asignación directa; usamos object.__setattr__
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class UserId:
    """Value Object para identificadores de usuario.

    Attributes:
        value: ID entero positivo.
    """

    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError(f"UserId debe ser positivo, recibido: {self.value}")

    def __str__(self) -> str:
        return str(self.value)
