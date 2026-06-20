"""
InstitucionService
====================
Orquesta los casos de uso del catálogo de instituciones (tenants).

Primer ladrillo multi-tenant (paso_24): listar, crear y resolver la
institución por defecto (#1). No contiene SQL ni lógica de presentación.
"""
from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

from src.domain.ports.institucion_repo import IInstitucionRepository
from src.domain.models.institucion import (
    Institucion,
    InstitucionResumenDTO,
    NuevaInstitucionDTO,
)


class InstitucionService:
    """
    Orquesta los casos de uso del módulo de Instituciones.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(self, repo: IInstitucionRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def listar(self, solo_activas: bool = False) -> list[InstitucionResumenDTO]:
        """Retorna el resumen de instituciones para selects y filtros."""
        return [
            InstitucionResumenDTO.desde_institucion(i)
            for i in self._repo.listar(solo_activas=solo_activas)
        ]

    def get(self, institucion_id: int) -> Institucion:
        """Retorna una institución por id. Lanza si no existe."""
        institucion = self._repo.get_by_id(institucion_id)
        if institucion is None:
            raise ValueError(f"La institución con id {institucion_id} no existe.")
        return institucion

    def get_por_defecto(self) -> Institucion | None:
        """
        Retorna la institución por defecto (#1), o None si aún no hay ninguna.
        Usada como destino del backfill y como default de usuarios nuevos.
        """
        return self._repo.get_por_defecto()

    def id_por_defecto(self) -> int | None:
        """Atajo: el id de la institución por defecto, o None si no hay ninguna."""
        institucion = self._repo.get_por_defecto()
        return institucion.id if institucion else None

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    @requiere_escritura
    def crear(self, dto: NuevaInstitucionDTO) -> Institucion:
        """
        Crea una institución nueva.
        Verifica que el nombre no exista antes de insertar.
        """
        if self._repo.existe_nombre(dto.nombre):
            raise ValueError(
                f"Ya existe una institución con el nombre '{dto.nombre}'."
            )
        return self._repo.guardar(dto.to_institucion())


__all__ = [
    "InstitucionService",
    "NuevaInstitucionDTO",
    "InstitucionResumenDTO",
]
