"""
Schemas Pydantic para el modulo de Configuracion (backend_12).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ConfiguracionAnioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    anio: int
    activo: bool
    institucion_id: int | None = None
    nota_minima_aprobacion: float | None = None
    nota_minima_escala: float | None = None
    nota_maxima_escala: float | None = None


class ActualizarInfoInstitucionalRequest(BaseModel):
    nombre_institucion: str | None = None
    dane_code: str | None = None
    rector: str | None = None
    municipio: str | None = None
    direccion: str | None = None


__all__ = [
    "ActualizarInfoInstitucionalRequest",
    "ConfiguracionAnioResponse",
]
