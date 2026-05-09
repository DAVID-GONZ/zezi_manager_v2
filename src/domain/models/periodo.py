"""
Modelo de dominio: Periodo y HitoPeriodo
=========================================

Contiene:
  Enums    — TipoHito
  Entidades — Periodo, HitoPeriodo
  DTOs     — NuevoPeriodoDTO, ActualizarPeriodoDTO, NuevoHitoPeriodoDTO

Reglas de negocio:
  - numero debe estar entre 1 y 6.
  - peso_porcentual debe ser > 0 y ≤ 100.
  - Si ambas fechas existen, fecha_inicio ≤ fecha_fin.
  - Un periodo cerrado no puede reabrirse — es el candado que protege
    las calificaciones definitivas de modificaciones posteriores.
  - Un periodo activo es el que acepta registros de asistencia y notas.
    activo y cerrado son flags independientes:
      activo=True,  cerrado=False → en curso
      activo=False, cerrado=False → inactivo (aún no iniciado o en pausa)
      activo=False, cerrado=True  → finalizado y bloqueado
  - La suma de pesos de todos los periodos del año debe ser 100%,
    pero esa regla la verifica el servicio (requiere todos los periodos).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enumeraciones
# =============================================================================

class TipoHito(str, Enum):
    ENTREGA_NOTAS          = "entrega_notas"
    INICIO_HABILITACIONES  = "inicio_habilitaciones"
    FIN_HABILITACIONES     = "fin_habilitaciones"
    ENTREGA_BOLETINES      = "entrega_boletines"
    GENERAL                = "general"


# =============================================================================
# Entidades
# =============================================================================

class Periodo(BaseModel):
    """
    Periodo académico dentro de un año lectivo.

    Cada periodo tiene un peso porcentual que define cuánto contribuye
    a la nota anual del estudiante. Para cuatro periodos con pesos iguales,
    cada uno vale 25%.

    El flag `cerrado` es el candado de evaluación: una vez cerrado,
    ningún trigger de BD ni ningún servicio debería aceptar nuevas notas
    para ese periodo. El modelo lo hace explícito para que los servicios
    puedan verificarlo antes de llegar a la BD.
    """
    id:               int | None      = None
    anio_id:          int
    numero:           int
    nombre:           str
    fecha_inicio:     date | None     = None
    fecha_fin:        date | None     = None
    peso_porcentual:  float           = 25.0
    activo:           bool            = True
    cerrado:          bool            = False
    fecha_cierre_real: datetime | None = None

    # ------------------------------------------------------------------
    # Validadores de campo
    # ------------------------------------------------------------------

    @field_validator("anio_id")
    @classmethod
    def validar_anio_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"anio_id debe ser un entero positivo (recibido: {v}).")
        return v

    @field_validator("numero")
    @classmethod
    def validar_numero(cls, v: int) -> int:
        if not (1 <= v <= 6):
            raise ValueError(
                f"El número de periodo debe estar entre 1 y 6 (recibido: {v})."
            )
        return v

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre del periodo no puede estar vacío.")
        if len(v) > 50:
            raise ValueError(
                f"El nombre no puede exceder 50 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("peso_porcentual")
    @classmethod
    def validar_peso(cls, v: float) -> float:
        if not (0 < v <= 100):
            raise ValueError(
                f"El peso porcentual debe estar entre 0 y 100 (recibido: {v})."
            )
        return round(v, 2)

    # ------------------------------------------------------------------
    # Validador de modelo
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def validar_coherencia_fechas(self) -> Self:
        if (
            self.fecha_inicio is not None
            and self.fecha_fin is not None
            and self.fecha_inicio > self.fecha_fin
        ):
            raise ValueError(
                f"fecha_inicio ({self.fecha_inicio}) no puede ser posterior "
                f"a fecha_fin ({self.fecha_fin})."
            )
        if self.cerrado and self.fecha_cierre_real is None:
            raise ValueError(
                "Un periodo cerrado debe tener fecha_cierre_real."
            )
        if not self.cerrado and self.fecha_cierre_real is not None:
            raise ValueError(
                "Un periodo abierto no puede tener fecha_cierre_real."
            )
        return self

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def esta_abierto(self) -> bool:
        """True si el periodo acepta modificaciones de notas y asistencia."""
        return not self.cerrado

    @property
    def esta_vigente(self) -> bool:
        """True si el periodo está activo y no cerrado."""
        return self.activo and not self.cerrado

    @property
    def duracion_dias(self) -> int | None:
        """Días de duración del periodo. None si faltan fechas."""
        if self.fecha_inicio is None or self.fecha_fin is None:
            return None
        return (self.fecha_fin - self.fecha_inicio).days

    @property
    def en_curso(self) -> bool:
        """
        True si la fecha actual está dentro del rango del periodo.
        None si faltan fechas → retorna False conservadoramente.
        """
        if self.fecha_inicio is None or self.fecha_fin is None:
            return False
        hoy = date.today()
        return self.fecha_inicio <= hoy <= self.fecha_fin

    # ------------------------------------------------------------------
    # Métodos de dominio
    # ------------------------------------------------------------------

    def cerrar(self, fecha: datetime | None = None) -> "Periodo":
        """
        Retorna una copia del periodo marcada como cerrada.

        Raises:
            ValueError: Si el periodo ya estaba cerrado.
        """
        if self.cerrado:
            raise ValueError(
                f"El periodo '{self.nombre}' ya fue cerrado el "
                f"{self.fecha_cierre_real}."
            )
        return self.model_copy(update={
            "cerrado":          True,
            "activo":           False,
            "fecha_cierre_real": fecha or datetime.now(),
        })

    def activar(self) -> "Periodo":
        """Retorna una copia con activo=True."""
        if self.cerrado:
            raise ValueError(
                "No se puede activar un periodo cerrado."
            )
        if self.activo:
            raise ValueError(
                f"El periodo '{self.nombre}' ya está activo."
            )
        return self.model_copy(update={"activo": True})

    def desactivar(self) -> "Periodo":
        """Retorna una copia con activo=False."""
        if not self.activo:
            raise ValueError(
                f"El periodo '{self.nombre}' ya está inactivo."
            )
        return self.model_copy(update={"activo": False})


class HitoPeriodo(BaseModel):
    """
    Fecha límite o evento importante dentro de un periodo.

    Ejemplos: fecha límite de entrega de notas, inicio de habilitaciones,
    entrega de boletines. Los hitos sirven para alertas automáticas
    y para mostrar el cronograma en el panel de director.
    """
    id:          int | None  = None
    periodo_id:  int
    tipo:        TipoHito    = TipoHito.GENERAL
    descripcion: str | None  = None
    fecha_limite: date | None = None

    @field_validator("periodo_id")
    @classmethod
    def validar_periodo_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"periodo_id debe ser positivo (recibido: {v}).")
        return v

    @field_validator("descripcion", mode="before")
    @classmethod
    def limpiar_descripcion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @property
    def esta_vencido(self) -> bool:
        """True si la fecha límite ya pasó."""
        if self.fecha_limite is None:
            return False
        return self.fecha_limite < date.today()

    @property
    def dias_restantes(self) -> int | None:
        """Días que faltan para el hito. Negativo si ya venció."""
        if self.fecha_limite is None:
            return None
        return (self.fecha_limite - date.today()).days


# =============================================================================
# DTOs
# =============================================================================

class NuevoPeriodoDTO(BaseModel):
    """Datos para crear un periodo nuevo."""
    anio_id:         int
    numero:          int
    nombre:          str
    peso_porcentual: float          = 25.0
    fecha_inicio:    date | None    = None
    fecha_fin:       date | None    = None

    @field_validator("numero")
    @classmethod
    def validar_numero(cls, v: int) -> int:
        if not (1 <= v <= 6):
            raise ValueError(f"El número debe estar entre 1 y 6 (recibido: {v}).")
        return v

    @field_validator("peso_porcentual")
    @classmethod
    def validar_peso(cls, v: float) -> float:
        if not (0 < v <= 100):
            raise ValueError(f"El peso debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    @model_validator(mode="after")
    def validar_fechas(self) -> Self:
        if (
            self.fecha_inicio and self.fecha_fin
            and self.fecha_inicio > self.fecha_fin
        ):
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")
        return self

    def to_periodo(self) -> Periodo:
        return Periodo(**self.model_dump())


class ActualizarPeriodoDTO(BaseModel):
    """Campos actualizables de un periodo. Todos opcionales."""
    nombre:          str | None     = None
    peso_porcentual: float | None   = None
    fecha_inicio:    date | None    = None
    fecha_fin:       date | None    = None
    activo:          bool | None    = None

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    def aplicar_a(self, periodo: Periodo) -> Periodo:
        if periodo.cerrado:
            raise ValueError(
                "No se puede modificar un periodo cerrado."
            )
        cambios = {k: v for k, v in self.model_dump().items() if v is not None}
        return periodo.model_copy(update=cambios) if cambios else periodo


class NuevoHitoPeriodoDTO(BaseModel):
    """
    Datos para registrar un hito dentro de un periodo.

    `descripcion` es obligatoria — un hito sin descripción no tiene
    significado para el usuario. `fecha_limite` es obligatoria en la
    UI pero se acepta como None para hitos de tipo informativo sin
    fecha límite definida.
    """
    periodo_id:   int
    tipo:         TipoHito    = TipoHito.GENERAL
    descripcion:  str                          # requerida
    fecha_limite: date | None = None

    @field_validator("descripcion", mode="before")
    @classmethod
    def validar_descripcion(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("La descripción del hito no puede estar vacía.")
        if len(v) > 300:
            raise ValueError(
                f"La descripción no puede exceder 300 caracteres (tiene {len(v)})."
            )
        return v

    @field_validator("periodo_id")
    @classmethod
    def validar_periodo_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"periodo_id debe ser positivo (recibido: {v}).")
        return v

    def to_hito(self) -> HitoPeriodo:
        return HitoPeriodo(**self.model_dump())


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "TipoHito",
    "Periodo",
    "HitoPeriodo",
    "NuevoPeriodoDTO",
    "ActualizarPeriodoDTO",
    "NuevoHitoPeriodoDTO",
]