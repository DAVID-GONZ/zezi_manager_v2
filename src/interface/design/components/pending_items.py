"""
pending_items.py — Lista de ítems pendientes con badges y navegación.

Componente de presentación puro: recibe lista de PendingItem,
no llama servicios ni Container.
"""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from src.interface.design.components.section_panel import section_panel
from src.interface.design.theme import ThemeManager


@dataclass
class PendingItem:
    """Un ítem pendiente con conteo, ruta de navegación e icono."""

    conteo: int
    label: str
    sublabel: str
    ruta: str
    icono: str
    color: str = "var(--color-primary)"


def pending_list(
    items: list[PendingItem],
    *,
    titulo: str = "Pendientes",
    icono: str = "checklist",
) -> None:
    """Lista de ítems pendientes, cada uno navega a su página de resolución.

    Args:
        items:  Lista de pendientes (solo se muestran los que tienen conteo > 0).
        titulo: Texto del encabezado del panel.
        icono:  Icono del encabezado.
    """
    with section_panel(titulo, icono):
        visibles = [item for item in items if item.conteo > 0]

        if not visibles:
            with ui.element("div").classes("flex-col items-center"):
                ThemeManager.icono("check_circle", size=36, color="var(--color-success)")
                ui.label("Sin pendientes").classes("success-empty-text")
            return

        for item in visibles:
            with (
                ui.element("div")
                .classes("hito-item quick-action-card")
                .on("click", lambda r=item.ruta: ui.navigate.to(r))
            ):
                with (
                    ui.element("div")
                    .classes("quick-action-icon")
                    .style(  # DYNAMIC: bg por item
                        "background:var(--color-surface-alt)"
                    )
                ):
                    ThemeManager.icono(item.icono, size=20, color=item.color)
                with ui.element("div").classes("hito-text-col"):
                    ui.label(f"{item.conteo} · {item.label}").classes("hito-desc")
                    ui.label(item.sublabel).classes("hito-date")


__all__ = ["PendingItem", "pending_list"]
