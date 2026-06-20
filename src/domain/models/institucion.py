"""
Modelo de dominio: Institución
===============================

Contiene:
  Entidad  — Institucion
  DTOs     — NuevaInstitucionDTO, InstitucionResumenDTO

Primer ladrillo del modelo multi-tenant (paso_24). Hoy existe una sola
configuración institucional (singleton `configuracion_anio`). Esta entidad
introduce un catálogo de instituciones; la institución #1 se siembra desde
`configuracion.nombre_institucion`.

Reglas de negocio:
  - `nombre` no puede estar vacío y se normaliza (strip).
  - `nit`/`codigo` son opcionales (identificadores externos, p.ej. DANE).
  - Soft state: las instituciones no se eliminan, se marcan inactivas.
  - El servicio garantiza la unicidad del nombre (no el modelo).

Fuera de alcance (paso_24): `institucion_id` en tablas académicas
(config/años/grupos). Aislamiento total por tenant.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Entidad principal
# =============================================================================

class Institucion(BaseModel):
    """
    Una institución educativa (tenant) registrada en la plataforma.

    La institución #1 representa la institución por defecto, sembrada a partir
    de la configuración institucional existente.
    """
    id:             int | None  = None
    nombre:         str
    nit:            str | None   = None   # NIT / identificador tributario
    codigo:         str | None   = None   # código externo (p.ej. DANE)
    activa:         bool         = True
    fecha_creacion: date         = Field(default_factory=date.today)

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la institución no puede estar vacío.")
        if len(v) > 200:
            raise ValueError(
                f"El nombre no puede exceder 200 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("nit", "codigo", mode="before")
    @classmethod
    def limpiar_opcional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @property
    def nombre_display(self) -> str:
        """'Colegio X' o 'Colegio X (inactiva)'."""
        return self.nombre + ("" if self.activa else " (inactiva)")


# =============================================================================
# DTOs
# =============================================================================

class NuevaInstitucionDTO(BaseModel):
    """Datos para crear una institución nueva."""
    nombre: str
    nit:    str | None = None
    codigo: str | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la institución no puede estar vacío.")
        if len(v) > 200:
            raise ValueError(
                f"El nombre no puede exceder 200 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("nit", "codigo", mode="before")
    @classmethod
    def limpiar_opcional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    def to_institucion(self) -> Institucion:
        return Institucion(**self.model_dump())


class InstitucionResumenDTO(BaseModel):
    """Vista mínima para selects, filtros y lookups."""
    id:     int
    nombre: str
    activa: bool

    @classmethod
    def desde_institucion(cls, i: Institucion) -> "InstitucionResumenDTO":
        if i.id is None:
            raise ValueError("No se puede resumir una institución sin id.")
        return cls(id=i.id, nombre=i.nombre, activa=i.activa)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Institucion",
    "NuevaInstitucionDTO",
    "InstitucionResumenDTO",
]
