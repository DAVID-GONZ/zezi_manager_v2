"""
src/interface/pages/informes/estadisticos.py
============================================
Página de estadísticos y gráficas analíticas.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.

Flujo:
  1. Filtros: grupo, asignacion, periodo.
  2. Al confirmar → carga datos de EstadisticosService.
  3. Renderiza 3 gráficas ECharts + tabla de ranking.

NOTA IMPORTANTE — R11:
  Todos los option dicts de ECharts están definidos como constantes de módulo
  con prefijo _EC_. NUNCA deben declararse dentro de funciones.
"""
from __future__ import annotations

import copy
import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons, DesempenoColors
from src.interface.design.components.buttons import btn_primary
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("ESTADISTICOS")


# ── Constantes ECharts (R11: módulo-level, prefijo _EC_) ─────────────────────

_EC_PIE_OPTIONS: dict = {
    "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
    "legend": {"orient": "horizontal", "bottom": 0},
    "series": [
        {
            "name": "Desempeño",
            "type": "pie",
            "radius": ["40%", "70%"],
            "avoidLabelOverlap": True,
            "label": {"show": True, "formatter": "{b}: {c}"},
            "data": [],
        }
    ],
}

_EC_LINE_OPTIONS: dict = {
    "tooltip": {"trigger": "axis"},
    "xAxis": {"type": "category", "data": [], "axisLabel": {"rotate": 30}},
    "yAxis": {"type": "value", "min": 0, "max": 100, "name": "Promedio"},
    "series": [
        {
            "name": "Promedio",
            "type": "line",
            "smooth": True,
            "data": [],
            "markLine": {
                "data": [{"type": "average", "name": "Media"}]
            },
        }
    ],
}

_EC_BAR_OPTIONS: dict = {
    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
    "grid": {"left": "25%"},
    "xAxis": {"type": "value", "min": 0, "max": 100, "name": "Promedio"},
    "yAxis": {"type": "category", "data": [], "inverse": True},
    "series": [
        {
            "name": "Promedio",
            "type": "bar",
            "data": [],
            "label": {"show": True, "position": "right", "formatter": "{c}"},
        }
    ],
}


# ── Colores por nivel de desempeño ────────────────────────────────────────────

_NIVEL_COLORES: dict[str, str] = {
    "Bajo":     DesempenoColors.BAJO,
    "Básico":   DesempenoColors.BASICO,
    "Alto":     DesempenoColors.ALTO,
    "Superior": DesempenoColors.SUPERIOR,
}


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "grupo_id":      None,
        "asignacion_id": None,
        "periodo_id":    None,
        "grupos":        [],
        "asignaciones":  [],
        "periodos":      [],
        "datos_listos":  False,
        "dist_desempeno": {},
        "comparativo":   [],
        "ranking":       [],
        "tendencia":     [],
    }


def _cargar_selectores(ctx: SessionContext, _s: dict) -> None:
    try:
        _s["grupos"] = Container.infraestructura_service().listar_grupos()
    except Exception as exc:
        logger.error("Error cargando grupos: %s", exc)
        _s["grupos"] = []

    if _s["grupo_id"]:
        try:
            filtro = FiltroAsignacionesDTO(grupo_id=_s["grupo_id"])
            _s["asignaciones"] = Container.asignacion_service().listar_con_info(filtro)
        except Exception as exc:
            logger.error("Error cargando asignaciones: %s", exc)
            _s["asignaciones"] = []

        try:
            anio_id = ctx.anio_id
            _s["periodos"] = Container.periodo_service().listar_por_anio(anio_id) if anio_id else []
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)
            _s["periodos"] = []
    else:
        _s["asignaciones"] = []
        _s["periodos"] = []


def _cargar_estadisticos(ctx: SessionContext, _s: dict) -> None:
    svc = Container.estadisticos_service()
    gid = _s["grupo_id"]
    aid = _s["asignacion_id"]
    pid = _s["periodo_id"]

    try:
        _s["dist_desempeno"] = svc.distribucion_desempenos(
            grupo_id=gid,
            asignacion_id=aid,
            periodo_id=pid,
            anio_id=ctx.anio_id,
        )
    except Exception as exc:
        logger.error("dist_desempenos: %s", exc)
        _s["dist_desempeno"] = {}

    try:
        _s["comparativo"] = svc.comparativo_periodos(
            grupo_id=gid,
            asignacion_id=aid,
            anio_id=ctx.anio_id,
        )
    except Exception as exc:
        logger.error("comparativo_periodos: %s", exc)
        _s["comparativo"] = []

    try:
        _s["ranking"] = svc.ranking_grupo(grupo_id=gid, periodo_id=pid)
    except Exception as exc:
        logger.error("ranking_grupo: %s", exc)
        _s["ranking"] = []

    try:
        _s["tendencia"] = svc.tendencia_asistencia(
            grupo_id=gid,
            asignacion_id=aid,
            periodo_id=pid,
        )
    except Exception as exc:
        logger.error("tendencia_asistencia: %s", exc)
        _s["tendencia"] = []

    _s["datos_listos"] = True


# ── Página ────────────────────────────────────────────────────────────────────

@ui.page("/informes/estadisticos")
def estadisticos_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _s["grupo_id"] = ctx.grupo_id
    _s["asignacion_id"] = ctx.asignacion_id
    _s["periodo_id"] = ctx.periodo_id
    _cargar_selectores(ctx, _s)

    @ui.refreshable
    def filtros_refreshable() -> None:
        with ui.element("div").classes("andes-card q-mb-md"):
            ui.label("Filtros").classes("text-subtitle1 text-weight-medium q-mb-md")
            with ui.element("div").classes("form-grid-3"):
                grupos_opts = {g.id: getattr(g, "nombre", str(g.id)) for g in _s["grupos"]}
                ui.select(
                    label="Grupo",
                    options=grupos_opts,
                    value=_s["grupo_id"],
                    on_change=lambda e: on_grupo_change(e.value),
                ).classes("w-full")

                asig_opts = {
                    a.asignacion_id: a.asignatura_nombre
                    for a in _s["asignaciones"]
                }
                ui.select(
                    label="Asignación",
                    options=asig_opts,
                    value=_s["asignacion_id"],
                    on_change=lambda e: _s.update({"asignacion_id": e.value}),
                ).classes("w-full")

                per_opts = {p.id: getattr(p, "nombre", str(p.id)) for p in _s["periodos"]}
                ui.select(
                    label="Periodo",
                    options=per_opts,
                    value=_s["periodo_id"],
                    on_change=lambda e: _s.update({"periodo_id": e.value}),
                ).classes("w-full")

            with ui.row().classes("justify-end q-mt-md"):
                btn_primary(
                    "Ver estadísticos",
                    icon=Icons.GRADES,
                    on_click=on_ver,
                )

    @ui.refreshable
    def graficas_refreshable() -> None:
        if not _s["datos_listos"]:
            return

        with ui.element("div").classes("charts-grid"):
            # Gráfica 1 — Distribución de desempeños (pie/donut)
            with ui.element("div").classes("andes-card"):
                ui.label("Distribución de Desempeños").classes("text-subtitle2 text-weight-medium q-mb-sm")
                dist = _s["dist_desempeno"]
                if dist:
                    pie_opts = copy.deepcopy(_EC_PIE_OPTIONS)
                    pie_opts["series"][0]["data"] = [
                        {
                            "name": nivel,
                            "value": cant,
                            "itemStyle": {"color": _NIVEL_COLORES.get(nivel, "#999")},
                        }
                        for nivel, cant in dist.items()
                    ]
                    ui.echart(pie_opts).classes("echart-md")
                else:
                    ui.label("Sin datos de desempeño.").classes("text-caption")

            # Gráfica 2 — Comparativo entre periodos (línea)
            with ui.element("div").classes("andes-card"):
                ui.label("Evolución por Periodos").classes("text-subtitle2 text-weight-medium q-mb-sm")
                comp = _s["comparativo"]
                if comp:
                    line_opts = copy.deepcopy(_EC_LINE_OPTIONS)
                    line_opts["xAxis"]["data"] = [r.get("periodo_nombre", str(r.get("periodo_numero", ""))) for r in comp]
                    line_opts["series"][0]["data"] = [round(r.get("promedio", 0), 1) for r in comp]
                    ui.echart(line_opts).classes("echart-md")
                else:
                    ui.label("Sin datos de comparativo.").classes("text-caption")

            # Gráfica 3 — Ranking del grupo (barras horizontales)
            with ui.element("div").classes("andes-card"):
                ui.label("Ranking del Grupo").classes("text-subtitle2 text-weight-medium q-mb-sm")
                ranking = _s["ranking"]
                if ranking:
                    top = ranking[:15]
                    bar_opts = copy.deepcopy(_EC_BAR_OPTIONS)
                    bar_opts["yAxis"]["data"] = [r.get("nombre_completo", f"#{r.get('posicion','')}") for r in top]
                    bar_opts["series"][0]["data"] = [round(r.get("promedio", 0), 1) for r in top]
                    ui.echart(bar_opts).classes("echart-lg")
                else:
                    ui.label("Sin datos de ranking.").classes("text-caption")

    def on_grupo_change(grupo_id) -> None:
        _s["grupo_id"] = grupo_id
        _s["asignacion_id"] = None
        _s["periodo_id"] = None
        _s["datos_listos"] = False
        _cargar_selectores(ctx, _s)
        filtros_refreshable.refresh()
        graficas_refreshable.refresh()

    def on_ver() -> None:
        if not _s["grupo_id"]:
            ui.notify("Selecciona un grupo.", type="warning")
            return
        if not _s["asignacion_id"]:
            ui.notify("Selecciona una asignación.", type="warning")
            return
        if not _s["periodo_id"]:
            ui.notify("Selecciona un periodo.", type="warning")
            return
        _cargar_estadisticos(ctx, _s)
        graficas_refreshable.refresh()

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            filtros_refreshable()
            graficas_refreshable()

    app_layout(
        titulo_pagina="Estadísticos",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/informes/estadisticos",
        contenido=contenido,
        ctx=ctx,
    )


__all__ = ["estadisticos_page"]
