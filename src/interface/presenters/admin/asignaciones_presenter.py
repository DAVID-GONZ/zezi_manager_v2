"""Presenter puro de la página de asignaciones (`/admin/asignaciones`).

Sin import de NiceGUI. La lógica de negocio (completitud del plan, carga docente,
cupos) YA vive en `asignacion_service`; aquí solo queda el view-state: perspectiva
(grupo/docente), periodo y elemento seleccionado, y la decisión de qué cargar. El
resto de `estado` son datos ya cargados que la página escribe directamente.
"""
from __future__ import annotations


class AsignacionesPresenter:
    """View-model de asignaciones: selección/perspectiva + dispatch de carga."""

    def __init__(self, perspectiva_inicial: str = "grupo") -> None:
        self.estado: dict = {
            # ── view-state ──
            "perspectiva": perspectiva_inicial,  # "grupo" | "docente"
            "periodo_id": None,
            "grupo_sel_id": None,
            "docente_sel_id": None,
            "solo_con_cupo": True,
            # ── datos cargados (los puebla la página) ──
            "anio_id": None,
            "periodos": [],
            "grupos": [],
            "docentes": [],
            "asignaturas": [],
            "plan": [],
            "asigns": [],
            "doc_asigns": [],
            "mis_asigns": [],
        }

    # ── Transiciones de view-state ──────────────────────────────────────────

    def set_periodo(self, periodo_id) -> None:
        self.estado["periodo_id"] = periodo_id

    def set_perspectiva(self, perspectiva: str) -> None:
        self.estado["perspectiva"] = perspectiva

    def set_grupo_sel(self, grupo_id) -> None:
        self.estado["grupo_sel_id"] = grupo_id

    def set_docente_sel(self, docente_id) -> None:
        self.estado["docente_sel_id"] = docente_id

    def set_solo_con_cupo(self, valor) -> None:
        self.estado["solo_con_cupo"] = bool(valor)

    # ── Decisión de vista ───────────────────────────────────────────────────

    def loader_objetivo(self, es_profesor: bool) -> str:
        """Qué dataset recargar según el rol y la perspectiva activa."""
        if es_profesor:
            return "profesor"
        return "grupo" if self.estado["perspectiva"] == "grupo" else "docente"


__all__ = ["AsignacionesPresenter"]
