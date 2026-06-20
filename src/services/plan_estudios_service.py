"""
PlanEstudiosService — gestión del plan de estudios por grado (paso_19).

Cubre CRUD sobre la tabla plan_estudios y los métodos de consulta de horas
que usan los validadores de PreparacionHorarioService.
"""

from __future__ import annotations

from src.services.solo_lectura import requiere_escritura

from src.domain.models.infraestructura import (
    Grado,
    NuevoPlanEstudiosDTO,
    PlanEstudios,
)
from src.domain.ports.infraestructura_repo import IInfraestructuraRepository


class PlanEstudiosService:

    def __init__(
        self,
        repo: IInfraestructuraRepository,
        asignacion_svc_provider=None,
    ) -> None:
        self._repo = repo
        # Provider lazy (callable que retorna AsignacionService) para evitar la
        # dependencia circular plan↔asignacion en el composition root.
        self._asignacion_svc_provider = asignacion_svc_provider

    # ── Grados ofrecidos ───────────────────────────────────────────────
    def listar_grados(self) -> list[Grado]:
        return self._repo.listar_grados()

    @requiere_escritura
    def guardar_grado(
        self, numero: int, nombre: str | None,
        min_estudiantes: int, max_estudiantes: int, horas_semanales: int,
    ) -> Grado:
        """Crea o actualiza un grado (upsert por número)."""
        grado = Grado(
            numero=numero, nombre=nombre or None,
            min_estudiantes=min_estudiantes, max_estudiantes=max_estudiantes,
            horas_semanales=horas_semanales,
        )
        return self._repo.upsert_grado(grado)

    @requiere_escritura
    def eliminar_grado(self, numero: int) -> bool:
        return self._repo.eliminar_grado(numero)

    def horas_objetivo(self, grado: int) -> int:
        """Total de horas semanales objetivo declarado para el grado (0 si no existe)."""
        g = next((x for x in self._repo.listar_grados() if x.numero == grado), None)
        return g.horas_semanales if g else 0

    # ── Plan de estudios ───────────────────────────────────────────────
    def listar(self) -> list[PlanEstudios]:
        return self._repo.listar_plan_estudios()

    def por_grado(self, grado: int) -> list[PlanEstudios]:
        return self._repo.get_plan_estudios_por_grado(grado)

    def horas_por_grado(self, grado: int) -> int:
        """Total horas semanales declaradas en el plan para ese grado."""
        return sum(p.horas_semanales for p in self.por_grado(grado))

    def horas_de(self, grado: int, asignatura_id: int) -> int:
        """Horas semanales de una asignatura en un grado.

        Usa el plan del grado; si el grado no tiene esa asignatura en su plan,
        cae al `horas_semanales` global de la asignatura (compatibilidad).
        """
        for p in self.por_grado(grado):
            if p.asignatura_id == asignatura_id:
                return p.horas_semanales
        asig = self._repo.get_asignatura(asignatura_id)
        return (asig.horas_semanales or 0) if asig else 0

    def horas_por_grupo(self, grupo) -> int:
        """
        Total horas semanales para un grupo según su grado.
        Si el grado no tiene plan, devuelve 0 (el validador lo reportará).
        """
        if grupo.grado is None:
            return 0
        return self.horas_por_grado(grupo.grado)

    @requiere_escritura
    def actualizar(self, dto: NuevoPlanEstudiosDTO) -> PlanEstudios:
        return self._repo.set_horas_plan(
            dto.grado, dto.asignatura_id, dto.horas_semanales
        )

    @requiere_escritura
    def set_horas(self, grado: int, asignatura_id: int, horas: int) -> PlanEstudios:
        """Upsert a partir de primitivas (la UI no importa DTOs de dominio)."""
        dto = NuevoPlanEstudiosDTO(
            grado=grado, asignatura_id=asignatura_id, horas_semanales=horas
        )
        return self.actualizar(dto)

    @requiere_escritura
    def eliminar(
        self,
        grado: int,
        asignatura_id: int,
        cascade: bool = True,
        usuario_id: int | None = None,
    ) -> tuple[bool, int]:
        """Quita una asignatura del plan de un grado.

        Con cascade=True (default) además desactiva las asignaciones de docentes
        de esa materia en todos los grupos del grado, en una sola operación.

        Retorna (eliminado_del_plan, n_asignaciones_desactivadas).
        """
        eliminado = self._repo.eliminar_plan_estudios(grado, asignatura_id)
        n_desactivadas = 0
        if cascade and self._asignacion_svc_provider is not None:
            asignacion_svc = self._asignacion_svc_provider()
            n_desactivadas = asignacion_svc.desactivar_por_grado_asignatura(
                grado, asignatura_id, usuario_id=usuario_id
            )
        return eliminado, n_desactivadas


__all__ = ["PlanEstudiosService"]
