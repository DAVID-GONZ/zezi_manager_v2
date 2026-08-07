"""
InstitucionService
====================
Orquesta los casos de uso del catálogo de instituciones (tenants).

Primer ladrillo multi-tenant (paso_24): listar, crear y resolver la
institución por defecto (#1). No contiene SQL ni lógica de presentación.
"""
from __future__ import annotations

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
    def actualizar(self, institucion_id: int, dto: ActualizarInstitucionDTO) -> Institucion:
        """Actualiza identidad institucional. No altera snapshots históricos de configuracion_anio."""
        inst = self._repo.get_by_id(institucion_id)
        if inst is None:
            raise ValueError(f"La institución con id {institucion_id} no existe.")
        inst_actualizada = dto.aplicar_a(inst)
        return self._repo.actualizar(inst_actualizada)

    def snapshot_institucional(self, institucion_id: int | None) -> dict:
        """
        Retorna dict con campos de identidad mapeados a las claves de ConfiguracionAnio.
        Solo incluye campos con valor no-None. Retorna {} si no hay datos o la institución no existe.
        """
        if institucion_id is None:
            return {}
        inst = self._repo.get_by_id(institucion_id)
        if inst is None:
            return {}
        mapeo = {
            "nombre_institucion":    inst.nombre_oficial or inst.nombre or None,
            "dane_code":             inst.codigo_dane,
            "rector":                inst.rector,
            "direccion":             inst.direccion,
            "municipio":             inst.municipio,
            "telefono_institucion":  inst.telefono,
            "logo_path":             inst.logo_path,
            "resolucion_aprobacion": inst.resolucion_aprobacion,
        }
        return {k: v for k, v in mapeo.items() if v is not None}

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
    "ActualizarInstitucionDTO",
    "InstitucionResumenDTO",
    "InstitucionService",
    "NuevaInstitucionDTO",
]
