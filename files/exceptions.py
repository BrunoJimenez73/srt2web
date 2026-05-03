"""Excepciones del dominio del proyecto.

Jerarquía:
    DomainException
    ├── UserNotFoundError
    ├── EmailAlreadyExistsError
    ├── InvalidCredentialsError
    ├── UserInactiveError
    └── ValidationError
        └── InvalidEmailError
"""
from __future__ import annotations


class DomainException(Exception):
    """Excepción base de todas las excepciones del dominio.

    Permite capturar cualquier error de negocio con un solo except.
    """

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


# ─── User exceptions ──────────────────────────────────────────────────────────


class UserNotFoundError(DomainException):
    """Se lanza cuando no se encuentra un usuario."""

    def __init__(self, identifier: str | int) -> None:
        super().__init__(
            message=f"Usuario no encontrado: {identifier}",
            code="USER_NOT_FOUND",
        )
        self.identifier = identifier


class EmailAlreadyExistsError(DomainException):
    """Se lanza cuando el email ya está registrado."""

    def __init__(self, email: str) -> None:
        super().__init__(
            message=f"El email ya está en uso: {email}",
            code="EMAIL_ALREADY_EXISTS",
        )
        self.email = email


class InvalidCredentialsError(DomainException):
    """Se lanza cuando las credenciales de autenticación son incorrectas."""

    def __init__(self) -> None:
        super().__init__(
            message="Credenciales incorrectas.",
            code="INVALID_CREDENTIALS",
        )


class UserInactiveError(DomainException):
    """Se lanza cuando se intenta operar sobre un usuario inactivo."""

    def __init__(self, user_id: int) -> None:
        super().__init__(
            message=f"El usuario {user_id} está inactivo.",
            code="USER_INACTIVE",
        )
        self.user_id = user_id


# ─── Validation exceptions ────────────────────────────────────────────────────


class ValidationError(DomainException):
    """Error de validación de datos de entrada."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            message=f"Error de validación en '{field}': {message}",
            code="VALIDATION_ERROR",
        )
        self.field = field


class InvalidEmailError(ValidationError):
    """Se lanza cuando el email no tiene formato válido."""

    def __init__(self, email: str) -> None:
        super().__init__(
            field="email",
            message=f"'{email}' no es un email válido.",
        )
        self.email = email


# ─── Authorization exceptions ─────────────────────────────────────────────────


class UnauthorizedError(DomainException):
    """Se lanza cuando el usuario no tiene permisos suficientes."""

    def __init__(self, action: str = "") -> None:
        msg = f"No autorizado para: {action}" if action else "No autorizado."
        super().__init__(message=msg, code="UNAUTHORIZED")
