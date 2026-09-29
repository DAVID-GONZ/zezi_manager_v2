"""
Schemas Pydantic para el modulo de Asistencia (backend_12).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class EstadoAsistenciaItem(BaseModel):
    """Item de asistencia para guardar en lote."""

    estudiante_id: int
    estado: str  # "P", "FJ", "FI", "R", "E"
    observacion: str | None = None


class GuardarAsistenciaMasivaRequest(BaseModel):
    grupo_id: int
    asignacion_id: int
    periodo_id: int
    fecha: date
    lista: list[EstadoAsistenciaItem]


class ResumenAsistenciaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    estudiante_id: int
    total_clases: int = 0
    presentes: int = 0
    faltas_justificadas: int = 0
    faltas_injustificadas: int = 0
    retrasos: int = 0
    excusas: int = 0


__all__ = [
    "EstadoAsistenciaItem",
    "GuardarAsistenciaMasivaRequest",
    "ResumenAsistenciaResponse",
]
