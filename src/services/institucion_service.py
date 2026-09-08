"""
InstitucionService
====================
Orquesta los casos de uso del catálogo de instituciones (tenants).

Primer ladrillo multi-tenant (paso_24): listar, crear y resolver la
institución por defecto (#1). No contiene SQL ni lógica de presentación.
"""

from __future__ import annotations

from src.domain.exceptions import ConflictoError, NoEncontradoError
from src.domain.models.institucion import (
    ActualizarInstitucionDTO,
    Institucion,
    InstitucionResumenDTO,
    NuevaInstitucionDTO,
)
from src.domain.ports.institucion_repo import IInstitucionRepository
from src.services.solo_lectura import requiere_escritura


class InstitucionService:
    """
    Orquesta los casos de uso del módulo de Instituciones.
    No contiene SQL. No contiene lógica de presentación.
    """

    def __init__(self, repo: IInstitucionRepository) -> None:
        """Inyecta el repositorio de instituciones."""
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

    def listar_entidades(self, solo_activas: bool = False) -> list[Institucion]:
        """
        Retorna las instituciones completas (mejora_09a). A diferencia de
        `listar()`, no las reduce a `InstitucionResumenDTO`: la usan vistas
        que necesitan campos fuera del resumen (p.ej. municipio o el flag
        `configuracion_inicial_completa` para el badge de estado).
        """
        return self._repo.listar(solo_activas=solo_activas)

    def get(self, institucion_id: int) -> Institucion:
        """Retorna una institución por id. Lanza si no existe."""
        institucion = self._repo.get_by_id(institucion_id)
        if institucion is None:
            raise NoEncontradoError(
                f"La institución con id {institucion_id} no existe.",
                detalles={"recurso": "institucion", "id": institucion_id},
            )
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
    def actualizar(self, institucion_id: int, dto: ActualizarInstitucionDTO) -> Institucion:
        """Actualiza identidad institucional. No altera snapshots históricos de configuracion_anio."""
        inst = self._repo.get_by_id(institucion_id)
        if inst is None:
            raise NoEncontradoError(
                f"La institución con id {institucion_id} no existe.",
                detalles={"recurso": "institucion", "id": institucion_id},
            )
        inst_actualizada = dto.aplicar_a(inst)
        return self._repo.actualizar(inst_actualizada)

    @requiere_escritura
    def marcar_configuracion_inicial_completa(self, institucion_id: int) -> Institucion:
        """
        Marca el tenant como configurado (fin del wizard de mejora_09b).
        Idempotente: si ya estaba en True, no falla.
        """
        inst = self._repo.get_by_id(institucion_id)
        if inst is None:
            raise NoEncontradoError(
                f"La institución con id {institucion_id} no existe.",
                detalles={"recurso": "institucion", "id": institucion_id},
            )
        return self._repo.actualizar(
            inst.model_copy(update={"configuracion_inicial_completa": True})
        )

    @requiere_escritura
    def crear(self, dto: NuevaInstitucionDTO) -> Institucion:
        """
        Crea una institución nueva.
        Verifica que el nombre no exista antes de insertar.
        """
        if self._repo.existe_nombre(dto.nombre):
            raise ConflictoError(f"Ya existe una institución con el nombre '{dto.nombre}'.")
        return self._repo.guardar(dto.to_institucion())


__all__ = [
    "ActualizarInstitucionDTO",
    "Institucion",
    "InstitucionResumenDTO",
    "InstitucionService",
    "NuevaInstitucionDTO",
]
