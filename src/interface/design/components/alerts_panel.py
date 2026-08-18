"""
alerts_panel.py — Panel de alertas pendientes con resumen y lista.

Componente de presentación puro: recibe lista de AlertItem,
no llama servicios ni Container.
"""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from src.interface.design.components.section_panel import section_panel
from src.interface.design.theme import ThemeManager


@dataclass
class AlertItem:
    """Una alerta para mostrar en el panel."""

    nivel: str
    tipo: str
    descripcion: str = ""


def alerts_panel(
    alertas: list[AlertItem],
    *,
    titulo: str = "Alertas pendientes",
    icono: str = "notifications",
) -> None:
    """Panel de alertas pendientes con conteo por nivel y listado.

    Args:
        alertas: Lista de alertas a mostrar.
        titulo:  Texto del encabezado del panel.
        icono:   Icono del encabezado.
    """
    with section_panel(titulo, icono, color="var(--color-error)"):
        if not alertas:
            with ui.element("div").classes("flex-col items-center"):
                ThemeManager.icono("check_circle", size=36, color="var(--color-success)")
                ui.label("Sin alertas pendientes").classes("success-empty-text")
            return

        criticas = [a for a in alertas if a.nivel.lower() == "critica"]
        advertencias = [a for a in alertas if a.nivel.lower() == "advertencia"]

        if criticas:
            with ui.element("div").classes("alert-summary alert-summary-error"):
                ThemeManager.icono("error", size=18, color="var(--color-error)")
                ui.label(f"{len(criticas)} alerta(s) crítica(s)").classes("alert-count-text")

        if advertencias:
            with ui.element("div").classes("alert-summary alert-summary-warning"):
                ThemeManager.icono("warning", size=18, color="var(--color-warning)")
                ui.label(f"{len(advertencias)} advertencia(s)").classes("alert-count-text")

        _clase_map = {"critica": "alerta-critica", "advertencia": "alerta-advertencia"}
        _icono_map = {"critica": "error", "advertencia": "warning"}
        _color_map = {
            "critica": "var(--color-error)",
            "advertencia": "var(--color-warning)",
        }

        for alerta in alertas[:5]:
            nivel = alerta.nivel.lower()
            clase = _clase_map.get(nivel, "alerta-info")
            icono_n = _icono_map.get(nivel, "info")
            color = _color_map.get(nivel, "var(--color-info)")

            with ui.element("div").classes(f"alerta-item {clase}"):
                ThemeManager.icono(icono_n, size=16, color=color)
                ui.label(alerta.tipo).classes("alerta-item-text")

        if len(alertas) > 5:
            ui.label(f"+ {len(alertas) - 5} más").classes("more-items-text")


__all__ = ["AlertItem", "alerts_panel"]
