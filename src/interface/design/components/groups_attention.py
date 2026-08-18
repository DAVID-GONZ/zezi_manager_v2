"""
groups_attention.py — Panel de grupos que requieren atención (riesgo académico).

Componente de presentación puro: recibe lista de GroupRisk,
no llama servicios ni Container.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nicegui import ui

from src.interface.design.components.section_panel import section_panel
from src.interface.design.theme import ThemeManager


@dataclass
class GroupRisk:
    """Datos de un grupo con estudiantes en riesgo."""

    grupo_id: int
    codigo: str
    en_riesgo: int
    promedio: float
    total: int


def _clase_dias_riesgo(n: int) -> str:
    """Reusa los colores de badge de hitos según severidad del conteo en riesgo."""
    if n >= 5:
        return "hito-dias-danger"
    if n >= 2:
        return "hito-dias-warning"
    return "hito-dias-ok"


def groups_attention_panel(
    grupos: list[GroupRisk],
    *,
    titulo: str = "Grupos que requieren atención",
    on_click: Callable[[int], None] | None = None,
) -> None:
    """Panel de ranking de grupos con más estudiantes en riesgo.

    Args:
        grupos:   Lista de grupos ya filtrados y ordenados.
        titulo:   Texto del encabezado del panel.
        on_click: Callback con grupo_id al hacer click en un grupo.
    """
    with section_panel(titulo, "notifications", color="var(--color-error)"):
        if not grupos:
            with ui.element("div").classes("flex-col items-center"):
                ThemeManager.icono("check_circle", size=36, color="var(--color-success)")
                ui.label("Ningún grupo con estudiantes en riesgo").classes("success-empty-text")
            return

        for g in grupos:
            clase_badge = _clase_dias_riesgo(g.en_riesgo)
            with (
                ui.element("div")
                .classes("hito-item quick-action-card")
                .on(
                    "click",
                    lambda gid=g.grupo_id: (
                        on_click(gid) if on_click else ui.navigate.to("/academico/tablero")
                    ),
                )
            ):
                with ui.element("div").classes(f"hito-dias-badge {clase_badge}"):
                    ui.label(str(g.en_riesgo))
                with ui.element("div").classes("hito-text-col"):
                    ui.label(f"Grupo {g.codigo}").classes("hito-desc")
                    ui.label(f"Promedio {g.promedio:.1f} · {g.total} estudiantes").classes(
                        "hito-date"
                    )


__all__ = ["GroupRisk", "groups_attention_panel"]
