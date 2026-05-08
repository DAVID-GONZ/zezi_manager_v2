"""
Modelo de dominio: PIAR
========================
Plan Individual de Apoyos y Ajustes Razonables (Decreto 1421 de 2017).

Contiene:
  Entidad  — PIAR
  DTOs     — NuevoPIARDTO, ActualizarPIARDTO

Reglas de negocio:
  - `descripcion_necesidad` es obligatoria y no puede estar vacía.
  - `fecha_elaboracion` no puede ser futura.
  - `fecha_revision`, si se provee, debe ser igual o posterior a `fecha_elaboracion`.
  - Cada estudiante tiene máximo un PIAR por año (UNIQUE en BD); el modelo
    no lo valida (es responsabilidad del repositorio), pero el servicio
    debe verificarlo antes de persistir.
"""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Entidad
# =============================================================================

class PIAR(BaseModel):
    """
    Plan Individual de Apoyos y Ajustes Razonables de un estudiante.

    El PIAR recoge las necesidades educativas específicas del estudiante
    y los ajustes acordados entre el equipo docente, el estudiante y su familia.
    No es un diagnóstico médico — es un instrumento pedagógico.
    """
    id:                     int | None  = None
    estudiante_id:          int
    anio_id:                int
    descripcion_necesidad:  str
    ajustes_evaluativos:    str | None  = None
    ajustes_pedagogicos:    str | None  = None
    profesionales_apoyo:    str | None  = None
    fecha_elaboracion:      date        = Field(default_factory=date.today)
    fecha_revision:         date | None = None
    usuario_elaboracion_id: int | None  = None

    # ------------------------------------------------------------------
    # Validadores de campo
    # ------------------------------------------------------------------

    @field_validator("descripcion_necesidad", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción de necesidades no puede estar vacía.")
        if len(v) > 3000:
            raise ValueError(
                f"La descripción no puede exceder 3000 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator(
        "ajustes_evaluativos", "ajustes_pedagogicos", "profesionales_apoyo",
        mode="before",
    )
    @classmethod
    def limpiar_campo_opcional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("fecha_elaboracion", mode="before")
    @classmethod
    def validar_fecha_elaboracion(cls, v: date | str) -> date:
        if isinstance(v, str):
            v = date.fromisoformat(v)
        if v > date.today():
            raise ValueError(
                "La fecha de elaboración no puede ser futura."
            )
        return v

    @field_validator("fecha_revision", mode="before")
    @classmethod
    def validar_fecha_revision(cls, v: date | str | None) -> date | None:
        if v is None:
            return None
        if isinstance(v, str):
            v = date.fromisoformat(v)
        return v

    # ------------------------------------------------------------------
    # Validador de modelo — coherencia entre fechas
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def validar_orden_fechas(self) -> Self:
        if self.fecha_revision and self.fecha_revision < self.fecha_elaboracion:
            raise ValueError(
                f"La fecha de revisión ({self.fecha_revision}) no puede ser "
                f"anterior a la fecha de elaboración ({self.fecha_elaboracion})."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades computadas
    # ------------------------------------------------------------------

    @property
    def tiene_revision_programada(self) -> bool:
        return self.fecha_revision is not None

    @property
    def revision_vencida(self) -> bool:
        """True si la fecha de revisión ya pasó y no se ha actualizado."""
        if self.fecha_revision is None:
            return False
        return self.fecha_revision < date.today()

    @property
    def dias_para_revision(self) -> int | None:
        """
        Días que faltan para la revisión programada.
        Negativo si ya venció. None si no hay revisión programada.
        """
        if self.fecha_revision is None:
            return None
        return (self.fecha_revision - date.today()).days

    @property
    def tiene_ajustes_evaluativos(self) -> bool:
        return bool(self.ajustes_evaluativos)

    @property
    def tiene_ajustes_pedagogicos(self) -> bool:
        return bool(self.ajustes_pedagogicos)

    # ------------------------------------------------------------------
    # Métodos de actualización
    # ------------------------------------------------------------------

    def programar_revision(self, fecha: date) -> "PIAR":
        """Retorna una copia con la fecha de revisión actualizada."""
        if fecha < self.fecha_elaboracion:
            raise ValueError(
                f"La fecha de revisión ({fecha}) no puede ser anterior "
                f"a la elaboración ({self.fecha_elaboracion})."
            )
        return self.model_copy(update={"fecha_revision": fecha})

    def actualizar_ajustes(
        self,
        ajustes_evaluativos: str | None = None,
        ajustes_pedagogicos: str | None = None,
        profesionales_apoyo: str | None = None,
    ) -> "PIAR":
        """Retorna una copia con los ajustes actualizados."""
        cambios: dict = {}
        if ajustes_evaluativos is not None:
            cambios["ajustes_evaluativos"] = ajustes_evaluativos.strip() or None
        if ajustes_pedagogicos is not None:
            cambios["ajustes_pedagogicos"] = ajustes_pedagogicos.strip() or None
        if profesionales_apoyo is not None:
            cambios["profesionales_apoyo"] = profesionales_apoyo.strip() or None
        return self.model_copy(update=cambios) if cambios else self


# =============================================================================
# DTOs
# =============================================================================

class NuevoPIARDTO(BaseModel):
    """Datos para registrar un PIAR nuevo."""
    estudiante_id:          int
    anio_id:                int
    descripcion_necesidad:  str
    ajustes_evaluativos:    str | None = None
    ajustes_pedagogicos:    str | None = None
    profesionales_apoyo:    str | None = None
    fecha_revision:         date | None = None

    @field_validator("descripcion_necesidad", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción de necesidades no puede estar vacía.")
        return v

    def to_piar(self, usuario_id: int | None = None) -> PIAR:
        return PIAR(
            **self.model_dump(),
            usuario_elaboracion_id=usuario_id,
        )


class ActualizarPIARDTO(BaseModel):
    """Campos actualizables de un PIAR. Todos opcionales."""
    descripcion_necesidad:  str | None  = None
    ajustes_evaluativos:    str | None  = None
    ajustes_pedagogicos:    str | None  = None
    profesionales_apoyo:    str | None  = None
    fecha_revision:         date | None = None

    @field_validator("descripcion_necesidad", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("La descripción no puede ser una cadena vacía.")
        return v

    def aplicar_a(self, piar: PIAR) -> PIAR:
        """Retorna una copia del PIAR con los campos del DTO aplicados."""
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        if not cambios:
            return piar
        return piar.model_copy(update=cambios)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "PIAR",
    "NuevoPIARDTO",
    "ActualizarPIARDTO",
]