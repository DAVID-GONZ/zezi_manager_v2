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
# VISTA GLOBAL (directivos) — funciones auxiliares
# ─────────────────────────────────────────────────────────────────────────────

def _cargar_datos_globales(_s: dict) -> None:
    """Carga métricas de todos los grupos para el periodo activo."""
    periodo_id = _s.get("periodo_id")
    anio_id    = _s.get("anio_id")
    if not periodo_id:
        _s.update({"global_data": [], "kpi_grupos": 0, "kpi_promedio": 0.0,
                   "kpi_asistencia": 0.0, "kpi_riesgo": 0})
        return
    try:
        svc    = Container.estadisticos_service()
        grupos = Container.infraestructura_service().listar_grupos()
        filas  = []
        for g in grupos:
            if not g.id:
                continue
            try:
                m = svc.metricas_dashboard(g.id, periodo_id, anio_id)
                if m.total_estudiantes == 0:
                    continue
                filas.append({
                    "grupo_id":   g.id,
                    "codigo":     g.codigo or str(g.id),
                    "total":      m.total_estudiantes,
                    "promedio":   m.promedio_general,
                    "asistencia": m.porcentaje_asistencia,
                    "en_riesgo":  m.estudiantes_en_riesgo,
                })
            except Exception:
                pass
        filas.sort(key=lambda x: x["codigo"])
        _s["global_data"]    = filas
        _s["kpi_grupos"]     = len(filas)
        _s["kpi_promedio"]   = round(sum(f["promedio"] for f in filas) / len(filas), 1) if filas else 0.0
        _s["kpi_asistencia"] = round(sum(f["asistencia"] for f in filas) / len(filas), 1) if filas else 0.0
        _s["kpi_riesgo"]     = sum(f["en_riesgo"] for f in filas)
    except Exception as exc:
        logger.error("Error cargando datos globales: %s", exc)
        _s.update({"global_data": [], "kpi_grupos": 0, "kpi_promedio": 0.0,
                   "kpi_asistencia": 0.0, "kpi_riesgo": 0})


def _cargar_drill_asignaciones(_s: dict) -> None:
    """Carga asignaciones del grupo seleccionado para el drill-down."""
    grupo_id   = _s.get("drill_grupo_id")
    periodo_id = _s.get("periodo_id")
    if not grupo_id or not periodo_id:
        _s["drill_asignaciones"] = []
        return
    try:
        _s["drill_asignaciones"] = Container.asignacion_service().listar_por_grupo(
            grupo_id, periodo_id
        )
    except Exception as exc:
        logger.error("Error cargando asignaciones drill: %s", exc)
        _s["drill_asignaciones"] = []


def _render_global_kpis(_s: dict, nota_minima: float) -> None:
    """4 stat cards institucionales: grupos, promedio, asistencia, riesgo."""
    with ui.element("div").classes("tablero-kpi-row"):
        stat_card(
            titulo    = "Grupos con datos",
            valor     = str(_s["kpi_grupos"]),
            icono     = "groups",
            subtitulo = "en el periodo activo",
            variante  = "info",
        )
        var_p = _kpi_variante(_s["kpi_promedio"], nota_minima, nota_minima + 10)
        stat_card(
            titulo    = "Promedio institucional",
            valor     = f"{_s['kpi_promedio']:.1f}",
            icono     = Icons.GRADES,
            subtitulo = "media de grupos",
            variante  = var_p,
        )
        var_a = _kpi_variante(_s["kpi_asistencia"], 70.0, 80.0)
        stat_card(
            titulo    = "Asistencia global",
            valor     = f"{_s['kpi_asistencia']:.1f}%",
            icono     = Icons.ATTENDANCE,
            subtitulo = "media de grupos",
            variante  = var_a,
        )
        var_r = "error" if _s["kpi_riesgo"] > 0 else "success"
        stat_card(
            titulo    = "En riesgo total",
            valor     = str(_s["kpi_riesgo"]),
            icono     = Icons.WARNING,
            subtitulo = "al menos 1 asignatura",
            variante  = var_r,
        )


def _render_global_comparativo(_s: dict, nota_minima: float) -> None:
    """Bar chart + ag-Grid comparando todos los grupos del periodo."""
    filas = _s.get("global_data", [])
    if not filas:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos de notas en el periodo seleccionado.").classes("tablero-empty-hint")
        return

    # ── Bar chart de promedios ────────────────────────────────────────────
    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono("bar_chart", size=20)
            with ui.element("div"):
                ui.label("Promedio por grupo").classes("panel-title")
                ui.label("Nota definitiva media de todos los estudiantes").classes("tablero-panel-subtitle")

        labels   = [f["codigo"] for f in filas]
        promedios = [f["promedio"] for f in filas]
        colores  = [_ec_color_nota(p, nota_minima) for p in promedios]

        ui.echart({
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"left": "6%", "right": "4%", "top": "8%", "bottom": "10%"},
            "xAxis": {
                "type": "category",
                "data": labels,
                "axisLabel": {"fontSize": 11, "color": _EC_MUTED},
            },
            "yAxis": {"type": "value", "min": 0, "max": 100},
            "series": [{
                "type": "bar",
                "data": [
                    {"value": p, "itemStyle": {"color": c}}
                    for p, c in zip(promedios, colores)
                ],
                "barMaxWidth": 44,
                "label": {
                    "show": True,
                    "position": "top",
                    "fontSize": 11,
                    "formatter": "{c}",
                },
            }],
        }).classes("w-full h-52")

    # ── ag-Grid de grupos ─────────────────────────────────────────────────
    with ui.element("div").classes("panel-card"):
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono(Icons.STUDENTS, size=20)
            ui.label("Resumen por grupo").classes("panel-title")

        prom_cell = (
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
                {"headerName": "Grupo",       "field": "codigo",     "pinned": "left", "width": 110},
                {"headerName": "Estudiantes", "field": "total",      "type": "numericColumn", "width": 130},
                {
                    "headerName": "Promedio",
                    "field": "promedio",
                    "type": "numericColumn",
                    ":valueFormatter": "x => x.value.toFixed(1)",
                    ":cellClass": prom_cell,
                    "width": 120,
                },
                {
                    "headerName": "Asistencia",
                    "field": "asistencia",
                    "type": "numericColumn",
                    ":valueFormatter": "x => x.value.toFixed(1) + '%'",
                    "width": 120,
                },
                {
                    "headerName": "En riesgo",
                    "field": "en_riesgo",
                    "type": "numericColumn",
                    ":cellRenderer": (
                        "params => params.value > 0"
                        " ? '<span class=\"tablero-badge-riesgo\">⚠ ' + params.value + '</span>'"
                        " : '<span class=\"tablero-badge-normal\">✓ 0</span>'"
                    ),
                    "width": 130,
                },
            ],
            "rowData": [
                {
                    "codigo":     f["codigo"],
                    "total":      f["total"],
                    "promedio":   f["promedio"],
                    "asistencia": f["asistencia"],
                    "en_riesgo":  f["en_riesgo"],
                }
                for f in filas
            ],
            "defaultColDef": {"sortable": True, "filter": True, "resizable": True},
            "domLayout": "autoHeight",
            "rowClassRules": {"tablero-row-riesgo": "data.en_riesgo > 0"},
        }).classes("w-full")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

@ui.page("/academico/tablero")
def tablero_estadisticos_page() -> None:
    """
    Tablero estadístico dual — ruta /academico/tablero.

    Directivos (admin / director / coordinador):
      - Sección 1: Vista institucional — métricas de todos los grupos del periodo.
      - Sección 2: Análisis por asignación — drill-down con selectores inline.

    Profesor:
      - Solo la sección de análisis por asignación, usando el contexto del chip
        (periodo + grupo + asignatura completamente seleccionados).
    """
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _ROLES_VALIDOS = {"admin", "director", "coordinador", "profesor"}
    if ctx.usuario_rol not in _ROLES_VALIDOS:
        ui.notify("Acceso no autorizado", type="negative")
        ui.navigate.to("/inicio")
        return

    es_directivo = ctx.usuario_rol in ("admin", "director", "coordinador")

    # ── Estado mutable ─────────────────────────────────────────────────────
    _s: dict = {
        # Contexto académico activo
        "periodo_id":    ctx.periodo_id,
        "anio_id":       ctx.anio_id,
        "grupo_id":      ctx.grupo_id,
        "asignacion_id": ctx.asignacion_id,
        # Vista institucional
        "global_data":    [],
        "kpi_grupos":     0,
        "kpi_promedio":   0.0,
        "kpi_asistencia": 0.0,
        "kpi_riesgo":     0,
        # Drill-down (selectores inline)
        "drill_grupo_id":     ctx.grupo_id,
        "drill_asig_id":      ctx.asignacion_id,
        "drill_asignaciones": [],
    }

    # Carga inicial
    if es_directivo and _s["periodo_id"]:
        _cargar_datos_globales(_s)
    if es_directivo and _s["drill_grupo_id"] and _s["periodo_id"]:
        _cargar_drill_asignaciones(_s)

    # Nota mínima desde config (fallback 60)
    try:
        _cfg = Container.configuracion_service().get_activa()
        _nota_minima: float = _cfg.nota_minima_aprobacion if _cfg else 60.0
    except Exception:
        _nota_minima = 60.0

    # ── Refreshables ───────────────────────────────────────────────────────

    @ui.refreshable
    def global_refreshable() -> None:
        """Vista institucional: KPIs + comparativo de grupos."""
        if not _s["periodo_id"]:
            with ui.element("div").classes("tablero-empty"):
                with ui.element("div").classes("tablero-empty-icon"):
                    ThemeManager.icono("public", size=48)
                ui.label("Selecciona un periodo").classes("panel-title")
                ui.label(
                    "Usa el selector en la barra superior para elegir el periodo activo."
                ).classes("tablero-panel-subtitle")
            return

        if not _s["global_data"]:
            with ui.element("div").classes("tablero-empty"):
                with ui.element("div").classes("tablero-empty-icon"):
                    ThemeManager.icono("bar_chart_off", size=48)
                ui.label("Sin datos institucionales").classes("panel-title")
                ui.label(
                    "Aún no hay notas registradas en ningún grupo para este periodo."
                ).classes("tablero-panel-subtitle")
            return

        _render_global_kpis(_s, _nota_minima)
        _render_global_comparativo(_s, _nota_minima)

    @ui.refreshable
    def drill_refreshable() -> None:
        """Drill-down: selectores inline + tablero detallado por asignación."""
        # ── Selectores ────────────────────────────────────────────────────
        if not _s["periodo_id"]:
            with ui.element("div").classes("tablero-empty"):
                ui.label("Selecciona un periodo para acceder al análisis detallado.").classes("tablero-empty-hint")
            return

        try:
            grupos_lista = Container.infraestructura_service().listar_grupos()
        except Exception:
            grupos_lista = []

        grupos_opts = {g.id: g.codigo for g in grupos_lista if g.id}
        asig_opts   = {
            a.asignacion_id: a.asignatura_nombre
            for a in _s.get("drill_asignaciones", [])
            if a.asignacion_id
        }

        with ui.row().classes("gap-3 items-center flex-wrap q-mb-md"):
            ThemeManager.icono("filter_list", size=18, clases="text-secondary")
            ui.select(
                label   = "Grupo",
                options = grupos_opts,
                value   = _s.get("drill_grupo_id"),
                on_change = lambda e: _on_drill_grupo(e.value),
            ).classes("w-40").props("dense outlined")

            ui.select(
                label   = "Asignatura",
                options = asig_opts,
                value   = _s.get("drill_asig_id"),
                on_change = lambda e: _on_drill_asig(e.value),
            ).classes("w-64").props(
                f"dense outlined {'disable' if not asig_opts else ''}"
            )

        # ── Tablero detallado ─────────────────────────────────────────────
        if not _s.get("drill_grupo_id") or not _s.get("drill_asig_id"):
            with ui.element("div").classes("tablero-empty"):
                with ui.element("div").classes("tablero-empty-icon"):
                    ThemeManager.icono("analytics", size=40)
                ui.label(
                    "Selecciona grupo y asignatura para ver el análisis detallado."
                ).classes("tablero-empty-hint")
            return

        datos = Container.estadisticos_service().datos_tablero(
            asignacion_id = _s["drill_asig_id"],
            periodo_id    = _s["periodo_id"],
            grupo_id      = _s["drill_grupo_id"],
            anio_id       = _s.get("anio_id"),
        )

        if datos.get("vacio") or datos.get("error"):
            with ui.element("div").classes("tablero-empty"):
                with ui.element("div").classes("tablero-empty-icon"):
                    ThemeManager.icono("bar_chart_off", size=40)
                ui.label(
                    datos.get("error") or "Sin datos disponibles para esta asignación."
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

    @ui.refreshable
    def profesor_refreshable() -> None:
        """Tablero por asignación para el rol profesor (contexto completo via chip)."""
        ctx_actual = SessionContext.desde_storage()
        if not ctx_actual or not ctx_actual.contexto_completo:
            with ui.element("div").classes("tablero-empty panel-card"):
                with ui.element("div").classes("tablero-empty-icon"):
                    ThemeManager.icono("analytics", size=48)
                ui.label("Selecciona un contexto académico").classes("panel-title")
                ui.label(
                    "Usa el selector en la barra superior para elegir periodo, "
                    "grupo y asignatura."
                ).classes("tablero-panel-subtitle")
            return

        datos = Container.estadisticos_service().datos_tablero(
            asignacion_id = ctx_actual.asignacion_id,
            periodo_id    = ctx_actual.periodo_id,
            grupo_id      = ctx_actual.grupo_id,
            anio_id       = ctx_actual.anio_id,
        )

        if datos.get("vacio") or datos.get("error"):
            with ui.element("div").classes("tablero-empty panel-card"):
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

    # ── Handlers ────────────────────────────────────────────────────────────

    def _on_drill_grupo(grupo_id: int | None) -> None:
        _s["drill_grupo_id"] = grupo_id
        _s["drill_asig_id"]  = None
        _cargar_drill_asignaciones(_s)
        drill_refreshable.refresh()

    def _on_drill_asig(asig_id: int | None) -> None:
        _s["drill_asig_id"] = asig_id
        drill_refreshable.refresh()

    def on_context_change() -> None:
        nuevo_ctx = SessionContext.desde_storage()
        if nuevo_ctx:
            _s["periodo_id"]    = nuevo_ctx.periodo_id
            _s["anio_id"]       = nuevo_ctx.anio_id
            _s["grupo_id"]      = nuevo_ctx.grupo_id
            _s["asignacion_id"] = nuevo_ctx.asignacion_id
            if es_directivo:
                if _s["periodo_id"]:
                    _cargar_datos_globales(_s)
                if _s["drill_grupo_id"] and _s["periodo_id"]:
                    _cargar_drill_asignaciones(_s)
        if es_directivo:
            global_refreshable.refresh()
            drill_refreshable.refresh()
        else:
            profesor_refreshable.refresh()

    # ── Contenido ────────────────────────────────────────────────────────────

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            if es_directivo:
                # Sección 1: Vista institucional
                with ui.element("div").classes("panel-card"):
                    with ui.element("div").classes("panel-header"):
                        ThemeManager.icono("public", size=20)
                        with ui.element("div"):
                            ui.label("Vista institucional").classes("panel-title")
                            ui.label(
                                "Métricas globales del periodo — todos los grupos"
                            ).classes("tablero-panel-subtitle")
                    global_refreshable()

                # Sección 2: Análisis por asignación
                with ui.element("div").classes("panel-card"):
                    with ui.element("div").classes("panel-header"):
                        ThemeManager.icono("analytics", size=20)
                        with ui.element("div"):
                            ui.label("Análisis por asignación").classes("panel-title")
                            ui.label(
                                "Detalle estadístico de un grupo y materia específicos"
                            ).classes("tablero-panel-subtitle")
                    drill_refreshable()
            else:
                profesor_refreshable()

    app_layout(
        ctx, contenido,
        page_titulo       = "Tablero Estadístico",
        on_context_change = on_context_change,
    )


__all__ = ["tablero_estadisticos_page"]
