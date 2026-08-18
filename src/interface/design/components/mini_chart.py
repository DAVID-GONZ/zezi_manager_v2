"""
mini_chart.py — Gráfica de línea pequeña de evolución (convivencia_22).

Un `ui.echart` compacto tipo `line` para incrustar tendencias breves en hubs
y tarjetas (p.ej. evolución semanal de seguimientos). Legible en claro y oscuro.

Excepción ECharts del design system: ECharts renderiza en <canvas> y NO puede
leer variables CSS ni clases. Sus colores se centralizan aquí en el bloque
`_EC_*`, todos derivados de tokens.py (espejo de :root en tokens.css). Cambiar
un color aquí implica cambiarlo también en tokens.css.
"""

from __future__ import annotations

from nicegui import ui

from src.interface.design.styles.tokens import Colors

# ── PALETA ECHARTS — única excepción al uso de color en Python (ver docstring).
_EC_LINE = Colors.INFO  # --color-info      línea + puntos
_EC_MUTED = Colors.TEXT_SECONDARY  # --color-text-secondary  ejes/etiquetas


def _build_option(
    labels: list[str],
    valores: list[float | None],
    titulo: str,
) -> dict:
    """Construye el diccionario de opciones de ECharts (lógica pura, testeable)."""
    option: dict = {
        "tooltip": {"trigger": "axis"},
        "grid": {
            "left": "6%",
            "right": "4%",
            "top": "22%" if titulo else "10%",
            "bottom": "12%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": labels,
            "boundaryGap": False,
            "axisLabel": {"fontSize": 10, "color": _EC_MUTED},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {"fontSize": 10, "color": _EC_MUTED},
        },
        "series": [
            {
                "type": "line",
                "data": valores,
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"color": _EC_LINE, "width": 2},
                "itemStyle": {"color": _EC_LINE},
                "areaStyle": {"opacity": 0.12, "color": _EC_LINE},
            }
        ],
    }
    if titulo:
        option["title"] = {
            "text": titulo,
            "left": "left",
            "textStyle": {"fontSize": 12, "color": _EC_MUTED},
        }
    return option


def mini_chart(
    labels: list[str],
    valores: list[float | None],
    *,
    titulo: str = "",
    clase: str = "echart-sm",
) -> ui.element:
    """
    Gráfica de línea pequeña de evolución.

    Args:
        labels:  Etiquetas del eje X (ej: ["S1", "S2", "S3"]).
        valores: Valores de la serie (`None` deja un hueco en la línea).
        titulo:  Título opcional sobre la gráfica.
        clase:   Clase CSS de tamaño del contenedor (por defecto "echart-sm").

    Returns:
        El elemento `ui.echart` para poder encadenar clases o estilos.

    Ejemplo:
        mini_chart(["S1", "S2", "S3"], [4, 7, 5], titulo="Seguimientos")
    """
    return ui.echart(_build_option(labels, valores, titulo)).classes(clase)


__all__ = ["mini_chart"]
