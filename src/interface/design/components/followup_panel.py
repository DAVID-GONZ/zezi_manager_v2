"""
followup_panel.py — Panel de seguimientos pendientes con acción de resolver.

Componente de presentación puro: recibe lista de FollowupItem y un callback,
no llama servicios ni Container.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nicegui import ui

from src.interface.design.components.buttons import btn_secondary
from src.interface.design.components.section_panel import section_panel
from src.interface.design.theme import ThemeManager


@dataclass
class FollowupItem:
    """Un seguimiento pendiente."""

    id: int
    descripcion: str
    nivel: str
    fecha: str


def followup_panel(
    items: list[FollowupItem],
    *,
    on_resolve: Callable[[int], None] | None = None,
    titulo: str = "Seguimientos pendientes",
) -> None:
    """Panel de seguimientos pendientes con botón de resolución.

    No renderiza nada si la lista está vacía.

    Args:
        items:      Lista de seguimientos.
        on_resolve: Callback con el id del seguimiento al marcar como atendido.
        titulo:     Texto del encabezado del panel.
    """
    if not items:
        return

    _nivel_color = {
        "critica": "var(--color-error)",
        "advertencia": "var(--color-warning)",
        "info": "var(--color-info)",
    }
    _nivel_icono = {
        "critica": "error",
        "advertencia": "warning",
        "info": "info",
    }

    with section_panel(f"{titulo} ({len(items)})", "notifications", color="var(--color-warning)"):
        for item in items:
            nivel = item.nivel.lower()
            color = _nivel_color.get(nivel, "var(--color-info)")
            icono = _nivel_icono.get(nivel, "info")

            with ui.element("div").classes("hito-item"):
                ThemeManager.icono(icono, size=16, color=color)
                with ui.element("div").classes("hito-text-col flex-1"):
                    ui.label(item.descripcion[:80]).classes("hito-desc")
                    ui.label(f"{item.fecha} · nivel: {nivel}").classes("hito-date")
                if on_resolve:
                    btn_secondary(
                        "Marcar como atendido",
                        on_click=lambda aid=item.id: on_resolve(aid),
                    )


__all__ = ["FollowupItem", "followup_panel"]
