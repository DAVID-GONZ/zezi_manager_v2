"""
Port: IInstitucionRepository
==============================
Contrato de acceso a datos para el catálogo de instituciones (tenants).

Cubre:
  Institucion — entidad persistida (nombre, nit/codigo, activa)

Principios (paso_24):
  - La institución #1 es la institución por defecto, sembrada desde la
    configuración institucional existente.
  - El servicio garantiza la unicidad del nombre antes de insertar.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.institucion import Institucion


class IInstitucionRepository(ABC):
    @abstractmethod
    def get_by_id(self, institucion_id: int) -> Institucion | None:
        """Retorna la institución con ese id, o None si no existe."""
        ...

    @abstractmethod
    def listar(self, solo_activas: bool = False) -> list[Institucion]:
        """
        Retorna las instituciones ordenadas por id.
        Si `solo_activas`, omite las marcadas como inactivas.
        """
        ...

    @abstractmethod
    def existe_nombre(self, nombre: str) -> bool:
        """True si ya existe una institución con ese nombre (case-insensitive)."""
        ...

    @abstractmethod
    def guardar(self, institucion: Institucion) -> Institucion:
        """Inserta una institución nueva. Retorna la entidad con id asignado."""
        ...

    @abstractmethod
    def get_por_defecto(self) -> Institucion | None:
        """
        Retorna la institución por defecto (id mínimo / institución #1),
        o None si no hay ninguna.
        """
        ...

    @abstractmethod
    def actualizar(self, institucion: Institucion) -> Institucion:
        """Actualiza los campos de una institución existente. Lanza ValueError si no existe."""
        ...

    @abstractmethod
    def sembrar_defaults_tenant(self, institucion_id: int) -> None:
        """
        Siembra catálogos estándar (áreas, categorías) + preferencias por
        defecto para un tenant nuevo (mejora_09a). Idempotente (INSERT OR
        IGNORE): puede llamarse varias veces sin duplicar datos.
        """
        ...


__all__ = ["IInstitucionRepository"]
