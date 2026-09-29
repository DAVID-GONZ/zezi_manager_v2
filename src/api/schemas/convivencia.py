"""
Schemas Pydantic para el modulo de Convivencia (backend_12).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ObservacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    estudiante_id: int
    asignacion_id: int
    periodo_id: int
    texto: str
    categoria_id: int | None = None
    es_publica: bool = True
    usuario_id: int | None = None


class NuevaObservacionRequest(BaseModel):
    estudiante_id: int
    asignacion_id: int
    periodo_id: int
    texto: str
    categoria_id: int
    es_publica: bool = True


class ResumenConvivenciaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    estudiante_id: int
    nombre: str
    num_observaciones: int = 0
    num_registros_negativos: int = 0
    nota: float | None = None
    nivel_nombre: str | None = None
    supera_umbral: bool = False


class NotaComportamientoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    estudiante_id: int
    grupo_id: int
    periodo_id: int
    valor: float
    observacion: str | None = None


__all__ = [
    "NotaComportamientoResponse",
    "NuevaObservacionRequest",
    "ObservacionResponse",
    "ResumenConvivenciaResponse",
]
