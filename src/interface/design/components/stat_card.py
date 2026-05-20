"""
stat_card.py — Tarjeta de estadística / KPI del design system Andes Minimal.

Ajustes NiceGUI 3.x:
  - Iconos via ThemeManager.icono() (ui.html) en vez de ui.element().text()
  - Contenedores de icono usando context managers con ui.element("div")
    en vez del método .add() que no existe en NiceGUI 3.x.
"""
from __future__ import annotations

from nicegui import ui

from src.interface.design.theme import ThemeManager


def stat_card(
    titulo: str,
    valor: str | int | float,
    icono: str,
    subtitulo: str = "",
    variante: str = "primary",
) -> ui.element:
    """
    Tarjeta de KPI/estadística con icono, valor destacado y título.

    Args:
        titulo:    Etiqueta descriptiva de la métrica (ej: "Total estudiantes").
        valor:     Valor principal a mostrar (ej: 342, "98.5%", "Activo").
        icono:     Nombre del Material Symbol Rounded (ej: "school", "bar_chart").
        subtitulo: Texto auxiliar opcional debajo del valor (ej: "+12 este mes").
        variante:  Color del icono:
                   - "primary"  → azul principal
                   - "success"  → verde
                   - "warning"  → naranja
                   - "danger"   → rojo
                   - "info"     → azul claro

    Returns:
        El elemento raíz de la tarjeta (ui.element div con .stat-card-wrapper)
        para poder encadenarlo con .classes() si es necesario.

    Ejemplo:
        stat_card("Total estudiantes", 342, "school", subtitulo="+12 este mes")
        stat_card("Promedio general", "4.1", "bar_chart", variante="success")
        stat_card("Faltas sin justificar", 18, "warning", variante="danger")
    """
    _ICON_COLORS = {
        "primary": "var(--color-primary)",
        "success": "var(--color-success)",
        "warning": "var(--color-warning)",
        "danger":  "var(--color-error)",
        "info":    "var(--color-info)",
    }
    icono_color = _ICON_COLORS.get(variante, "var(--color-primary)")

    card = ui.element("div").classes(f"stat-card-wrapper {variante}")
    with card:
        with ui.element("div").classes("stat-card-icon-wrap"):
            ThemeManager.icono(icono, size=22, color=icono_color)
        ui.label(titulo).classes("stat-card-label")
        ui.label(str(valor)).classes("stat-card-value")
        if subtitulo:
            ui.label(subtitulo).classes("stat-card-subtitle")
    return card


__all__ = ["stat_card"]
