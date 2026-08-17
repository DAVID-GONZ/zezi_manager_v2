"""
milestones_panel.py — Panel de hitos/fechas próximas.

Componente de presentación puro: recibe lista de MilestoneItem,
no llama servicios ni Container.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from nicegui import ui

from src.interface.design.components.section_panel import section_panel


@dataclass
class MilestoneItem:
    """Un hito o fecha próxima."""
    descripcion: str
    fecha_limite: date | None


def _clase_dias(dias: int) -> str:
    if dias > 14:
        return "hito-dias-ok"
    if dias > 5:
        return "hito-dias-warning"
    return "hito-dias-danger"


def milestones_panel(
    hitos: list[MilestoneItem],
    *,
    titulo: str = "Próximas fechas",
    icono: str = "event",
) -> None:
    """Panel de hitos próximos con badges de días restantes.

    Args:
        hitos:  Lista de hitos a mostrar.
        titulo: Texto del encabezado del panel.
        icono:  Icono del encabezado.
    """
    with section_panel(titulo, icono):
        if not hitos:
            ui.label("Sin hitos próximos").classes("empty-state")
            return

        hoy = date.today()
        for hito in hitos[:6]:
            dias_txt = "—"
            clase_dias = "hito-dias-ok"

            if hito.fecha_limite:
                dias = (hito.fecha_limite - hoy).days
                clase_dias = _clase_dias(dias)
                dias_txt = f"{dias}d" if dias > 0 else "HOY"

            with ui.element("div").classes("hito-item"):
                with ui.element("div").classes(f"hito-dias-badge {clase_dias}"):
                    ui.label(dias_txt)
                with ui.element("div").classes("hito-text-col"):
                    ui.label(str(hito.descripcion)[:45]).classes("hito-desc")
                    if hito.fecha_limite:
                        ui.label(hito.fecha_limite.strftime("%d %b %Y")).classes("hito-date")


__all__ = ["MilestoneItem", "milestones_panel"]
