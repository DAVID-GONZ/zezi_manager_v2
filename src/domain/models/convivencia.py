"""
Modelo de dominio: Convivencia
================================

Contiene:
  Enums    — TipoRegistro
  Entidades — ObservacionPeriodo, RegistroComportamiento, NotaComportamiento
  DTOs     — NuevaObservacionDTO, NuevoRegistroComportamientoDTO,
              NuevaNotaComportamientoDTO, FiltroConvivenciaDTO

Conceptos:
  ObservacionPeriodo
      Texto narrativo que el docente escribe sobre un estudiante al cierre
      del periodo. Aparece en el boletín si es_publica=True.

  RegistroComportamiento
      Evento puntual de convivencia: fortaleza, dificultad, compromiso,
      citación al acudiente, o descargo del estudiante.
      Puede requerir firma del acudiente.

  NotaComportamiento
      Calificación cuantitativa de convivencia por periodo (si la institución
      la usa). Opcional — no todas las instituciones califican convivencia.

Reglas de negocio:
  - texto (ObservacionPeriodo) no puede estar vacío, máximo 2000 chars.
  - descripcion (RegistroComportamiento) no puede estar vacía, máximo 1000 chars.
  - fecha (RegistroComportamiento) no puede ser futura.
  - acudiente_notificado=True implica que hubo contacto; puede ser True
    incluso si requiere_firma=False (se notificó sin requerir firma).
  - valor (NotaComportamiento) debe estar en [0, 100].
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class TipoRegistro(str, Enum):
    FORTALEZA          = "fortaleza"
    DIFICULTAD         = "dificultad"
    COMPROMISO         = "compromiso"
    CITACION_ACUDIENTE = "citacion_acudiente"
    DESCARGO           = "descargo"


# =============================================================================
# Entidades
# =============================================================================

class ObservacionPeriodo(BaseModel):
    """
    Observación narrativa de un docente sobre un estudiante en un periodo.

    `es_publica=True` indica que el texto aparecerá en el boletín.
    `es_publica=False` es para notas internas del docente.
    """
    id:             int | None  = None
    estudiante_id:  int
    asignacion_id:  int
    periodo_id:     int
    texto:          str
    es_publica:     bool        = True
    fecha_registro: datetime    = Field(default_factory=datetime.now)
    usuario_id:     int | None  = None

    @field_validator("texto", mode="before")
    @classmethod
    def validar_texto(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La observación no puede estar vacía.")
        if len(v) > 2000:
            raise ValueError(
                f"La observación no puede exceder 2000 caracteres (tiene {len(v)})."
            )
        return v

    def hacer_publica(self) -> "ObservacionPeriodo":
        """Retorna una copia marcada como pública (aparece en boletín)."""
        return self.model_copy(update={"es_publica": True})

    def hacer_privada(self) -> "ObservacionPeriodo":
        """Retorna una copia marcada como privada (solo visible al docente)."""
        return self.model_copy(update={"es_publica": False})


class RegistroComportamiento(BaseModel):
    """
    Evento puntual de convivencia registrado por un docente o directivo.

    La secuencia típica de un registro negativo:
      1. Se crea con tipo=DIFICULTAD, requiere_firma=True.
      2. Se llama a `registrar_notificacion()` cuando el acudiente es contactado.
      3. Se llama a `agregar_seguimiento(texto)` cuando hay acciones posteriores.

    DESCARGO es la respuesta formal del estudiante ante una falta grave.
    COMPROMISO es un acuerdo entre el estudiante/acudiente y la institución.
    """
    id:                  int | None      = None
    estudiante_id:       int
    grupo_id:            int
    periodo_id:          int
    fecha:               date            = Field(default_factory=date.today)
    tipo:                TipoRegistro
    descripcion:         str
    seguimiento:         str | None      = None
    requiere_firma:      bool            = False
    acudiente_notificado: bool           = False
    usuario_registro_id: int | None      = None

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción del registro no puede estar vacía.")
        if len(v) > 1000:
            raise ValueError(
                f"La descripción no puede exceder 1000 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("seguimiento", mode="before")
    @classmethod
    def limpiar_seguimiento(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @field_validator("fecha", mode="before")
    @classmethod
    def validar_fecha(cls, v: date | str) -> date:
        if isinstance(v, str):
            v = date.fromisoformat(v)
        if v > date.today():
            raise ValueError(
                f"La fecha del registro ({v}) no puede ser futura."
            )
        return v

    @model_validator(mode="after")
    def validar_notificacion(self) -> Self:
        """
        No tiene sentido marcar acudiente_notificado=True en un registro
        de FORTALEZA que no requiere firma. Pero sí puede notificarse
        en cualquier caso — el sistema no lo restringe; solo verifica
        que no haya inconsistencia con descargos.
        Un DESCARGO no requiere firma (es el estudiante quien habla).
        """
        if self.tipo == TipoRegistro.DESCARGO and self.requiere_firma:
            raise ValueError(
                "Un registro de tipo DESCARGO es emitido por el estudiante "
                "y no requiere firma del acudiente."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades computadas
    # ------------------------------------------------------------------

    @property
    def es_negativo(self) -> bool:
        """True para registros que implican una situación problemática."""
        return self.tipo in (
            TipoRegistro.DIFICULTAD,
            TipoRegistro.CITACION_ACUDIENTE,
        )

    @property
    def es_positivo(self) -> bool:
        """True para registros que reconocen comportamiento positivo."""
        return self.tipo == TipoRegistro.FORTALEZA

    @property
    def pendiente_notificacion(self) -> bool:
        """True si requiere firma pero el acudiente aún no ha sido notificado."""
        return self.requiere_firma and not self.acudiente_notificado

    @property
    def tiene_seguimiento(self) -> bool:
        return bool(self.seguimiento)

    # ------------------------------------------------------------------
    # Métodos de dominio
    # ------------------------------------------------------------------

    def registrar_notificacion(self) -> "RegistroComportamiento":
        """
        Retorna una copia marcando que el acudiente fue notificado.

        Raises:
            ValueError: Si el registro no requería firma/notificación.
        """
        if not self.requiere_firma:
            raise ValueError(
                "Este registro no requiere notificación al acudiente."
            )
        if self.acudiente_notificado:
            raise ValueError(
                "El acudiente ya fue notificado para este registro."
            )
        return self.model_copy(update={"acudiente_notificado": True})

    def agregar_seguimiento(self, texto: str) -> "RegistroComportamiento":
        """
        Retorna una copia con el texto de seguimiento añadido o reemplazado.

        Args:
            texto: Descripción de las acciones tomadas después del registro.
        """
        texto = texto.strip()
        if not texto:
            raise ValueError("El texto de seguimiento no puede estar vacío.")
        return self.model_copy(update={"seguimiento": texto})


class NotaComportamiento(BaseModel):
    """
    Calificación cuantitativa de convivencia por periodo.

    No todas las instituciones la usan. Cuando existe, es independiente
    de las notas académicas y puede tener su propio nivel de desempeño.
    """
    id:            int | None   = None
    estudiante_id: int
    grupo_id:      int
    periodo_id:    int
    valor:         float
    desempeno_id:  int | None   = None
    observacion:   str | None   = None
    usuario_id:    int | None   = None

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(
                f"La nota de comportamiento debe estar entre 0 y 100 (recibido: {v})."
            )
        return round(v, 2)

    @field_validator("observacion", mode="before")
    @classmethod
    def limpiar_observacion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @property
    def aprobado(self, nota_minima: float = 60.0) -> bool:
        """
        Indica si la nota de comportamiento es aprobatoria.
        La nota mínima se pasa como parámetro porque es configurable
        por institución (configuracion_anio.nota_minima_aprobacion).
        """
        return self.valor >= nota_minima


# =============================================================================
# DTOs
# =============================================================================

class NuevaObservacionDTO(BaseModel):
    """Datos para registrar una observación de periodo."""
    estudiante_id: int
    asignacion_id: int
    periodo_id:    int
    texto:         str
    es_publica:    bool = True

    @field_validator("texto", mode="before")
    @classmethod
    def validar_texto(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El texto no puede estar vacío.")
        return v

    def to_observacion(self, usuario_id: int | None = None) -> ObservacionPeriodo:
        return ObservacionPeriodo(
            **self.model_dump(),
            usuario_id=usuario_id,
        )


class NuevoRegistroComportamientoDTO(BaseModel):
    """Datos para crear un registro de comportamiento."""
    estudiante_id:   int
    grupo_id:        int
    periodo_id:      int
    tipo:            TipoRegistro
    descripcion:     str
    requiere_firma:  bool = False
    fecha:           date = Field(default_factory=date.today)

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción no puede estar vacía.")
        return v

    def to_registro(self, usuario_id: int | None = None) -> RegistroComportamiento:
        return RegistroComportamiento(
            **self.model_dump(),
            usuario_registro_id=usuario_id,
        )


class NuevaNotaComportamientoDTO(BaseModel):
    """Datos para registrar la nota de comportamiento de un periodo."""
    estudiante_id: int
    grupo_id:      int
    periodo_id:    int
    valor:         float
    observacion:   str | None = None

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(f"El valor debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    def to_nota(self, usuario_id: int | None = None) -> NotaComportamiento:
        return NotaComportamiento(
            **self.model_dump(),
            usuario_id=usuario_id,
        )


class FiltroConvivenciaDTO(BaseModel):
    """Parámetros para consultar registros de comportamiento."""
    estudiante_id: int | None       = None
    grupo_id:      int | None       = None
    periodo_id:    int | None       = None
    tipo:          TipoRegistro | None = None
    solo_negativos: bool            = False
    pagina:        int              = Field(default=1, ge=1)
    por_pagina:    int              = Field(default=50, ge=1, le=200)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "TipoRegistro",
    "ObservacionPeriodo",
    "RegistroComportamiento",
    "NotaComportamiento",
    "NuevaObservacionDTO",
    "NuevoRegistroComportamientoDTO",
    "NuevaNotaComportamientoDTO",
    "FiltroConvivenciaDTO",
]