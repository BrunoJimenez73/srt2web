"""Servicios de seguridad: hashing de contraseñas y JWT."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from src.infrastructure.config.settings import get_settings

_settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Password Hasher ──────────────────────────────────────────────────────────


class IPasswordHasher(ABC):
    """Interfaz para hashing de contraseñas."""

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Genera hash de la contraseña."""

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica si la contraseña coincide con el hash."""


class BcryptPasswordHasher(IPasswordHasher):
    """Implementación bcrypt de IPasswordHasher."""

    def hash(self, plain_password: str) -> str:
        return str(_pwd_context.hash(plain_password))

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bool(_pwd_context.verify(plain_password, hashed_password))


# ─── JWT ──────────────────────────────────────────────────────────────────────


class JWTService:
    """Servicio para creación y verificación de tokens JWT.

    Args:
        secret_key: Clave secreta para firmar tokens.
        algorithm: Algoritmo de firma (default HS256).
        expire_minutes: Minutos hasta expiración del access token.
    """

    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str | None = None,
        expire_minutes: int | None = None,
    ) -> None:
        self._secret = secret_key or _settings.SECRET_KEY
        self._algorithm = algorithm or _settings.ALGORITHM
        self._expire_minutes = expire_minutes or _settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def create_access_token(
        self,
        subject: str | int,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Genera un JWT de acceso.

        Args:
            subject: Identificador del usuario (normalmente su ID).
            extra_claims: Claims adicionales a incluir en el payload.

        Returns:
            Token JWT firmado como string.
        """
        now = datetime.now(tz=UTC)
        payload: dict[str, Any] = {
            "sub": str(subject),
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
            "type": "access",
        }
        if extra_claims:
            payload.update(extra_claims)

        return str(jwt.encode(payload, self._secret, algorithm=self._algorithm))

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decodifica y valida un JWT.

        Args:
            token: Token JWT a decodificar.

        Returns:
            Payload del token como diccionario.

        Raises:
            JWTError: Si el token es inválido o ha expirado.
        """
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
            return payload
        except JWTError as exc:
            raise JWTError(f"Token inválido: {exc}") from exc

    def get_subject(self, token: str) -> str:
        """Extrae el subject (user id) del token.

        Raises:
            JWTError: Si el token es inválido.
            KeyError: Si el payload no tiene campo 'sub'.
        """
        payload = self.decode_token(token)
        sub = payload.get("sub")
        if not sub:
            raise JWTError("Token sin campo 'sub'.")
        return str(sub)
