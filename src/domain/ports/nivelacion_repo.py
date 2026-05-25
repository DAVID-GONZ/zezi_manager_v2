"""
Port: INivelacionRepository
==============================
Contrato de acceso a datos para el módulo de nivelación.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.nivelacion import (
    ActividadNivelacion,
    CierreNivelacion,
    NotaNivelacion,
)


class INivelacionRepository(ABC):

    # =========================================================================
    # ActividadNivelacion
    # =========================================================================

    @abstractmethod
    def guardar_actividad(self, actividad: ActividadNivelacion) -> ActividadNivelacion:
        """Inserta una actividad de nivelación. Retorna la entidad con id."""
        ...

    @abstractmethod
    def listar_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[ActividadNivelacion]:
        """Lista actividades de nivelación para una asignacion+periodo."""
        ...

    @abstractmethod
    def get_actividad(self, actividad_id: int) -> ActividadNivelacion | None:
        """Retorna la actividad por id, o None."""
        ...

    @abstractmethod
    def suma_pesos_actividades(
        self,
        asignacion_id: int,
        periodo_id: int,
        excluir_id: int | None = None,
    ) -> float:
        """Suma de pesos de actividades para asignacion+periodo. Excluye excluir_id si dado."""
        ...

    # =========================================================================
    # NotaNivelacion
    # =========================================================================

    @abstractmethod
    def guardar_nota(self, nota: NotaNivelacion) -> NotaNivelacion:
        """Inserta una nota (upsert por actividad_nivelacion_id+estudiante_id)."""
        ...

    @abstractmethod
    def actualizar_nota(self, nota: NotaNivelacion) -> NotaNivelacion:
        """Actualiza el valor de una nota existente."""
        ...

    @abstractmethod
    def listar_notas_por_actividad(
        self,
        actividad_nivelacion_id: int,
    ) -> list[NotaNivelacion]:
        """Lista todas las notas de una actividad."""
        ...

    @abstractmethod
    def listar_notas_por_asignacion(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> list[NotaNivelacion]:
        """Lista todas las notas de una asignacion+periodo (todas las actividades)."""
        ...

    @abstractmethod
    def get_nota(
        self,
        actividad_nivelacion_id: int,
        estudiante_id: int,
    ) -> NotaNivelacion | None:
        """Retorna la nota de un estudiante en una actividad, o None."""
        ...

    # =========================================================================
    # CierreNivelacion
    # =========================================================================

    @abstractmethod
    def guardar_cierre(self, cierre: CierreNivelacion) -> CierreNivelacion:
        """Persiste el registro de cierre. Retorna con id."""
        ...

    @abstractmethod
    def get_cierre(
        self,
        asignacion_id: int,
        periodo_id: int,
    ) -> CierreNivelacion | None:
        """Retorna el cierre si existe, None si la nivelación está abierta."""
        ...


__all__ = ["INivelacionRepository"]
