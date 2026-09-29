"""
Schemas de autenticacion para la API REST (backend_11).

Pydantic models para request/response del flujo de login JWT.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    """Body del POST /auth/login."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Respuesta exitosa del login: token JWT + metadata."""

    access_token: str
    token_type: str
    expires_in: int


class CurrentUserDTO(BaseModel):
    """Datos del usuario autenticado extraidos del token JWT."""

    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    username: str
    rol: str
    institucion_id: int | None


__all__ = [
    "CurrentUserDTO",
    "LoginRequest",
    "TokenResponse",
]
