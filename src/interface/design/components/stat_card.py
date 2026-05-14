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
        El elemento raíz de la tarjeta (ui.card) para poder encadenarlo
        con .style() o .classes() si es necesario.

    Ejemplo:
        stat_card("Total estudiantes", 342, "school", subtitulo="+12 este mes")
        stat_card("Promedio general", "4.1", "bar_chart", variante="success")
        stat_card("Faltas sin justificar", 18, "warning", variante="danger")
    """
    _COLOR_MAP = {
        "primary": "var(--color-primary)",
        "success": "var(--color-success)",
        "warning": "var(--color-warning)",
        "danger":  "var(--color-error)",
        "info":    "var(--color-info)",
    }
    _BG_MAP = {
        "primary": "var(--color-primary-lighter)",
        "success": "#E8F5E9",
        "warning": "#FFF3E0",
        "danger":  "#FFEBEE",
        "info":    "#E1F5FE",
    }

    icono_color = _COLOR_MAP.get(variante, "var(--color-primary)")
    icono_bg    = _BG_MAP.get(variante, "var(--color-primary-lighter)")

    card = ui.card().classes("andes-card").style(
        "min-width:200px;"
        "flex:1;"
        "padding:var(--space-lg);"
    )
    with card:
        with ui.row().classes("items-start justify-between").style("width:100%;margin-bottom:var(--space-md)"):
            # Columna de textos
            with ui.column().classes("gap-1"):
                ui.label(titulo).style(
                    "color:var(--color-text-secondary);"
                    "font-size:var(--font-size-small);"
                    "font-weight:500;"
                    "text-transform:uppercase;"
                    "letter-spacing:0.05em;"
                )
                ui.label(str(valor)).classes("font-h1").style(
                    "color:var(--color-text-primary);"
                    "line-height:1.1;"
                    "margin-top:2px;"
                )
                if subtitulo:
                    ui.label(subtitulo).style(
                        "color:var(--color-text-secondary);"
                        "font-size:var(--font-size-small);"
                        "margin-top:4px;"
                    )

            # Contenedor circular del icono
            with ui.element("div").style(
                f"background:{icono_bg};"
                "border-radius:50%;"
                "width:48px;"
                "height:48px;"
                "display:flex;"
                "align-items:center;"
                "justify-content:center;"
                "flex-shrink:0;"
            ):
                ThemeManager.icono(icono, size=24, color=icono_color)

    return card


__all__ = ["stat_card"]
