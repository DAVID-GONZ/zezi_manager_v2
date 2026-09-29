"""
Schemas Pydantic para el modulo de Contexto academico (backend_12).

Expone grupos, asignaturas y periodos del catalogo academico.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GrupoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    grado: int | None = None
    codigo: str | None = None
    institucion_id: int | None = None


class AsignaturaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    codigo: str | None = None
    area_id: int | None = None
    institucion_id: int | None = None


class PeriodoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    numero: int
    anio_id: int
    activo: bool


class AreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    institucion_id: int | None = None


__all__ = [
    "AreaResponse",
    "AsignaturaResponse",
    "GrupoResponse",
    "PeriodoResponse",
]
