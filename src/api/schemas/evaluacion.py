"""
Schemas Pydantic para el modulo de Evaluacion (backend_12).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class PlanillaEstudianteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    estudiante_id: int
    nombre_completo: str | None = None
    definitiva: float | None = None
    promedio_ajustado: float | None = None
    notas: Any = None


class RegistrarNotaItem(BaseModel):
    estudiante_id: int
    actividad_id: int
    valor: float


class RegistrarNotasMasivasRequest(BaseModel):
    grupo_id: int
    asignacion_id: int
    periodo_id: int
    anio_id: int
    actividad_id: int
    notas: list[RegistrarNotaItem]


class ConfiguracionSIEEResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    anio_id: int
    modo: str = "LIBRE"


__all__ = [
    "ConfiguracionSIEEResponse",
    "PlanillaEstudianteResponse",
    "RegistrarNotaItem",
    "RegistrarNotasMasivasRequest",
]
