"""
Schemas Pydantic para el modulo de Auditoria (backend_12).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventoSesionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    usuario: str
    usuario_id: int | None = None
    tipo_evento: str
    ip_address: str | None = None
    fecha_hora: datetime
    detalles: str | None = None
    severidad: str = "INFO"
    institucion_id: int | None = None


class RegistroCambioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    usuario_id: int | None = None
    usuario: str | None = None
    accion: str
    tabla: str
    registro_id: int | None = None
    timestamp: datetime
    institucion_id: int | None = None


class IntegridadResponse(BaseModel):
    eventos_ok: bool
    cambios_ok: bool
    evento_roto_id: int | None = None
    cambio_roto_id: int | None = None
    alcance: str = "incremental"


__all__ = [
    "EventoSesionResponse",
    "IntegridadResponse",
    "RegistroCambioResponse",
]
