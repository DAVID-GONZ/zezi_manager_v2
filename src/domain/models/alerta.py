"""
Modelo de dominio: Alertas
===========================

Contiene:
  Enums    — TipoAlerta, NivelAlerta
  Entidades — ConfiguracionAlerta, Alerta
  DTOs     — CrearAlertaDTO, ResolverAlertaDTO, FiltroAlertasDTO

Reglas de negocio:
  - Una alerta resuelta no puede resolverse de nuevo.
  - `fecha_resolucion` y `usuario_resolucion_id` solo existen si `resuelta=True`.
  - El umbral de ConfiguracionAlerta tiene semántica dependiente del tipo:
      faltas_injustificadas  → número entero de faltas (≥ 1)
      promedio_bajo          → nota entre 0 y 100
      materias_en_riesgo     → número entero de materias (≥ 1)
      plan_mejoramiento_*    → número entero (≥ 1)
      habilitacion_pendiente → número entero (≥ 1)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class TipoAlerta(str, Enum):
    FALTAS_INJUSTIFICADAS     = "faltas_injustificadas"
    PROMEDIO_BAJO             = "promedio_bajo"
    MATERIAS_EN_RIESGO        = "materias_en_riesgo"
    PLAN_MEJORAMIENTO_VENCIDO = "plan_mejoramiento_vencido"
    HABILITACION_PENDIENTE    = "habilitacion_pendiente"


class NivelAlerta(str, Enum):
    INFO        = "info"
    ADVERTENCIA = "advertencia"
    CRITICA     = "critica"


# =============================================================================
# Entidades
# =============================================================================

class ConfiguracionAlerta(BaseModel):
    """
    Define cuándo se genera automáticamente una alerta para un año lectivo.

    El significado de `umbral` depende del tipo:
      - faltas_injustificadas:     número de faltas antes de generar alerta (ej. 3)
      - promedio_bajo:             nota por debajo de la cual se alerta (ej. 55.0)
      - materias_en_riesgo:        cantidad de materias perdidas (ej. 2)
      - plan_mejoramiento_vencido: días de vencimiento antes de alertar (ej. 1)
      - habilitacion_pendiente:    días antes de la fecha límite (ej. 1)
    """
    id:                  int | None  = None
    anio_id:             int
    tipo_alerta:         TipoAlerta
    umbral:              float
    activa:              bool        = True
    notificar_docente:   bool        = True
    notificar_director:  bool        = False
    notificar_acudiente: bool        = False

    @field_validator("umbral")
    @classmethod
    def validar_umbral(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(
                f"El umbral debe ser mayor que cero (recibido: {v})."
            )
        return v

    @model_validator(mode="after")
    def validar_umbral_segun_tipo(self) -> Self:
        """
        Para tipos de conteo (faltas, materias, planes), el umbral debe ser
        un número entero positivo. Para promedio_bajo debe estar en [0, 100].
        """
        tipos_conteo = {
            TipoAlerta.FALTAS_INJUSTIFICADAS,
            TipoAlerta.MATERIAS_EN_RIESGO,
            TipoAlerta.PLAN_MEJORAMIENTO_VENCIDO,
            TipoAlerta.HABILITACION_PENDIENTE,
        }
        if self.tipo_alerta in tipos_conteo:
            if self.umbral != int(self.umbral):
                raise ValueError(
                    f"El umbral para '{self.tipo_alerta.value}' debe ser un "
                    f"número entero (recibido: {self.umbral})."
                )
        elif self.tipo_alerta == TipoAlerta.PROMEDIO_BAJO:
            if not (0 <= self.umbral <= 100):
                raise ValueError(
                    f"El umbral para 'promedio_bajo' debe estar entre 0 y 100 "
                    f"(recibido: {self.umbral})."
                )
        return self

    @property
    def umbral_entero(self) -> int:
        """Umbral como entero para tipos de conteo."""
        return int(self.umbral)

    @property
    def notifica_a_alguien(self) -> bool:
        """True si al menos un destinatario está habilitado."""
        return self.notificar_docente or self.notificar_director or self.notificar_acudiente


class Alerta(BaseModel):
    """
    Alerta generada para un estudiante específico.

    Una vez resuelta, la alerta es inmutable: no puede volver a abrirse
    ni resolverse de nuevo.
    """
    id:                     int | None      = None
    estudiante_id:          int
    tipo_alerta:            TipoAlerta
    nivel:                  NivelAlerta     = NivelAlerta.ADVERTENCIA
    descripcion:            str
    fecha_generacion:       datetime        = Field(default_factory=datetime.now)
    resuelta:               bool            = False
    fecha_resolucion:       datetime | None = None
    usuario_resolucion_id:  int | None      = None
    observacion_resolucion: str | None      = None

    @field_validator("estudiante_id", mode="before")
    @classmethod
    def coercer_estudiante_id(cls, v):
        # NULL en BD indica alerta huérfana (estudiante eliminado sin CASCADE DELETE).
        # Se acepta como 0 para que la hidratación no falle en lectura.
        if v is None:
            return 0
        return int(v)

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción de la alerta no puede estar vacía.")
        if len(v) > 500:
            raise ValueError(
                f"La descripción no puede exceder 500 caracteres (tiene {len(v)})."
            )
        return v

    @model_validator(mode="after")
    def validar_coherencia_resolucion(self) -> Self:
        """
        Si la alerta está resuelta, debe tener fecha_resolucion.
        Si no está resuelta, no debe tener datos de resolución.
        """
        if self.resuelta and self.fecha_resolucion is None:
            raise ValueError(
                "Una alerta resuelta debe tener fecha_resolucion."
            )
        if not self.resuelta and (
            self.fecha_resolucion is not None
            or self.usuario_resolucion_id is not None
        ):
            raise ValueError(
                "Una alerta pendiente no puede tener datos de resolución."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades computadas
    # ------------------------------------------------------------------

    @property
    def esta_pendiente(self) -> bool:
        return not self.resuelta

    @property
    def dias_pendiente(self) -> int | None:
        """Días transcurridos desde la generación. None si ya está resuelta."""
        if self.resuelta:
            return None
        return (datetime.now() - self.fecha_generacion).days

    @property
    def es_critica(self) -> bool:
        return self.nivel == NivelAlerta.CRITICA

    # ------------------------------------------------------------------
    # Transición de estado
    # ------------------------------------------------------------------

    def resolver(
        self,
        usuario_id: int,
        observacion: str | None = None,
        fecha: datetime | None = None,
    ) -> "Alerta":
        """
        Retorna una nueva instancia de la alerta marcada como resuelta.

        Args:
            usuario_id:   Id del usuario que resuelve la alerta.
            observacion:  Texto opcional explicando cómo se resolvió.
            fecha:        Momento de resolución. Por defecto datetime.now().

        Raises:
            ValueError: Si la alerta ya estaba resuelta.
        """
        if self.resuelta:
            raise ValueError(
                f"La alerta #{self.id} ya fue resuelta el "
                f"{self.fecha_resolucion}. No se puede resolver de nuevo."
            )
        return self.model_copy(update={
            "resuelta":               True,
            "fecha_resolucion":       fecha or datetime.now(),
            "usuario_resolucion_id":  usuario_id,
            "observacion_resolucion": observacion.strip() if observacion else None,
        })


# =============================================================================
# DTOs
# =============================================================================

class CrearAlertaDTO(BaseModel):
    """Datos necesarios para generar una alerta nueva."""
    estudiante_id: int
    tipo_alerta:   TipoAlerta
    nivel:         NivelAlerta = NivelAlerta.ADVERTENCIA
    descripcion:   str

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción no puede estar vacía.")
        return v

    def to_alerta(self) -> Alerta:
        return Alerta(**self.model_dump())


class ResolverAlertaDTO(BaseModel):
    """Datos para marcar una alerta como resuelta."""
    usuario_id:  int
    observacion: str | None = None

    @field_validator("observacion", mode="before")
    @classmethod
    def limpiar_observacion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class FiltroAlertasDTO(BaseModel):
    """Parámetros para listar alertas."""
    estudiante_id: int | None       = None
    tipo_alerta:   TipoAlerta | None = None
    nivel:         NivelAlerta | None = None
    solo_pendientes: bool           = True
    pagina:        int              = Field(default=1, ge=1)
    por_pagina:    int              = Field(default=50, ge=1, le=200)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "TipoAlerta",
    "NivelAlerta",
    "ConfiguracionAlerta",
    "Alerta",
    "CrearAlertaDTO",
    "ResolverAlertaDTO",
    "FiltroAlertasDTO",
]