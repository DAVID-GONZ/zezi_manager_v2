"""Modelos de dominio para Plan de Mejoramiento."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator


class EstadoNotaCorte(str, Enum):
    SIN_PLAN = "sin_plan"       # Aprobó el corte, no va a plan
    EN_PLAN = "en_plan"         # Bajo umbral, en plan de mejoramiento
    APROBADO = "aprobado"       # Cerró el plan y aprobó
    REPROBADO = "reprobado"     # Cerró el plan y reprobó


class CortePlan(BaseModel):
    """Registro de un corte de plan de mejoramiento para una asignación en un periodo."""
    id: int | None = None
    asignacion_id: int
    periodo_id: int
    fecha_ejecucion: date = Field(default_factory=date.today)
    peso_registrado: float          # Suma de pesos de categorías con notas registradas (0..1)
    nota_umbral: float              # = peso_registrado * nota_minima_aprobacion
    nota_minima_aprobacion: float   # Umbral de aprobación del periodo (ej. 60.0)
    usuario_id: int | None = None   # Quién ejecutó el corte


class NotaCortePlan(BaseModel):
    """Nota de corte por estudiante. Todos los estudiantes tienen una."""
    id: int | None = None
    corte_id: int
    estudiante_id: int
    asignacion_id: int      # desnorm
    periodo_id: int         # desnorm
    nota_al_corte: float    # Contribución parcial al corte (escala 0-100)
    nota_definitiva_plan: float | None = None  # Congelado al cerrar el plan
    estado: EstadoNotaCorte = EstadoNotaCorte.SIN_PLAN
    usuario_cierre_id: int | None = None


class ActividadPlan(BaseModel):
    """Actividad de plan de mejoramiento (columna compartida para todos los en-plan)."""
    id: int | None = None
    corte_id: int
    asignacion_id: int      # desnorm
    periodo_id: int         # desnorm
    nombre: str
    descripcion: str | None = None
    peso: float             # (0, 1.0] - fracción del peso del plan
    fecha: date | None = None
    usuario_id: int | None = None

    @field_validator("peso")
    @classmethod
    def peso_valido(cls, v: float) -> float:
        if not (0 < v <= 1.0):
            raise ValueError("El peso debe estar entre 0 y 1.0 (exclusivo en 0)")
        return v


class NotaActividadPlan(BaseModel):
    """Nota de una actividad del plan por estudiante (celda)."""
    id: int | None = None
    actividad_plan_id: int
    estudiante_id: int
    asignacion_id: int      # desnorm
    periodo_id: int         # desnorm
    valor: float | None = None
    usuario_id: int | None = None


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

class EjecutarCorteDTO(BaseModel):
    """Datos para ejecutar un corte de plan de mejoramiento."""
    asignacion_id: int
    periodo_id: int
    nota_minima_aprobacion: float = 60.0    # Umbral de aprobación (0-100)
    usuario_id: int | None = None


class NuevaActividadPlanDTO(BaseModel):
    """Datos para crear una actividad de plan de mejoramiento."""
    corte_id: int
    asignacion_id: int
    periodo_id: int
    nombre: str
    descripcion: str | None = None
    peso: float
    fecha: date | None = None

    @field_validator("peso")
    @classmethod
    def peso_valido(cls, v: float) -> float:
        if not (0 < v <= 1.0):
            raise ValueError("El peso debe ser mayor a 0 y hasta 1.0")
        return v

    def to_actividad(self, usuario_id: int | None = None) -> ActividadPlan:
        return ActividadPlan(
            corte_id=self.corte_id,
            asignacion_id=self.asignacion_id,
            periodo_id=self.periodo_id,
            nombre=self.nombre,
            descripcion=self.descripcion,
            peso=self.peso,
            fecha=self.fecha,
            usuario_id=usuario_id,
        )


class CalificarNotaPlanDTO(BaseModel):
    """Datos para calificar la nota de una actividad de plan."""
    valor: float
    usuario_id: int | None = None

    @field_validator("valor")
    @classmethod
    def valor_valido(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError("El valor debe estar entre 0 y 100")
        return v


class CerrarPlanEstudianteDTO(BaseModel):
    """Datos para cerrar el plan de un estudiante específico."""
    estudiante_id: int
    corte_id: int
    aprobado: bool          # True → APROBADO, False → REPROBADO
    usuario_cierre_id: int | None = None


# ---------------------------------------------------------------------------
# Calculador
# ---------------------------------------------------------------------------

class CalculadorPlan:
    """Utilidades de cálculo para Plan de Mejoramiento."""

    @staticmethod
    def nota_al_corte(
        categorias_con_notas: list[dict],
    ) -> float:
        """
        Calcula la contribución parcial al corte.

        Cada ítem en `categorias_con_notas` debe tener:
            - "peso": float  (fracción 0..1, ej. 0.3)
            - "promedio": float  (0-100)

        Retorna la suma de contribuciones (escala 0-100 proporcional).
        """
        return sum(c["peso"] * c["promedio"] for c in categorias_con_notas)

    @staticmethod
    def peso_registrado(categorias_con_notas: list[dict]) -> float:
        """Suma de pesos de categorías que tienen al menos una nota registrada."""
        return sum(c["peso"] for c in categorias_con_notas)

    @staticmethod
    def nota_umbral(peso_registrado: float, nota_minima: float) -> float:
        """Umbral de aprobación proporcional al peso registrado."""
        return peso_registrado * nota_minima

    @staticmethod
    def nota_definitiva_aprobado(peso_registrado: float, nota_minima: float) -> float:
        """Nota definitiva del plan si el estudiante aprobó."""
        return peso_registrado * nota_minima

    @staticmethod
    def suma_pesos_actividades(actividades: list[ActividadPlan]) -> float:
        return sum(a.peso for a in actividades)

    @staticmethod
    def pesos_completos(actividades: list[ActividadPlan], tolerancia: float = 0.005) -> bool:
        """Verifica que la suma de pesos de actividades sea ~1.0."""
        return abs(CalculadorPlan.suma_pesos_actividades(actividades) - 1.0) <= tolerancia

    @staticmethod
    def nota_plan_estudiante(
        notas: list[NotaActividadPlan],
        actividades: list[ActividadPlan],
    ) -> float | None:
        """
        Promedio ponderado de las actividades del plan para un estudiante.
        Retorna None si alguna nota no está registrada.
        """
        if not actividades:
            return None
        mapa_actividades = {a.id: a for a in actividades}
        total = 0.0
        for n in notas:
            if n.valor is None:
                return None
            act = mapa_actividades.get(n.actividad_plan_id)
            if act is None:
                return None
            total += act.peso * n.valor
        return total
