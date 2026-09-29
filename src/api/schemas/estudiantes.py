"""
Schemas Pydantic para el modulo de Estudiantes (backend_12).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class EstudianteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_publico: str | None = None
    tipo_documento: str
    numero_documento: str
    nombre: str
    apellido: str
    genero: str | None = None
    fecha_nacimiento: date | None = None
    direccion: str | None = None
    grupo_id: int | None = None
    posee_piar: bool
    fecha_ingreso: date
    estado_matricula: str
    institucion_id: int | None = None


class NuevoEstudianteRequest(BaseModel):
    tipo_documento: str = "TI"
    numero_documento: str
    nombre: str
    apellido: str
    genero: str | None = None
    fecha_nacimiento: date | None = None
    direccion: str | None = None
    grupo_id: int | None = None


class ActualizarEstudianteRequest(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    genero: str | None = None
    fecha_nacimiento: date | None = None
    direccion: str | None = None
    grupo_id: int | None = None
    posee_piar: bool | None = None


class RetirarEstudianteRequest(BaseModel):
    motivo: str | None = None


class EstudianteResumenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_completo: str
    documento_display: str
    grupo_id: int | None = None
    estado_matricula: str
    genero: str | None = None
    posee_piar: bool


class CargaMasivaResponse(BaseModel):
    insertados: int
    errores: list


__all__ = [
    "ActualizarEstudianteRequest",
    "CargaMasivaResponse",
    "EstudianteResponse",
    "EstudianteResumenResponse",
    "NuevoEstudianteRequest",
    "RetirarEstudianteRequest",
]
