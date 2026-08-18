"""
src/domain/models/preferencia_institucion.py
============================================
Modelo de preferencias por institución (tenant).
"""

from __future__ import annotations

import json as _json
from enum import StrEnum

from pydantic import BaseModel, Field


class CategoriaPreferencia(StrEnum):
    ACADEMICAS = "academicas"
    CONVIVENCIA = "convivencia"
    APARIENCIA = "apariencia"


class TipoValor(StrEnum):
    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    JSON = "json"


class PreferenciaInstitucion(BaseModel):
    id: int | None = None
    institucion_id: int
    categoria: CategoriaPreferencia
    clave: str
    valor: str | None = None
    tipo_valor: TipoValor = TipoValor.STR

    def valor_tipado(self) -> bool | int | float | str | dict | None:
        if self.valor is None:
            return None
        match self.tipo_valor:
            case TipoValor.BOOL:
                return self.valor.lower() in ("true", "1", "yes")
            case TipoValor.INT:
                return int(self.valor)
            case TipoValor.FLOAT:
                return float(self.valor)
            case TipoValor.JSON:
                return _json.loads(self.valor)
            case _:
                return self.valor


class PreferenciasDTO(BaseModel):
    """Vista plana de las preferencias de una institución."""

    nota_minima_aprobacion_default: float = 60.0
    nota_minima_escala_default: float = 0.0
    nota_maxima_escala_default: float = 100.0
    numero_periodos_default: int = 4
    modulo_convivencia_activo: bool = True
    modulo_alertas_activo: bool = True
    color_primario: str | None = "#2E3192"
    color_secundario: str | None = "#8B90F0"
    # Política de registros de comportamiento en el boletín (convivencia_29).
    # Defaults conservadores aprobados por David 2026-08-12.
    registros_boletin_tipos: list[str] = Field(
        default_factory=lambda: ["fortaleza", "compromiso", "citacion_acudiente"]
    )
    registros_boletin_dificultad_requiere_notificacion: bool = True
    registros_boletin_incluye_descargo: bool = False
    registros_boletin_dedup_observaciones: bool = True


class ActualizarPreferenciaDTO(BaseModel):
    clave: str
    valor: str | None


__all__ = [
    "ActualizarPreferenciaDTO",
    "CategoriaPreferencia",
    "PreferenciaInstitucion",
    "PreferenciasDTO",
    "TipoValor",
]
