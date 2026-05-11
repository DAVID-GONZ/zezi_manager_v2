"""
Port: IHabilitacionRepository
================================
Contrato de acceso a datos para el módulo de habilitaciones y planes de mejoramiento.

Cubre:
  Habilitacion    — actividad de recuperación de periodo o anual
  PlanMejoramiento — plan de trabajo para superar dificultades académicas

Marco legal: Decreto 1290 de 2009 — obliga a ofrecer actividades de
recuperación y planes de mejoramiento documentados.

Patrones de uso principales:

  Programar una habilitación:
    if not repo.existe_habilitacion(estudiante_id, asignacion_id, tipo=PERIODO, periodo_id=pid):
        hab = repo.guardar_habilitacion(NuevaHabilitacionDTO(...).to_habilitacion())

  Registrar la nota cuando se presenta:
    hab = repo.get_habilitacion(hab_id)
    hab_realizada = hab.registrar_nota(nota=72.5)
    repo.actualizar_habilitacion(hab_realizada)

  Crear un plan de mejoramiento:
    plan = repo.guardar_plan(dto.to_plan(usuario_id=docente_id))

  Listar planes vencidos para alertas:
    planes = repo.listar_planes_por_seguimiento(fecha_limite=date.today())
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..models.habilitacion import (
    EstadoHabilitacion,
    EstadoPlanMejoramiento,
    FiltroHabilitacionesDTO,
    Habilitacion,
    PlanMejoramiento,
    TipoHabilitacion,
)


class IHabilitacionRepository(ABC):

    # =========================================================================
    # Habilitaciones — lectura
    # =========================================================================

    @abstractmethod
    def get_habilitacion(self, habilitacion_id: int) -> Habilitacion | None:
        """Retorna la habilitación con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_habilitaciones(
        self,
        filtro: FiltroHabilitacionesDTO,
    ) -> list[Habilitacion]:
        """
        Retorna habilitaciones según los filtros indicados.
        Ordenadas por fecha (nulls al final), luego por id descendente.
        """
        ...

    @abstractmethod
    def listar_por_estudiante(
        self,
        estudiante_id: int,
        periodo_id: int | None = None,
        tipo: TipoHabilitacion | None = None,
    ) -> list[Habilitacion]:
        """
        Retorna todas las habilitaciones de un estudiante.
        Filtra opcionalmente por periodo y/o tipo.
        Ordenadas cronológicamente.
        """
        ...

    @abstractmethod
    def existe_habilitacion(
        self,
        estudiante_id: int,
        asignacion_id: int,
        tipo: TipoHabilitacion,
        periodo_id: int | None = None,
    ) -> bool:
        """
        True si ya existe una habilitación para esa combinación.
        Evita duplicar habilitaciones para el mismo estudiante,
        asignatura y periodo.
        """
        ...

    # =========================================================================
    # Habilitaciones — escritura
    # =========================================================================

    @abstractmethod
    def guardar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion:
        """
        Inserta una habilitación nueva.
        Retorna la entidad con id asignado.
        El servicio debe verificar con `existe_habilitacion` antes de llamar.
        """
        ...

    @abstractmethod
    def actualizar_habilitacion(self, habilitacion: Habilitacion) -> Habilitacion:
        """
        Actualiza el estado y los datos de una habilitación existente.
        Usado tras registrar_nota(), aprobar() o reprobar() en el modelo.
        Requiere que habilitacion.id no sea None.
        """
        ...

    @abstractmethod
    def actualizar_estado_habilitacion(
        self,
        habilitacion_id: int,
        estado: EstadoHabilitacion,
    ) -> bool:
        """
        Actualiza solo el estado de una habilitación.
        Más eficiente que actualizar_habilitacion() cuando solo cambia el estado.
        Retorna True si la fila fue afectada.
        """
        ...

    # =========================================================================
    # Planes de mejoramiento — lectura
    # =========================================================================

    @abstractmethod
    def get_plan(self, plan_id: int) -> PlanMejoramiento | None:
        """Retorna el plan de mejoramiento con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_planes_por_estudiante(
        self,
        estudiante_id: int,
        asignacion_id: int | None = None,
        estado: EstadoPlanMejoramiento | None = None,
    ) -> list[PlanMejoramiento]:
        """
        Retorna los planes de mejoramiento de un estudiante.
        Filtra opcionalmente por asignación y/o estado.
        Ordenados por fecha_inicio descendente.
        """
        ...

    @abstractmethod
    def listar_planes_por_seguimiento(
        self,
        fecha_limite: date,
        solo_activos: bool = True,
    ) -> list[PlanMejoramiento]:
        """
        Retorna planes cuya fecha_seguimiento es menor o igual a fecha_limite.
        Usado para el job de alertas de planes vencidos o próximos a vencer.
        Si solo_activos=True, filtra planes con estado=ACTIVO.
        """
        ...

    # =========================================================================
    # Planes de mejoramiento — escritura
    # =========================================================================

    @abstractmethod
    def guardar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento:
        """
        Inserta un plan de mejoramiento nuevo.
        Retorna la entidad con id asignado.
        """
        ...

    @abstractmethod
    def actualizar_plan(self, plan: PlanMejoramiento) -> PlanMejoramiento:
        """
        Actualiza un plan de mejoramiento existente.
        Usado tras programar_seguimiento() o cerrar() en el modelo.
        Requiere que plan.id no sea None.
        """
        ...


__all__ = ["IHabilitacionRepository"]
