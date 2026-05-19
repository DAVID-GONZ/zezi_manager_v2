"""
src/services/infraestructura_service.py
========================================
Fachada sobre IInfraestructuraRepository que expone a la capa de
interfaz las operaciones sobre AreaConocimiento, Asignatura, Grupo,
Horario y Logro sin revelar el repositorio directamente.
"""
from __future__ import annotations

from src.domain.ports.infraestructura_repo import IInfraestructuraRepository
from src.domain.models.infraestructura import (
    AreaConocimiento,
    Asignatura,
    Grupo,
    Horario,
    HorarioEstadisticasDTO,
    HorarioInfo,
    Jornada,
    NuevoHorarioDTO,
    DiaSemana,
)


class InfraestructuraService:

    def __init__(self, repo: IInfraestructuraRepository) -> None:
        self._repo = repo

    # ── Áreas ─────────────────────────────────────────────────────────────────

    def listar_areas(self) -> list[AreaConocimiento]:
        return self._repo.listar_areas()

    def guardar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        return self._repo.guardar_area(area)

    def actualizar_area(self, area: AreaConocimiento) -> AreaConocimiento:
        return self._repo.actualizar_area(area)

    def eliminar_area(self, area_id: int) -> bool:
        return self._repo.eliminar_area(area_id)

    # ── Asignaturas ───────────────────────────────────────────────────────────

    def listar_asignaturas(self, area_id: int | None = None) -> list[Asignatura]:
        return self._repo.listar_asignaturas(area_id=area_id)

    def guardar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        return self._repo.guardar_asignatura(asignatura)

    def actualizar_asignatura(self, asignatura: Asignatura) -> Asignatura:
        return self._repo.actualizar_asignatura(asignatura)

    def eliminar_asignatura(self, asignatura_id: int) -> bool:
        return self._repo.eliminar_asignatura(asignatura_id)

    # ── Grupos ────────────────────────────────────────────────────────────────

    def listar_grupos(self, grado: int | None = None) -> list[Grupo]:
        return self._repo.listar_grupos(grado=grado)

    def guardar_grupo(self, grupo: Grupo) -> Grupo:
        return self._repo.guardar_grupo(grupo)

    def actualizar_grupo(self, grupo: Grupo) -> Grupo:
        return self._repo.actualizar_grupo(grupo)

    def eliminar_grupo(self, grupo_id: int) -> bool:
        return self._repo.eliminar_grupo(grupo_id)

    # ── Horarios ──────────────────────────────────────────────────────────────

    def listar_horario_grupo(
        self, grupo_id: int, periodo_id: int
    ) -> list[HorarioInfo]:
        return self._repo.listar_horario_grupo(grupo_id, periodo_id)

    def listar_horario_docente(
        self, usuario_id: int, periodo_id: int
    ) -> list[HorarioInfo]:
        return self._repo.listar_horario_docente(usuario_id, periodo_id)

    def guardar_horario(self, horario: Horario) -> Horario:
        return self._repo.guardar_horario(horario)

    def eliminar_horario(self, horario_id: int) -> bool:
        return self._repo.eliminar_horario(horario_id)

    def existe_conflicto_horario(
        self,
        usuario_id: int,
        periodo_id: int,
        dia_semana: str,
        hora_inicio: str,
        hora_fin: str,
        excluir_horario_id: int | None = None,
    ) -> bool:
        return self._repo.existe_conflicto_horario(
            usuario_id,
            periodo_id,
            dia_semana,
            hora_inicio,
            hora_fin,
            excluir_horario_id,
        )

    def get_estadisticas(self, periodo_id: int) -> HorarioEstadisticasDTO:
        return self._repo.get_estadisticas(periodo_id)


__all__ = ["InfraestructuraService"]
