"""Puerto (interfaz) para el repositorio de Plan de Mejoramiento."""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.plan_mejoramiento import (
    ActividadPlan,
    CortePlan,
    NotaActividadPlan,
    NotaCortePlan,
)


class IPlanMejoramientoRepository(ABC):
    """Contrato que toda implementación de repositorio debe cumplir."""

    # ------------------------------------------------------------------
    # Corte
    # ------------------------------------------------------------------

    @abstractmethod
    def guardar_corte(self, corte: CortePlan) -> CortePlan:
        """Persiste un nuevo corte. Retorna la instancia con id asignado."""

    @abstractmethod
    def get_corte(self, asignacion_id: int, periodo_id: int) -> CortePlan | None:
        """Obtiene el corte de una asignación en un periodo, o None."""

    @abstractmethod
    def get_corte_by_id(self, corte_id: int) -> CortePlan | None:
        """Obtiene un corte por su id primario."""

    # ------------------------------------------------------------------
    # Notas de corte
    # ------------------------------------------------------------------

    @abstractmethod
    def guardar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan:
        """Persiste una nota de corte (INSERT OR REPLACE)."""

    @abstractmethod
    def get_nota_corte(self, corte_id: int, estudiante_id: int) -> NotaCortePlan | None:
        """Obtiene la nota de corte de un estudiante específico."""

    @abstractmethod
    def listar_notas_corte(self, corte_id: int) -> list[NotaCortePlan]:
        """Lista todas las notas de corte para un corte dado."""

    @abstractmethod
    def actualizar_nota_corte(self, nota: NotaCortePlan) -> NotaCortePlan:
        """Actualiza una nota de corte existente (cierre de plan)."""

    # ------------------------------------------------------------------
    # Actividades del plan
    # ------------------------------------------------------------------

    @abstractmethod
    def guardar_actividad(self, actividad: ActividadPlan) -> ActividadPlan:
        """Persiste una nueva actividad de plan."""

    @abstractmethod
    def get_actividad(self, actividad_id: int) -> ActividadPlan | None:
        """Obtiene una actividad por su id."""

    @abstractmethod
    def listar_actividades(self, corte_id: int) -> list[ActividadPlan]:
        """Lista todas las actividades de un corte."""

    @abstractmethod
    def suma_pesos_actividades(self, corte_id: int, excluir_id: int | None = None) -> float:
        """Suma de pesos de las actividades de un corte, excluyendo opcionalmente una."""

    # ------------------------------------------------------------------
    # Notas de actividades
    # ------------------------------------------------------------------

    @abstractmethod
    def guardar_nota_actividad(self, nota: NotaActividadPlan) -> NotaActividadPlan:
        """Persiste una nota de actividad (INSERT OR REPLACE)."""

    @abstractmethod
    def get_nota_actividad(
        self, actividad_plan_id: int, estudiante_id: int
    ) -> NotaActividadPlan | None:
        """Obtiene la nota de un estudiante para una actividad."""

    @abstractmethod
    def listar_notas_actividad(self, actividad_plan_id: int) -> list[NotaActividadPlan]:
        """Lista todas las notas de una actividad."""

    @abstractmethod
    def listar_notas_por_corte_estudiante(
        self, corte_id: int, estudiante_id: int
    ) -> list[NotaActividadPlan]:
        """Lista todas las notas de actividades del plan para un estudiante en un corte."""
