"""Modelos de dominio para Plan de Mejoramiento."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from pydantic import Field, field_validator

from src.domain.models.base import DTODominio, EntidadDominio
from src.domain.models.decimal_types import QUANT_NOTA, NotaDecimal, PesoDecimal


class EstadoNotaCorte(StrEnum):
    SIN_PLAN = "sin_plan"  # Aprobó el corte, no va a plan
    EN_PLAN = "en_plan"  # Bajo umbral, en plan de mejoramiento
    APROBADO = "aprobado"  # Cerró el plan y aprobó
    REPROBADO = "reprobado"  # Cerró el plan y reprobó


class CortePlan(EntidadDominio):
    """Registro de un corte de plan de mejoramiento para una asignación en un periodo."""

    id: int | None = None
    asignacion_id: int
    periodo_id: int
    fecha_ejecucion: date = Field(default_factory=date.today)
    peso_registrado: PesoDecimal  # Suma de pesos de categorías con notas registradas (0..1)
    nota_umbral: NotaDecimal  # = peso_registrado * nota_minima_aprobacion
    nota_minima_aprobacion: NotaDecimal  # Umbral de aprobación del periodo (ej. 60.0)
    usuario_id: int | None = None  # Quién ejecutó el corte


class NotaCortePlan(EntidadDominio):
    """Nota de corte por estudiante. Todos los estudiantes tienen una."""

    id: int | None = None
    corte_id: int
    estudiante_id: int
    asignacion_id: int  # desnorm
    periodo_id: int  # desnorm
    nota_al_corte: NotaDecimal  # Contribución parcial al corte (escala 0-100)
    nota_definitiva_plan: NotaDecimal | None = None  # Congelado al cerrar el plan
    estado: EstadoNotaCorte = EstadoNotaCorte.SIN_PLAN
    usuario_cierre_id: int | None = None


class ActividadPlan(EntidadDominio):
    """Actividad de plan de mejoramiento (columna compartida para todos los en-plan)."""

    id: int | None = None
    corte_id: int
    asignacion_id: int  # desnorm
    periodo_id: int  # desnorm
    nombre: str
    descripcion: str | None = None
    peso: PesoDecimal  # (0, 1.0] - fracción del peso del plan
    fecha: date | None = None
    usuario_id: int | None = None

    @field_validator("peso")
    @classmethod
    def peso_valido(cls, v: Decimal) -> Decimal:
        """El peso de la actividad debe estar en (0, 1.0] (fracción del peso del plan)."""
        if not (0 < v <= Decimal("1")):
            raise ValueError("El peso debe estar entre 0 y 1.0 (exclusivo en 0)")
        return v


class NotaActividadPlan(EntidadDominio):
    """Nota de una actividad del plan por estudiante (celda)."""

    id: int | None = None
    actividad_plan_id: int
    estudiante_id: int
    asignacion_id: int  # desnorm
    periodo_id: int  # desnorm
    valor: NotaDecimal | None = None
    usuario_id: int | None = None


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class EjecutarCorteDTO(DTODominio):
    """Datos para ejecutar un corte de plan de mejoramiento."""

    asignacion_id: int
    periodo_id: int
    nota_minima_aprobacion: NotaDecimal = Decimal("60.00")  # Umbral de aprobación (0-100)
    usuario_id: int | None = None


class NuevaActividadPlanDTO(DTODominio):
    """Datos para crear una actividad de plan de mejoramiento."""

    corte_id: int
    asignacion_id: int
    periodo_id: int
    nombre: str
    descripcion: str | None = None
    peso: PesoDecimal
    fecha: date | None = None

    @field_validator("peso")
    @classmethod
    def peso_valido(cls, v: Decimal) -> Decimal:
        """El peso de la actividad debe estar en (0, 1.0]."""
        if not (0 < v <= Decimal("1")):
            raise ValueError("El peso debe ser mayor a 0 y hasta 1.0")
        return v

    def to_actividad(self, usuario_id: int | None = None) -> ActividadPlan:
        """Construye una ActividadPlan del DTO, fijando el usuario que la crea."""
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


class CalificarNotaPlanDTO(DTODominio):
    """Datos para calificar la nota de una actividad de plan."""

    valor: NotaDecimal
    usuario_id: int | None = None

    @field_validator("valor")
    @classmethod
    def valor_valido(cls, v: Decimal) -> Decimal:
        """La nota de la actividad de plan debe estar en 0-100."""
        if not (0 <= v <= 100):
            raise ValueError("El valor debe estar entre 0 y 100")
        return v


class CerrarPlanEstudianteDTO(DTODominio):
    """Datos para cerrar el plan de un estudiante específico."""

    estudiante_id: int
    corte_id: int
    aprobado: bool  # True → APROBADO, False → REPROBADO
    usuario_cierre_id: int | None = None


# ---------------------------------------------------------------------------
# Calculador
# ---------------------------------------------------------------------------


class CalculadorPlan:
    """Utilidades de cálculo para Plan de Mejoramiento."""

    @staticmethod
    def nota_al_corte(
        categorias_con_notas: list[dict],
    ) -> Decimal:
        """
        Calcula la contribución parcial al corte.

        Cada ítem en `categorias_con_notas` debe tener:
            - "peso": Decimal  (fracción 0..1, ej. Decimal("0.3"))
            - "promedio": Decimal  (0-100)

        Retorna la suma de contribuciones (escala 0-100 proporcional).
        """
        return sum(
            (Decimal(str(c["peso"])) * Decimal(str(c["promedio"])) for c in categorias_con_notas),
            Decimal("0"),
        ).quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)

    @staticmethod
    def peso_registrado(categorias_con_notas: list[dict]) -> Decimal:
        """Suma de pesos de categorías que tienen al menos una nota registrada."""
        return sum(
            (Decimal(str(c["peso"])) for c in categorias_con_notas),
            Decimal("0"),
        )

    @staticmethod
    def nota_umbral(peso_registrado: Decimal, nota_minima: Decimal) -> Decimal:
        """Umbral de aprobación proporcional al peso registrado."""
        if not isinstance(peso_registrado, Decimal):
            peso_registrado = Decimal(str(peso_registrado))
        if not isinstance(nota_minima, Decimal):
            nota_minima = Decimal(str(nota_minima))
        return (peso_registrado * nota_minima).quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)

    @staticmethod
    def nota_definitiva_aprobado(peso_registrado: Decimal, nota_minima: Decimal) -> Decimal:
        """Nota definitiva del plan si el estudiante aprobó."""
        if not isinstance(peso_registrado, Decimal):
            peso_registrado = Decimal(str(peso_registrado))
        if not isinstance(nota_minima, Decimal):
            nota_minima = Decimal(str(nota_minima))
        return (peso_registrado * nota_minima).quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)

    @staticmethod
    def suma_pesos_actividades(actividades: list[ActividadPlan]) -> Decimal:
        """Suma exacta de los pesos de todas las actividades del plan."""
        return sum((a.peso for a in actividades), Decimal("0"))

    @staticmethod
    def pesos_completos(actividades: list[ActividadPlan], tolerancia: Decimal = Decimal("0")) -> bool:
        """Verifica que la suma de pesos de actividades sea exactamente 1.0."""
        return abs(CalculadorPlan.suma_pesos_actividades(actividades) - Decimal("1")) <= tolerancia

    @staticmethod
    def nota_plan_estudiante(
        notas: list[NotaActividadPlan],
        actividades: list[ActividadPlan],
    ) -> Decimal | None:
        """
        Promedio ponderado de las actividades del plan para un estudiante.
        Retorna None si alguna nota no está registrada.
        """
        if not actividades:
            return None
        mapa_actividades = {a.id: a for a in actividades}
        total = Decimal("0")
        for n in notas:
            if n.valor is None:
                return None
            act = mapa_actividades.get(n.actividad_plan_id)
            if act is None:
                return None
            total += act.peso * n.valor
        return total.quantize(QUANT_NOTA, rounding=ROUND_HALF_UP)
