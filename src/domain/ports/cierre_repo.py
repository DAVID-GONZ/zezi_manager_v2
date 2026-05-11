"""
Port: ICierreRepository
============================
Contrato de acceso a datos para el módulo de cierres y promoción.

Cubre:
  CierrePeriodo  — notas definitivas por periodo
  CierreAnio     — notas definitivas anuales
  PromocionAnual — decisión de promoción al siguiente año

Patrones de uso principales:

  Guardar o reemplazar un cierre de periodo (Upsert):
    cierre = repo.guardar_cierre_periodo(nuevo_cierre_periodo)

  Consultar estado de promoción:
    promocion = repo.get_promocion(estudiante_id, anio_id)
    
  Actualizar estado de promoción:
    repo.actualizar_promocion(promocion_decidida)

Invariantes del repositorio:
  - CierrePeriodo y CierreAnio son tratados como registros inmutables a nivel
    lógico, pero a nivel de persistencia un "guardar" actúa como Upsert 
    (reemplazo) si ocurre una corrección.
  - PromocionAnual mantiene estado, por lo que separa guardar (creación)
    de actualizar (decisión).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.cierre import (
    CierreAnio,
    CierrePeriodo,
    EstadoPromocion,
    PromocionAnual,
)


class ICierreRepository(ABC):

    # =========================================================================
    # Cierre Periodo
    # =========================================================================

    @abstractmethod
    def get_cierre_periodo(
        self, estudiante_id: int, asignacion_id: int, periodo_id: int
    ) -> CierrePeriodo | None:
        """
        Retorna el cierre de periodo para un estudiante en una asignación y 
        periodo específicos. Retorna None si no existe.
        """
        ...

    @abstractmethod
    def listar_cierres_periodo_por_estudiante(
        self, estudiante_id: int, periodo_id: int | None = None
    ) -> list[CierrePeriodo]:
        """
        Retorna los cierres de periodo de un estudiante.
        Si se especifica periodo_id, filtra exclusivamente por ese periodo.
        """
        ...

    @abstractmethod
    def guardar_cierre_periodo(self, cierre: CierrePeriodo) -> CierrePeriodo:
        """
        Guarda un cierre de periodo.
        Si ya existe uno para el mismo estudiante, asignación y periodo, 
        lo reemplaza (Upsert) para permitir correcciones excepcionales.
        Retorna la entidad guardada con su id.
        """
        ...

    # =========================================================================
    # Cierre Año
    # =========================================================================

    @abstractmethod
    def get_cierre_anio(
        self, estudiante_id: int, asignacion_id: int, anio_id: int
    ) -> CierreAnio | None:
        """
        Retorna el cierre anual para un estudiante en una asignación y año 
        específicos. Retorna None si no existe.
        """
        ...

    @abstractmethod
    def listar_cierres_anio_por_estudiante(
        self, estudiante_id: int, anio_id: int
    ) -> list[CierreAnio]:
        """
        Retorna todos los cierres anuales de un estudiante en un año específico.
        Útil para generar el boletín final y decidir la promoción.
        """
        ...

    @abstractmethod
    def guardar_cierre_anio(self, cierre: CierreAnio) -> CierreAnio:
        """
        Guarda un cierre anual.
        Si ya existe uno para el mismo estudiante, asignación y año, lo reemplaza 
        (Upsert) en caso de correcciones o ingreso de nota de habilitación.
        Retorna la entidad guardada con su id.
        """
        ...

    # =========================================================================
    # Promoción Anual
    # =========================================================================

    @abstractmethod
    def get_promocion(
        self, estudiante_id: int, anio_id: int
    ) -> PromocionAnual | None:
        """
        Retorna el registro de promoción de un estudiante para un año.
        Retorna None si no se ha iniciado el proceso de promoción.
        """
        ...

    @abstractmethod
    def listar_promociones(
        self, anio_id: int, estado: EstadoPromocion | None = None
    ) -> list[PromocionAnual]:
        """
        Lista todas las decisiones de promoción de un año. 
        Opcionalmente filtra por un estado específico (ej. PENDIENTE).
        """
        ...

    @abstractmethod
    def guardar_promocion(self, promocion: PromocionAnual) -> PromocionAnual:
        """
        Inserta un nuevo registro de promoción anual (usualmente inicializado 
        en estado PENDIENTE).
        Retorna la entidad con id asignado.
        """
        ...

    @abstractmethod
    def actualizar_promocion(self, promocion: PromocionAnual) -> PromocionAnual:
        """
        Actualiza el estado y detalles de una decisión de promoción existente.
        Debe ser usado cuando se aplica la decisión (PENDIENTE -> PROMOVIDO/REPROBADO).
        Requiere que promocion.id no sea None.
        """
        ...
