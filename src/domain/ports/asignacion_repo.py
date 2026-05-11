"""
Port: IAsignacionRepository
=============================
Contrato de acceso a datos para el módulo de asignaciones.

La asignación es el pivot central del sistema: conecta un docente
con una asignatura, un grupo y un periodo. Toda evaluación, asistencia
y observación está ligada a una asignación.

Cubre:
  Asignacion     — entidad de escritura (solo IDs)
  AsignacionInfo — read model con nombres resueltos por JOIN

Patrones de uso principales:

  Crear una asignación nueva:
    if not repo.existe(grupo_id, asignatura_id, usuario_id, periodo_id):
        asignacion = repo.guardar(Asignacion(...))

  Obtener las asignaciones de un docente para el periodo activo:
    infos = repo.listar_info(FiltroAsignacionesDTO(
        usuario_id=docente_id, periodo_id=periodo_id
    ))

  Reasignar un grupo a otro docente:
    repo.reasignar_docente(asignacion_id, nuevo_usuario_id)

Invariante: la unicidad (grupo, asignatura, docente, periodo) la garantiza
la BD con UNIQUE constraint; el servicio la verifica con `existe` antes de insertar.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.asignacion import (
    Asignacion,
    AsignacionInfo,
    FiltroAsignacionesDTO,
)


class IAsignacionRepository(ABC):

    # =========================================================================
    # Lectura — entidad de persistencia
    # =========================================================================

    @abstractmethod
    def get_by_id(self, asignacion_id: int) -> Asignacion | None:
        """Retorna la asignación con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar(self, filtro: FiltroAsignacionesDTO) -> list[Asignacion]:
        """
        Retorna asignaciones según los filtros indicados.
        Uso interno: cuando solo se necesitan los IDs, sin JOIN.
        """
        ...

    @abstractmethod
    def existe(
        self,
        grupo_id: int,
        asignatura_id: int,
        usuario_id: int,
        periodo_id: int,
    ) -> bool:
        """
        True si ya existe una asignación con esa combinación exacta.
        El servicio llama esto antes de insertar para anticipar
        la violación del UNIQUE constraint de la BD.
        """
        ...

    # =========================================================================
    # Lectura — read model con JOINs
    # =========================================================================

    @abstractmethod
    def get_info(self, asignacion_id: int) -> AsignacionInfo | None:
        """
        Retorna la vista enriquecida de una asignación (con nombres
        de grupo, asignatura, docente y periodo resueltos por JOIN).
        None si la asignación no existe.
        """
        ...

    @abstractmethod
    def listar_info(self, filtro: FiltroAsignacionesDTO) -> list[AsignacionInfo]:
        """
        Retorna vistas enriquecidas de asignaciones según los filtros.
        Es la query principal para poblar grids y selects en la UI.
        Ordenadas por grupo_codigo, luego asignatura_nombre.
        """
        ...

    @abstractmethod
    def listar_por_grupo(
        self,
        grupo_id: int,
        periodo_id: int,
        solo_activas: bool = True,
    ) -> list[AsignacionInfo]:
        """
        Retorna todas las asignaciones de un grupo en un periodo.
        Usado para generar el horario completo del grupo y el boletín.
        """
        ...

    @abstractmethod
    def listar_por_docente(
        self,
        usuario_id: int,
        periodo_id: int | None = None,
        solo_activas: bool = True,
    ) -> list[AsignacionInfo]:
        """
        Retorna todas las asignaciones de un docente.
        Si periodo_id es None, retorna de todos los periodos.
        Usado para la vista de carga académica del docente.
        """
        ...

    # =========================================================================
    # Escritura
    # =========================================================================

    @abstractmethod
    def guardar(self, asignacion: Asignacion) -> Asignacion:
        """
        Inserta una asignación nueva.
        Retorna la entidad con id asignado.
        El servicio debe verificar unicidad con `existe` antes de llamar.
        """
        ...

    @abstractmethod
    def desactivar(self, asignacion_id: int) -> bool:
        """
        Marca la asignación como inactiva (activo=False, soft-delete).
        Los registros de evaluación y asistencia vinculados se conservan.
        Retorna True si la fila fue afectada.
        """
        ...

    @abstractmethod
    def reactivar(self, asignacion_id: int) -> bool:
        """
        Marca la asignación como activa (activo=True).
        Retorna True si la fila fue afectada.
        """
        ...

    @abstractmethod
    def reasignar_docente(
        self,
        asignacion_id: int,
        nuevo_usuario_id: int,
    ) -> bool:
        """
        Cambia el docente de una asignación existente.
        El historial de notas y asistencia permanece asociado
        a la asignación, no al docente.
        Retorna True si la fila fue afectada.
        """
        ...


__all__ = ["IAsignacionRepository"]
