"""
Port: IPeriodoRepository
==========================
Contrato de acceso a datos para el módulo de periodos académicos.

Cubre:
  Periodo     — periodo académico dentro de un año lectivo
  HitoPeriodo — fechas límite y eventos importantes del periodo

Reglas que el repositorio debe respetar:
  - Un periodo cerrado (cerrado=True) no puede modificarse.
    El servicio verifica periodo.esta_abierto antes de actualizar.
  - La unicidad (anio_id, numero) la garantiza la BD con UNIQUE constraint.
  - La suma de pesos de los periodos de un año debe ser 100%:
    el servicio la verifica con `suma_pesos_otros` antes de insertar/actualizar.

Patrones de uso principales:

  Obtener el periodo activo para registrar notas/asistencia:
    periodo = repo.get_activo(anio_id)
    if periodo is None or not periodo.esta_abierto:
        raise ValueError("No hay periodo activo abierto.")

  Cerrar el periodo al fin del trimestre:
    periodo = repo.get_by_id(periodo_id)
    cerrado = periodo.cerrar()
    repo.actualizar(cerrado)

  Agregar hitos para el cronograma:
    repo.guardar_hito(NuevoHitoPeriodoDTO(
        periodo_id=pid,
        tipo=TipoHito.ENTREGA_NOTAS,
        descripcion="Fecha límite entrega de notas P1",
        fecha_limite=date(2026, 3, 31),
    ).to_hito())
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..models.periodo import HitoPeriodo, Periodo, TipoHito


class IPeriodoRepository(ABC):

    # =========================================================================
    # Lectura — periodos
    # =========================================================================

    @abstractmethod
    def get_by_id(self, periodo_id: int) -> Periodo | None:
        """Retorna el periodo con ese id, o None si no existe."""
        ...

    @abstractmethod
    def get_por_numero(self, anio_id: int, numero: int) -> Periodo | None:
        """
        Retorna el periodo de un año por su número (1–6).
        None si no existe. Respeta la UNIQUE constraint (anio_id, numero).
        """
        ...

    @abstractmethod
    def get_activo(self, anio_id: int) -> Periodo | None:
        """
        Retorna el periodo activo (activo=True, cerrado=False) del año.
        None si no hay periodo activo.
        Normalmente solo hay uno activo a la vez, pero si hay varios
        retorna el de menor número.
        """
        ...

    @abstractmethod
    def listar_por_anio(
        self,
        anio_id: int,
        incluir_cerrados: bool = True,
    ) -> list[Periodo]:
        """
        Retorna todos los periodos de un año lectivo, ordenados por numero.
        Si incluir_cerrados=False, excluye los periodos cerrados.
        Usado para validar la suma de pesos y para selects en la UI.
        """
        ...

    @abstractmethod
    def suma_pesos_otros(
        self,
        anio_id: int,
        excluir_periodo_id: int | None = None,
    ) -> float:
        """
        Suma de los pesos porcentuales de los periodos del año,
        excluyendo opcionalmente el periodo indicado.

        Uso típico antes de crear/actualizar:
          suma = repo.suma_pesos_otros(anio_id, excluir_periodo_id=periodo.id)
          if suma + nuevo_peso > 100.01:
              raise ValueError("Los pesos superan el 100%")
        """
        ...

    # =========================================================================
    # Escritura — periodos
    # =========================================================================

    @abstractmethod
    def guardar(self, periodo: Periodo) -> Periodo:
        """
        Inserta un periodo nuevo. Retorna la entidad con id asignado.
        El servicio debe verificar unicidad (anio_id, numero) y suma de pesos.
        """
        ...

    @abstractmethod
    def actualizar(self, periodo: Periodo) -> Periodo:
        """
        Actualiza un periodo existente (nombre, fechas, peso, activo).
        No modifica el campo `cerrado` — use `cerrar` para eso.
        Requiere que periodo.id no sea None.
        El servicio debe verificar que el periodo no esté cerrado.
        """
        ...

    @abstractmethod
    def cerrar(self, periodo_id: int) -> bool:
        """
        Marca el periodo como cerrado (cerrado=True, activo=False)
        y registra la fecha_cierre_real=now().
        Retorna True si la fila fue afectada.
        Esta operación es irreversible.
        El servicio debe verificar que el periodo esté abierto.
        """
        ...

    @abstractmethod
    def activar(self, periodo_id: int) -> bool:
        """
        Marca el periodo como activo (activo=True).
        Retorna True si la fila fue afectada.
        El servicio debe verificar que el periodo no esté cerrado.
        """
        ...

    @abstractmethod
    def desactivar(self, periodo_id: int) -> bool:
        """
        Marca el periodo como inactivo (activo=False).
        Retorna True si la fila fue afectada.
        """
        ...

    # =========================================================================
    # Lectura — hitos
    # =========================================================================

    @abstractmethod
    def get_hito(self, hito_id: int) -> HitoPeriodo | None:
        """Retorna el hito con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar_hitos(
        self,
        periodo_id: int,
        tipo: TipoHito | None = None,
    ) -> list[HitoPeriodo]:
        """
        Retorna los hitos de un periodo, opcionalmente filtrados por tipo.
        Ordenados por fecha_limite (nulls al final), luego por id.
        """
        ...

    @abstractmethod
    def listar_hitos_proximos(
        self,
        anio_id: int,
        dias: int = 7,
    ) -> list[HitoPeriodo]:
        """
        Retorna los hitos de todos los periodos del año cuya fecha_limite
        está en los próximos `dias` días (inclusive hoy).
        Usado para el panel de cronograma del director.
        """
        ...

    # =========================================================================
    # Escritura — hitos
    # =========================================================================

    @abstractmethod
    def guardar_hito(self, hito: HitoPeriodo) -> HitoPeriodo:
        """Inserta un hito nuevo. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def actualizar_hito(self, hito: HitoPeriodo) -> HitoPeriodo:
        """Actualiza descripción, tipo y/o fecha_limite de un hito existente."""
        ...

    @abstractmethod
    def eliminar_hito(self, hito_id: int) -> bool:
        """Elimina un hito. Retorna True si la fila fue afectada."""
        ...


__all__ = ["IPeriodoRepository"]
