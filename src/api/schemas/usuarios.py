"""
Schemas Pydantic para el modulo de Usuarios (backend_12).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario: str
    nombre_completo: str
    email: str | None = None
    telefono: str | None = None
    rol: str
    activo: bool
    debe_cambiar_password: bool
    fecha_creacion: date
    ultima_sesion: datetime | None = None
    institucion_id: int | None = None


class NuevoUsuarioRequest(BaseModel):
    usuario: str
    nombre_completo: str
    rol: str
    email: str | None = None
    institucion_id: int | None = None
    password: str | None = None


class ActualizarUsuarioRequest(BaseModel):
    nombre_completo: str | None = None
    email: str | None = None
    telefono: str | None = None


class CambiarRolRequest(BaseModel):
    nuevo_rol: str


class ResetearPasswordRequest(BaseModel):
    nueva_password: str = ""


class UsuarioResumenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario: str
    nombre_completo: str
    rol: str
    activo: bool
    institucion_id: int | None = None


__all__ = [
    "ActualizarUsuarioRequest",
    "CambiarRolRequest",
    "NuevoUsuarioRequest",
    "ResetearPasswordRequest",
    "UsuarioResponse",
    "UsuarioResumenResponse",
]
