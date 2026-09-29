"""
Schemas Pydantic para el modulo de Informes (backend_12).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class InformeNotasRequest(BaseModel):
    grupo_id: int
    asignacion_id: int
    periodo_id: int
    fecha_desde: date
    fecha_hasta: date
    formato: str = "excel"  # "excel" | "pdf"
    incluir_piar: bool = True


class InformeAsistenciaRequest(BaseModel):
    grupo_id: int
    asignacion_id: int
    periodo_id: int
    fecha_desde: date
    fecha_hasta: date
    formato: str = "excel"


__all__ = [
    "InformeAsistenciaRequest",
    "InformeNotasRequest",
]
