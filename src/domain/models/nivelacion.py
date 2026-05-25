"""
Módulo de Nivelación — ZECI Manager v2
=======================================
Entidades para el proceso de nivelación posterior al cierre de período.

Decreto 1290: las instituciones deben ofrecer actividades de recuperación
documentadas a estudiantes con desempeño bajo.

Arquitectura:
  ActividadNivelacion  — columna compartida por todos los bajo-desempeño de una asignatura en un período
  NotaNivelacion       — celda: nota de un estudiante en una actividad
  CierreNivelacion     — registro de cierre (uno por asignacion+periodo); su existencia indica "cerrado"

La nota definitiva de nivelación por estudiante = Σ(NotaNivelacion.valor × ActividadNivelacion.peso).
No se almacena redundantemente; se computa al consultar.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator, model_validator

if TYPE_CHECKING:
    pass


class ActividadNivelacion(BaseModel):
    """
    Columna de la planilla de nivelación.
    Compartida por todos los estudiantes con bajo desempeño de esa asignacion+periodo.

    peso: fracción del total (0 < peso ≤ 1.0).
    La suma de pesos de todas las actividades de una asignacion+periodo debe ser 1.0
    para poder cerrar la nivelación. El servicio valida esto.
    """
    id:            int | None = None
    asignacion_id: int
    periodo_id:    int
    nombre:        str
    descripcion:   str | None = None
    peso:          float          # (0, 1.0]
    fecha:         date | None = None
    usuario_id:    int | None = None

    @field_validator("asignacion_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("peso")
    @classmethod
    def validar_peso(cls, v: float) -> float:
        if not (0 < v <= 1.0):
            raise ValueError(
                f"El peso debe estar en el rango (0, 1.0] (recibido: {v})."
            )
        return round(v, 4)

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre de la actividad no puede estar vacío.")
        if len(v) > 120:
            raise ValueError("El nombre no puede superar 120 caracteres.")
        return v

    @field_validator("descripcion", mode="before")
    @classmethod
    def limpiar_descripcion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None


class NotaNivelacion(BaseModel):
    """
    Celda de la planilla de nivelación.
    Una por (estudiante × actividad_nivelacion).

    valor=None → pendiente de calificación.
    """
    id:                      int | None   = None
    actividad_nivelacion_id: int
    estudiante_id:           int
    asignacion_id:           int          # desnormalizado para queries
    periodo_id:              int          # desnormalizado para queries
    valor:                   float | None = None
    usuario_id:              int | None   = None

    @field_validator("actividad_nivelacion_id", "estudiante_id",
                     "asignacion_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if not (0 <= v <= 100):
            raise ValueError(f"La nota debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)

    @property
    def calificada(self) -> bool:
        return self.valor is not None


class CierreNivelacion(BaseModel):
    """
    Registro de cierre de nivelación para una asignacion+periodo.
    Su existencia implica que la nivelación está cerrada (read-only).
    La nota definitiva por estudiante se calcula sobre las NotaNivelacion persistidas.
    """
    id:               int | None = None
    asignacion_id:    int
    periodo_id:       int
    fecha_cierre:     date = Field(default_factory=date.today)
    usuario_cierre_id: int | None = None

    @field_validator("asignacion_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v


class CalculadorNivelacion:
    """
    Utilidad estática para cálculos de nivelación.
    No tiene estado; solo recibe datos y retorna resultados.
    """

    @staticmethod
    def nota_definitiva(
        notas: list[NotaNivelacion],
        actividades: list[ActividadNivelacion],
    ) -> float | None:
        """
        Calcula el promedio ponderado de las notas de nivelación.
        Retorna None si no hay actividades o alguna nota está sin calificar.
        """
        if not actividades:
            return None
        act_map = {a.id: a for a in actividades if a.id is not None}
        total_peso = 0.0
        total = 0.0
        for nota in notas:
            act = act_map.get(nota.actividad_nivelacion_id)
            if act is None or nota.valor is None:
                return None   # incompleto
            total      += nota.valor * act.peso
            total_peso += act.peso
        if total_peso == 0:
            return None
        return round(total / total_peso * total_peso, 2)  # = round(total, 2)

    @staticmethod
    def suma_pesos(actividades: list[ActividadNivelacion]) -> float:
        return round(sum(a.peso for a in actividades), 4)

    @staticmethod
    def pesos_completos(
        actividades: list[ActividadNivelacion],
        tolerancia: float = 0.005,
    ) -> bool:
        """True si la suma de pesos es 1.0 (con tolerancia de redondeo)."""
        return abs(CalculadorNivelacion.suma_pesos(actividades) - 1.0) <= tolerancia


# =============================================================================
# DTOs
# =============================================================================

class NuevaActividadNivelacionDTO(BaseModel):
    """Datos para crear una actividad de nivelación."""
    asignacion_id: int
    periodo_id:    int
    nombre:        str
    descripcion:   str | None = None
    peso:          float
    fecha:         date | None = None

    @field_validator("asignacion_id", "periodo_id")
    @classmethod
    def validar_id_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"El ID debe ser positivo (recibido: {v}).")
        return v

    @field_validator("peso")
    @classmethod
    def validar_peso(cls, v: float) -> float:
        if not (0 < v <= 1.0):
            raise ValueError(f"El peso debe estar en (0, 1.0] (recibido: {v}).")
        return round(v, 4)

    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v

    def to_actividad(self, usuario_id: int | None = None) -> ActividadNivelacion:
        return ActividadNivelacion(
            **self.model_dump(),
            usuario_id=usuario_id,
        )


class CalificarNotaNivelacionDTO(BaseModel):
    """Datos para calificar (upsert) una nota de nivelación."""
    valor:      float
    usuario_id: int | None = None

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError(f"La nota debe estar entre 0 y 100 (recibido: {v}).")
        return round(v, 2)


__all__ = [
    "ActividadNivelacion",
    "NotaNivelacion",
    "CierreNivelacion",
    "CalculadorNivelacion",
    "NuevaActividadNivelacionDTO",
    "CalificarNotaNivelacionDTO",
]
