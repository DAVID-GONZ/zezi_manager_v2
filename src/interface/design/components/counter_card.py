"""
counter_card.py — Tile contador compacto con estado de alerta (convivencia_22).

Pensado para hubs y tableros que muestran conteos con un umbral de alerta
(p.ej. seguimientos abiertos, compromisos vencidos). Más compacto que
`stat_card`: una sola fila icono + valor + etiqueta, con un modificador
`.counter-card--alert` que resalta el tile cuando hay algo que atender.

Reglas del design system:
  - Solo clases del contrato (`.counter-card*`).
  - Colores por variante vía tokens semánticos de tokens.css (NO se redefinen).
  - Icono vía ThemeManager.icono().
"""
from __future__ import annotations

from nicegui import ui

from src.interface.design.theme import ThemeManager

# Variante → color de token semántico para el icono. NO redefine colores:
# reutiliza las variables públicas de tokens.css (misma estrategia que stat_card).
_VARIANTE_ICONO_COLOR: dict[str, str] = {
    "neutral": "var(--color-text-secondary)",
    "primary": "var(--color-primary)",
    "success": "var(--color-success)",
    "warning": "var(--color-warning)",
    "danger":  "var(--color-error)",
    "info":    "var(--color-info)",
}


def counter_card(
    titulo: str,
    valor: str | float | int,
    icono: str,
    *,
    variante: str = "neutral",
    alerta: bool = False,
    subtitulo: str = "",
) -> ui.element:
    """
    Tile contador compacto: icono + valor destacado + etiqueta.

    Args:
        titulo:    Etiqueta de la métrica (ej: "Seguimientos abiertos").
        valor:     Valor principal (ej: 12, "3", "0").
        icono:     Material Symbol Rounded (ej: "flag", "pending_actions").
        variante:  "neutral" | "primary" | "success" | "warning" | "danger" | "info".
                   Mapea a un token semántico existente (no redefine color).
        alerta:    Si True, aplica `.counter-card--alert` (borde + icono de aviso).
        subtitulo: Texto auxiliar opcional bajo el valor.

    Returns:
        El elemento raíz (div.counter-card) para poder encadenar .classes().

    Ejemplo:
        counter_card("Compromisos vencidos", 4, "event_busy",
                     variante="danger", alerta=True)
        counter_card("Seguimientos cerrados", 27, "task_alt", variante="success")
    """
    color_icono = _VARIANTE_ICONO_COLOR.get(variante, _VARIANTE_ICONO_COLOR["neutral"])

    clases = f"counter-card counter-card--{variante}"
    if alerta:
        clases += " counter-card--alert"

    card = ui.element("div").classes(clases)
    with card:
        with ui.element("div").classes("counter-card-icon"):
            ThemeManager.icono(icono, size=20, color=color_icono)
        with ui.element("div").classes("counter-card-body"):
            ui.label(str(valor)).classes("counter-card-value")
            ui.label(titulo).classes("counter-card-label")
            if subtitulo:
                ui.label(subtitulo).classes("counter-card-subtitle")
    return card


__all__ = ["counter_card"]
