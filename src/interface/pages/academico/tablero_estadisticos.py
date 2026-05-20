"""
tablero_estadisticos.py — Tablero estadístico de la asignación
==============================================================
Página: /academico/tablero
Rol mínimo: cualquier usuario autenticado con contexto completo.

Secciones:
  1. KPIs — 4 tarjetas métricas
  2. Gauge del promedio + Donut de distribución por nivel
  3. Análisis por categoría (barras horizontales ponderadas)
  4. Análisis por actividad (bar chart + tabla compacta)
  5. Mapa de calor nota × estudiante × actividad
  6. Tendencia de asistencia semanal
  7. Tabla completa de estudiantes (ag-Grid)

Reglas de estilo:
  - NINGÚN color, tamaño ni propiedad visual en Python.
  - ECharts es la única excepción: no puede leer variables CSS ni clases.
    Sus colores se centralizan en el bloque _EC_* al inicio del módulo,
    todos derivados de tokens.py (que a su vez refleja :root en styles.css).
  - Todo lo demás (ag-Grid, HTML, NiceGUI) usa clases CSS exclusivamente.

Arquitectura de datos:
  - SOLO usa Container.estadisticos_service().datos_tablero().
  - NUNCA importa src.domain.models.*.
  - NUNCA llama repositorios directamente.
"""
from __future__ import annotations

import logging
from nicegui import ui
from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons, Colors, DesempenoColors
from src.interface.design.components import stat_card

logger = logging.getLogger("TABLERO_ESTADISTICOS")

# ─────────────────────────────────────────────────────────────────────────────
# PALETA ECHARTS — única excepción al uso de valores de color en Python.
#
# ECharts renderiza en <canvas> y no puede leer variables CSS ni clases HTML.
# Todos los valores proceden de tokens.py / :root de styles.css.
# Cambiar un color aquí implica cambiarlo también en ambos lugares.
# ─────────────────────────────────────────────────────────────────────────────

_EC_ERROR   = Colors.ERROR            # --color-error      #DC2626
_EC_WARNING = Colors.WARNING          # --color-warning    #D97706
_EC_INFO    = Colors.INFO             # --color-info       #0284C7
_EC_SUCCESS = Colors.SUCCESS          # --color-success    #059669
_EC_MUTED   = Colors.TEXT_SECONDARY   # --color-text-secondary #475569
_EC_GRID    = Colors.DIVIDER          # --color-divider (aprox.) #E2E8F0
_EC_SHADOW  = "rgba(15, 23, 42, 0.12)"   # basado en --shadow-md
_EC_BG_BAR  = "rgba(15, 23, 42, 0.04)"  # relleno sutil de barra de contexto

_EC_NIVEL: dict[str, str] = {
    "Bajo":     DesempenoColors.BAJO,      # --desempeno-bajo
    "Básico":   DesempenoColors.BASICO,    # --desempeno-basico
    "Alto":     DesempenoColors.ALTO,      # --desempeno-alto
    "Superior": DesempenoColors.SUPERIOR,  # --desempeno-superior
}


def _ec_color_nivel(nombre: str) -> str:
    """Color ECharts para un nivel de desempeño. Solo para opciones de gráficos."""
    return _EC_NIVEL.get(nombre, _EC_MUTED)


def _ec_color_nota(nota: float | None, nota_minima: float) -> str:
    """Color ECharts para una nota. Solo para opciones de gráficos."""
    if nota is None or nota == 0:
        return _EC_MUTED
    if nota < nota_minima:
        return _EC_ERROR
    if nota < 70:
        return _EC_WARNING
    if nota < 85:
        return _EC_INFO
    return _EC_SUCCESS


# ─────────────────────────────────────────────────────────────────────────────
# HELPER DE VARIANTE CSS — devuelve un modificador de clase, no un color
# ─────────────────────────────────────────────────────────────────────────────

def _kpi_variante(valor: float, umbral_error: float, umbral_ok: float) -> str:
    """Devuelve 'error', 'warning' o 'success' para componer clases CSS."""
    if valor < umbral_error:
        return "error"
    if valor < umbral_ok:
        return "warning"
    return "success"


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 1 — KPIs
# ─────────────────────────────────────────────────────────────────────────────

def _render_kpis(datos: dict) -> None:
    """4 tarjetas métricas en grid responsive de 4 columnas."""
    nota_minima = datos["nota_minima"]
    prom        = datos["promedio_grupo"]
    asist       = datos["pct_asistencia"]
    riesgo      = datos["en_riesgo_count"]
    total       = datos["total_estudiantes"]
    acts        = datos["actividades_count"]

    with ui.element("div").classes("tablero-kpi-row"):

        var_prom = _kpi_variante(prom, nota_minima, nota_minima + 10)
        stat_card(
            titulo    = "Promedio ponderado",
            valor     = f"{prom:.1f}",
            icono     = Icons.GRADES,
            subtitulo = "ajustado al periodo",
            variante  = var_prom,
        )

        var_asist = _kpi_variante(asist, 70.0, 80.0)
        stat_card(
            titulo    = "Asistencia efectiva",
            valor     = f"{asist:.1f}%",
            icono     = Icons.ATTENDANCE,
            subtitulo = "promedio del grupo",
            variante  = var_asist,
        )

        var_riesgo = "error" if riesgo > 0 else "success"
        stat_card(
            titulo    = "Estudiantes en riesgo",
            valor     = str(riesgo),
            icono     = Icons.WARNING,
            subtitulo = f"bajo {nota_minima:.0f} puntos",
            variante  = var_riesgo,
        )

        stat_card(
            titulo    = "Actividades",
            valor     = str(acts),
            icono     = Icons.SUBJECTS,
            subtitulo = f"para {total} estudiantes",
            variante  = "info",
        )


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 2 — Gauge + Donut
# ─────────────────────────────────────────────────────────────────────────────

def _render_gauge_y_distribucion(datos: dict) -> None:
    """Gauge del promedio (col 40%) y donut de distribución por nivel (col 60%)."""
    nota_minima = datos["nota_minima"]
    prom        = datos["promedio_grupo"]
    dist        = datos["dist_niveles"]

    with ui.element("div").classes("tablero-row-split"):

        # ── Gauge ──────────────────────────────────────────────
        with ui.element("div").classes("tablero-col-40 panel-card"):
            with ui.element("div").classes("panel-header"):
                ThemeManager.icono(Icons.GRADES, size=20)
                ui.label("Promedio del grupo").classes("panel-title")

            ui.echart({
                "series": [{
                    "type": "gauge",
                    "min": 0, "max": 100,
                    "progress": {"show": True, "width": 16},
                    "axisLine": {
                        "lineStyle": {
                            "width": 16,
                            "color": [
                                [nota_minima / 100, _EC_ERROR],
                                [0.70, _EC_WARNING],
                                [0.85, _EC_INFO],
                                [1.00, _EC_SUCCESS],
                            ],
                        }
                    },
                    "pointer":   {"show": True, "length": "65%", "width": 5},
                    "axisTick":  {"show": False},
                    "splitLine": {"show": False},
                    "axisLabel": {"show": False},
                    "detail": {
                        "valueAnimation": True,
                        "formatter":      "{value}",
                        "fontSize":       30,
                        "fontWeight":     "bold",
                        "offsetCenter":   [0, "72%"],
                    },
                    "title": {
                        "offsetCenter": [0, "90%"],
                        "fontSize":     11,
                        "color":        _EC_MUTED,
                    },
                    "data": [{"value": prom, "name": "Promedio"}],
                }],
            }).classes("w-full h-56")

        # ── Donut ──────────────────────────────────────────────
        with ui.element("div").classes("tablero-col-60 panel-card"):
            with ui.element("div").classes("panel-header"):
                ThemeManager.icono(Icons.DASHBOARD, size=20)
                with ui.element("div"):
                    ui.label("Distribución por nivel").classes("panel-title")
                    ui.label("Estudiantes clasificados por desempeño").classes(
                        "tablero-panel-subtitle"
                    )

            donut_data = [
                {
                    "name":      nivel,
                    "value":     count,
                    "itemStyle": {"color": _ec_color_nivel(nivel)},
                }
                for nivel, count in dist.items()
                if count > 0
            ]

            if not donut_data:
                with ui.element("div").classes("tablero-empty"):
                    ui.label("Sin datos de distribución.").classes("tablero-empty-hint")
            else:
                ui.echart({
                    "tooltip": {
                        "trigger":   "item",
                        "formatter": "{b}: {c} alumnos ({d}%)",
                    },
                    "legend": {
                        "orient":    "vertical",
                        "right":     "5%",
                        "top":       "middle",
                        "textStyle": {"fontSize": 12, "color": _EC_MUTED},
                    },
                    "series": [{
                        "type":      "pie",
                        "radius":    ["38%", "68%"],
                        "center":    ["42%", "50%"],
                        "data":      donut_data,
                        "label":     {"show": False},
                        "labelLine": {"show": False},
                        "emphasis": {
                            "label": {
                                "show":       True,
                                "fontSize":   13,
                                "fontWeight": "bold",
                            },
                            "itemStyle": {
                                "shadowBlur":  10,
                                "shadowColor": _EC_SHADOW,
                            },
                        },
                    }],
                }).classes("w-full h-56")


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3 — Análisis por categoría
# ─────────────────────────────────────────────────────────────────────────────

def _render_categorias(datos: dict) -> None:
    """Barras horizontales ponderadas por categoría evaluativa."""
    cats        = datos["analisis_categorias"]
    nota_minima = datos["nota_minima"]

    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono("layers", size=20)
            with ui.element("div"):
                ui.label("Análisis por categoría").classes("panel-title")
                ui.label(
                    "Promedio del grupo ponderado por el peso de cada categoría"
                ).classes("tablero-panel-subtitle")

        if not cats:
            with ui.element("div").classes("tablero-empty"):
                ui.label("Sin categorías evaluativas definidas.").classes("tablero-empty-hint")
            return

        cat_labels   = [f"{c['nombre']} ({c['peso_pct']}%)" for c in cats]
        cat_bar_data = [
            {
                "value":     c["promedio"] if c["promedio"] is not None else 0,
                "itemStyle": {"color": _ec_color_nota(c["promedio"], nota_minima)},
            }
            for c in cats
        ]

        chart_h = max(120, len(cats) * 46)  # DYNAMIC: escala con nº de categorías

        ui.echart({
            "tooltip": {"trigger": "axis"},
            "grid": {
                "left": "38%", "right": "12%",
                "top": "4%",   "bottom": "4%",
                "containLabel": False,
            },
            "xAxis": {
                "type": "value",
                "max":  100,
                "axisLabel": {"fontSize": 10},
                "splitLine": {"lineStyle": {"color": _EC_GRID}},
            },
            "yAxis": {
                "type": "category",
                "data": cat_labels,
                "axisLabel": {"fontSize": 11, "color": _EC_MUTED},
            },
            "series": [
                {
                    "type":       "bar",
                    "data":       cat_bar_data,
                    "barMaxWidth": 26,
                    "z":           2,
                    "label": {
                        "show":      True,
                        "position":  "right",
                        "formatter": "{c}",
                        "fontSize":  11,
                    },
                },
                {
                    "type":       "bar",
                    "data":       [100] * len(cats),
                    "itemStyle":  {"color": _EC_BG_BAR},
                    "barGap":     "-100%",
                    "barMaxWidth": 26,
                    "z":          1,
                    "label":      {"show": False},
                    "tooltip":    {"show": False},
                },
            ],
        }).classes("w-full").style(f"height: {chart_h}px")  # DYNAMIC


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 4 — Análisis por actividad
# ─────────────────────────────────────────────────────────────────────────────

def _render_actividades(datos: dict) -> None:
    """Bar chart (col 60%) + tabla compacta de las más difíciles (col 40%)."""
    acts        = datos["analisis_actividades"]
    nota_minima = datos["nota_minima"]

    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono(Icons.SUBJECTS, size=20)
            with ui.element("div"):
                ui.label("Análisis por actividad").classes("panel-title")
                ui.label(
                    "Promedio del grupo · las actividades con menor promedio "
                    "aparecen primero en la tabla"
                ).classes("tablero-panel-subtitle")

        if not acts:
            with ui.element("div").classes("tablero-empty"):
                ui.label("Sin actividades evaluativas registradas.").classes(
                    "tablero-empty-hint"
                )
            return

        with ui.element("div").classes("tablero-row-split"):

            # ── Bar chart — col 60% ───────────────────────────────
            with ui.element("div").classes("tablero-col-60"):
                bar_data = [
                    {
                        "value":     a["promedio"] if a["promedio"] is not None else 0,
                        "itemStyle": {"color": _ec_color_nota(a["promedio"], nota_minima)},
                    }
                    for a in acts
                ]
                act_labels = [a["nombre"] for a in acts]

                ui.echart({
                    "tooltip": {
                        "trigger":     "axis",
                        "axisPointer": {"type": "shadow"},
                    },
                    "grid": {
                        "left": "4%", "right": "4%",
                        "bottom": "30%", "top": "6%",
                    },
                    "xAxis": {
                        "type": "category",
                        "data": act_labels,
                        "axisLabel": {
                            "rotate":   40,
                            "fontSize": 10,
                            "color":    _EC_MUTED,
                        },
                    },
                    "yAxis": {"type": "value", "min": 0, "max": 100},
                    "series": [{
                        "type":       "bar",
                        "data":       bar_data,
                        "barMaxWidth": 32,
                        "label": {
                            "show":      True,
                            "position":  "top",
                            "fontSize":  9,
                            "formatter": "{c}",
                        },
                    }],
                }).classes("w-full h-52")

            # ── Tabla compacta — col 40% ──────────────────────────
            with ui.element("div").classes("tablero-col-40"):
                sorted_acts = sorted(
                    [a for a in acts if a["promedio"] is not None],
                    key=lambda a: a["promedio"],
                )[:15]

                rows_html = "".join(
                    (
                        '<tr class="tablero-act-row-riesgo">'
                        f'<td class="tablero-act-riesgo">{a["nombre"]}</td>'
                        f"<td>{a['categoria'][:10]}</td>"
                        f'<td class="tablero-act-riesgo">{a["promedio"]:.1f}</td>'
                        f"<td>{a['entregadas']}/{a['total']}</td>"
                        "</tr>"
                    )
                    if (a["promedio"] or 0) < nota_minima
                    else (
                        "<tr>"
                        f"<td>{a['nombre']}</td>"
                        f"<td>{a['categoria'][:10]}</td>"
                        f"<td>{a['promedio']:.1f}</td>"
                        f"<td>{a['entregadas']}/{a['total']}</td>"
                        "</tr>"
                    )
                    for a in sorted_acts
                )
                ui.html(
                    f'<table class="tablero-act-table">'
                    f"<thead><tr>"
                    f"<th>Actividad</th><th>Cat.</th><th>Prom.</th><th>Entr.</th>"
                    f"</tr></thead>"
                    f"<tbody>{rows_html}</tbody>"
                    f"</table>"
                )


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 5 — Mapa de calor
# ─────────────────────────────────────────────────────────────────────────────

def _render_heatmap(datos: dict) -> None:
    """Heatmap filas=estudiantes × columnas=actividades con nota como valor."""
    heatmap_data = datos["heatmap_data"]
    act_names    = datos["heatmap_actos"]
    est_names    = datos["heatmap_ests"]
    n_est        = len(est_names)
    n_act        = len(act_names)

    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono("grid_on", size=20)
            with ui.element("div"):
                ui.label("Mapa de calor — notas individuales").classes("panel-title")
                ui.label(
                    f"{n_est} estudiantes · {n_act} actividades — "
                    "ordenados por promedio ascendente"
                ).classes("tablero-panel-subtitle")

        if not heatmap_data:
            with ui.element("div").classes("tablero-empty"):
                with ui.element("div").classes("tablero-empty-icon"):
                    ThemeManager.icono("grid_off", size=40)
                ui.label(
                    "Sin notas registradas para mostrar el mapa de calor."
                ).classes("tablero-empty-hint")
            return

        chart_h = max(260, n_est * 26)  # DYNAMIC: 26px por fila de estudiante

        def _chart() -> None:
            with ui.element("div").classes("tablero-heatmap-wrap"):
                ui.echart({
                    "tooltip": {
                        "position":  "top",
                        "formatter": (
                            "params => params.value"
                            " ? (params.value[2] + '/100')"
                            " : 'Sin nota'"
                        ),
                    },
                    "grid": {
                        "left": "22%", "right": "3%",
                        "bottom": "20%", "top": "3%",
                    },
                    "xAxis": {
                        "type": "category",
                        "data": act_names,
                        "axisLabel": {
                            "rotate":   40,
                            "fontSize": 9,
                            "color":    _EC_MUTED,
                        },
                        "splitArea": {"show": True},
                    },
                    "yAxis": {
                        "type": "category",
                        "data": est_names,
                        "axisLabel": {"fontSize": 10, "color": _EC_MUTED},
                        "splitArea": {"show": True},
                    },
                    "visualMap": {
                        "min":         0,
                        "max":         100,
                        "calculable":  True,
                        "orient":      "horizontal",
                        "left":        "center",
                        "bottom":      0,
                        "inRange": {
                            "color": [
                                _EC_ERROR, _EC_WARNING, _EC_INFO, _EC_SUCCESS,
                            ],
                        },
                    },
                    "series": [{
                        "type":  "heatmap",
                        "data":  heatmap_data,
                        "label": {"show": True, "fontSize": 9},
                        "emphasis": {
                            "itemStyle": {
                                "shadowBlur":  8,
                                "shadowColor": _EC_SHADOW,
                            },
                        },
                    }],
                }).classes("w-full").style(f"height: {chart_h}px")  # DYNAMIC

        if n_est > 20:
            with ui.expansion(
                f"Ver mapa de calor completo ({n_est} estudiantes)",
                icon=Icons.EXPAND,
            ).classes("w-full"):
                _chart()
        else:
            _chart()


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 6 — Tendencia de asistencia
# ─────────────────────────────────────────────────────────────────────────────

def _render_tendencia_asistencia(datos: dict) -> None:
    """Line chart con evolución semanal de asistencia y marcador de umbral."""
    tendencia = datos["tendencia_asistencia"]

    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono(Icons.ATTENDANCE, size=20)
            with ui.element("div"):
                ui.label("Tendencia de asistencia").classes("panel-title")
                ui.label(
                    "Evolución semanal del porcentaje de asistencia efectiva del grupo"
                ).classes("tablero-panel-subtitle")

        if len(tendencia) < 2:
            with ui.element("div").classes("tablero-empty"):
                ui.label(
                    "Datos insuficientes para mostrar la tendencia."
                ).classes("tablero-empty-hint")
                ui.label(
                    "El tablero se actualiza con cada registro de asistencia."
                ).classes("tablero-empty-hint")
            return

        semanas = [t["semana"] for t in tendencia]
        valores = [t["pct"]    for t in tendencia]

        ui.echart({
            "tooltip": {"trigger": "axis", "formatter": "{b}: {c}%"},
            "grid": {
                "left": "8%", "right": "4%",
                "bottom": "10%", "top": "18%",
            },
            "xAxis": {
                "type": "category",
                "data": semanas,
                "axisLabel": {"fontSize": 11, "color": _EC_MUTED},
                "boundaryGap": False,
            },
            "yAxis": {
                "type": "value",
                "min":  0,
                "max":  100,
                "axisLabel": {"formatter": "{value}%", "fontSize": 10},
            },
            "series": [{
                "type":       "line",
                "data":       valores,
                "smooth":     True,
                "areaStyle":  {"opacity": 0.15, "color": _EC_INFO},
                "lineStyle":  {"color": _EC_INFO, "width": 2},
                "itemStyle":  {"color": _EC_INFO},
                "markLine": {
                    "silent":  True,
                    "symbol":  ["none", "none"],
                    "data":    [{"yAxis": 70, "name": "Umbral 70%"}],
                    "lineStyle": {
                        "color": _EC_WARNING,
                        "type":  "dashed",
                        "width": 1.5,
                    },
                    "label": {
                        "formatter": "Umbral 70%",
                        "position":  "insideEndTop",
                        "color":     _EC_WARNING,
                        "fontSize":  10,
                    },
                },
            }],
        }).classes("w-full h-48")


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 7 — Tabla de estudiantes (ag-Grid)
# ─────────────────────────────────────────────────────────────────────────────

def _render_tabla_estudiantes(datos: dict) -> None:
    """ag-Grid completo: promedio, nivel, asistencia y estado de riesgo."""
    rows        = datos["tabla_estudiantes"]
    nota_minima = datos["nota_minima"]

    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono(Icons.STUDENTS, size=20)
            with ui.element("div"):
                ui.label("Tabla de estudiantes").classes("panel-title")
                ui.label(
                    "Ordenada por promedio ascendente — "
                    "los estudiantes en riesgo aparecen primero"
                ).classes("tablero-panel-subtitle")

        if not rows:
            with ui.element("div").classes("tablero-empty"):
                ui.label("Sin estudiantes en este grupo.").classes("tablero-empty-hint")
            return

        # cellClass devuelve una clase CSS según el valor numérico.
        # nota_minima se embebe como número (no como color).
        promedio_cell_class = (
            f"params => {{"
            f" const v = params.value, m = {nota_minima};"
            f" if (v >= 85) return 'tablero-promedio-superior';"
            f" if (v >= 70) return 'tablero-promedio-alto';"
            f" if (v >= m)  return 'tablero-promedio-basico';"
            f" return 'tablero-promedio-riesgo';"
            f"}}"
        )

        ui.aggrid({
            "columnDefs": [
                {
                    "headerName": "Estudiante",
                    "field":      "nombre",
                    "pinned":     "left",
                    "minWidth":   180,
                    "flex":       2,
                },
                {
                    "headerName":     "Promedio",
                    "field":          "promedio",
                    "type":           "numericColumn",
                    ":valueFormatter": "x => x.value != null ? x.value.toFixed(1) + '/100' : '—'",
                    ":cellClass":      promedio_cell_class,
                    "width":          140,
                },
                {
                    "headerName": "Nivel",
                    "field":      "nivel",
                    "width":      110,
                },
                {
                    "headerName":     "Asistencia",
                    "field":          "asistencia_pct",
                    "type":           "numericColumn",
                    ":valueFormatter": "x => x.value != null ? x.value.toFixed(1) + '%' : '—'",
                    "width":          120,
                },
                {
                    "headerName": "Estado",
                    "field":      "en_riesgo",
                    ":cellRenderer": (
                        "params => params.value"
                        " ? '<span class=\"tablero-badge-riesgo\">⚠ Riesgo</span>'"
                        " : '<span class=\"tablero-badge-normal\">✓ Normal</span>'"
                    ),
                    "width": 110,
                },
            ],
            "rowData": rows,
            "defaultColDef": {
                "sortable":  True,
                "filter":    True,
                "resizable": True,
            },
            "domLayout": "autoHeight",
            "rowClassRules": {
                "tablero-row-riesgo": "data.en_riesgo === true",
            },
        }).classes("w-full")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

@ui.page("/academico/tablero")
def tablero_estadisticos_page() -> None:
    """Tablero estadístico de la asignación — ruta /academico/tablero."""
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    # ── Sin contexto académico completo ───────────────────────────────────
    if not ctx.contexto_completo:
        def _contenido_vacio() -> None:
            with ui.element("div").classes("tablero-empty panel-card"):
                with ui.element("div").classes("tablero-empty-icon"):
                    ThemeManager.icono("analytics", size=48)
                ui.label("Selecciona un contexto académico").classes("panel-title")
                ui.label(
                    "Usa el selector en la barra superior para elegir periodo, "
                    "grupo y asignatura antes de ver el tablero."
                ).classes("tablero-panel-subtitle")

        app_layout(
            "Tablero Estadístico",
            ctx.usuario_nombre,
            ctx.usuario_rol,
            "/academico/tablero",
            _contenido_vacio,
            ctx=ctx,
        )
        return

    # ── Contenido principal ───────────────────────────────────────────────
    @ui.refreshable
    def _tablero_refreshable() -> None:
        ctx_actual = SessionContext.desde_storage()
        if not ctx_actual or not ctx_actual.contexto_completo:
            with ui.element("div").classes("tablero-empty"):
                ui.label(
                    "Contexto incompleto — selecciona periodo, grupo y asignatura."
                ).classes("tablero-empty-hint")
            return

        datos = Container.estadisticos_service().datos_tablero(
            asignacion_id = ctx_actual.asignacion_id,
            periodo_id    = ctx_actual.periodo_id,
            grupo_id      = ctx_actual.grupo_id,
            anio_id       = ctx_actual.anio_id,
        )

        if datos.get("vacio") or datos.get("error"):
            with ui.element("div").classes("tablero-empty"):
                with ui.element("div").classes("tablero-empty-icon"):
                    ThemeManager.icono("bar_chart_off", size=40)
                ui.label(
                    datos.get("error") or "Sin datos disponibles para este contexto."
                ).classes("tablero-empty-hint")
            return

        with ui.element("div").classes("page-stack"):
            _render_kpis(datos)
            _render_gauge_y_distribucion(datos)
            _render_categorias(datos)
            _render_actividades(datos)
            _render_heatmap(datos)
            _render_tendencia_asistencia(datos)
            _render_tabla_estudiantes(datos)

    def _contenido() -> None:
        _tablero_refreshable()

    app_layout(
        titulo_pagina     = "Tablero Estadístico",
        usuario_nombre    = ctx.usuario_nombre,
        usuario_rol       = ctx.usuario_rol,
        ruta_activa       = "/academico/tablero",
        contenido         = _contenido,
        ctx               = ctx,
        on_context_change = lambda: _tablero_refreshable.refresh(),
    )


__all__ = ["tablero_estadisticos_page"]
