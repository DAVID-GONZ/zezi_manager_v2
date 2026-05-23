"""
src/interface/pages/informes/estadisticos.py
============================================
Centro unificado de generación de informes exportables.

Arquitectura:
  - Panel de configuración: Tipo de Informe + selectores dinámicos + btn Previsualizar
  - Panel de preview:        tabla ag-Grid o gráfica ECharts según el tipo
  - Panel de exportación:    Excel siempre; PDF solo si el tipo lo admite

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.* salvo DTOs
  (InformeNotasDTO, InformeAsistenciaDTO, FormatoInforme).

NOTA IMPORTANTE — R11:
  Todos los option dicts de ECharts están definidos como constantes de módulo
  con prefijo _EC_. NUNCA deben declararse dentro de funciones.
"""
from __future__ import annotations

import copy
import logging
from datetime import date

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons, DesempenoColors, AsistenciaColors
from src.interface.design.components.buttons import btn_primary, btn_secondary
from src.services.asignacion_service import FiltroAsignacionesDTO
from src.interface.design.components.stat_card import stat_card
from src.domain.models.dtos import FormatoInforme
from src.services.informe_service import sanitizar_datos_exportacion

logger = logging.getLogger("ESTADISTICOS")


# ── Catálogo de tipos de informe ─────────────────────────────────────────────

_TIPOS_INFORME: list[dict] = [
    {
        "id":      "consolidado_notas",
        "label":   "Consolidado de Notas",
        "filtros": ["grupo", "periodo"],
        "preview": "aggrid",
        "pdf":     True,
    },
    {
        "id":      "consolidado_asistencia",
        "label":   "Consolidado de Asistencia",
        "filtros": ["grupo", "periodo"],
        "preview": "aggrid",
        "pdf":     True,
    },
    {
        "id":      "ranking_grupo",
        "label":   "Ranking del Grupo",
        "filtros": ["grupo", "periodo"],
        "preview": "aggrid",
        "pdf":     True,
    },
    {
        "id":      "distribucion_desempenos",
        "label":   "Distribución de Desempeños",
        "filtros": ["grupo", "asignatura", "periodo"],
        "preview": "donut",
        "pdf":     True,
    },
    {
        "id":      "comparativo_periodos",
        "label":   "Comparativo por Periodos",
        "filtros": ["grupo", "asignatura"],
        "preview": "linea",
        "pdf":     True,
    },
    {
        "id":      "promedios_area",
        "label":   "Promedios por Área",
        "filtros": ["grupo", "periodo"],
        "preview": "barras",
        "pdf":     True,
    },
    {
        "id":      "tendencia_asistencia",
        "label":   "Tendencia de Asistencia",
        "filtros": ["grupo", "asignatura", "periodo"],
        "preview": "linea",
        "pdf":     True,
    },
    {
        "id":      "estados_asistencia",
        "label":   "Estados de Asistencia",
        "filtros": ["grupo", "asignatura", "periodo"],
        "preview": "pie",
        "pdf":     True,
    },
    {
        "id":      "consolidado_anual",
        "label":   "Consolidado Anual",
        "filtros": ["grupo"],
        "preview": "aggrid",
        "pdf":     True,
    },
]

_TIPOS_MAP: dict[str, dict] = {t["id"]: t for t in _TIPOS_INFORME}
_TIPOS_SELECT_OPTS: dict[str, str] = {t["id"]: t["label"] for t in _TIPOS_INFORME}


# ── Colores ECharts ───────────────────────────────────────────────────────────

_NIVEL_COLORES: dict[str, str] = {
    "Bajo":     DesempenoColors.BAJO,
    "Básico":   DesempenoColors.BASICO,
    "Alto":     DesempenoColors.ALTO,
    "Superior": DesempenoColors.SUPERIOR,
}

_ASISTENCIA_COLORES: dict[str, str] = {
    "P":  AsistenciaColors.PRESENTE,
    "FJ": AsistenciaColors.FJ,
    "FI": AsistenciaColors.FI,
    "R":  AsistenciaColors.RETRASO,
    "E":  AsistenciaColors.EXCUSA,
}


# ── Constantes ECharts (R11: módulo-level, prefijo _EC_) ─────────────────────

_EC_DONUT_OPTIONS: dict = {
    "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
    "legend":  {"orient": "horizontal", "bottom": 0},
    "series": [
        {
            "name":              "Desempeño",
            "type":              "pie",
            "radius":            ["40%", "70%"],
            "avoidLabelOverlap": True,
            "label":             {"show": True, "formatter": "{b}: {c}"},
            "data":              [],
        }
    ],
}

_EC_LINE_OPTIONS: dict = {
    "tooltip": {"trigger": "axis"},
    "xAxis":   {"type": "category", "data": [], "axisLabel": {"rotate": 30}},
    "yAxis":   {"type": "value", "min": 0, "max": 100, "name": "Promedio"},
    "series": [
        {
            "name":   "Promedio",
            "type":   "line",
            "smooth": True,
            "data":   [],
        }
    ],
}

_EC_LINE_ASISTENCIA_OPTIONS: dict = {
    "tooltip": {"trigger": "axis"},
    "xAxis":   {"type": "category", "data": [], "axisLabel": {"rotate": 30}},
    "yAxis":   {"type": "value", "min": 0, "max": 100, "name": "% Asistencia"},
    "series": [
        {
            "name":   "% Asistencia",
            "type":   "line",
            "smooth": True,
            "data":   [],
            "markLine": {
                "data": [{"yAxis": 70, "name": "Mínimo (70%)"}],
                "lineStyle": {"color": DesempenoColors.BAJO, "type": "dashed"},
            },
        }
    ],
}

_EC_BAR_OPTIONS: dict = {
    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
    "grid":    {"left": "25%"},
    "xAxis":   {"type": "value", "min": 0, "max": 100, "name": "Promedio"},
    "yAxis":   {"type": "category", "data": [], "inverse": True},
    "series": [
        {
            "name":  "Promedio",
            "type":  "bar",
            "data":  [],
            "label": {"show": True, "position": "right", "formatter": "{c}"},
        }
    ],
}

_EC_PIE_OPTIONS: dict = {
    "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
    "legend":  {"orient": "horizontal", "bottom": 0},
    "series": [
        {
            "name":              "Asistencia",
            "type":              "pie",
            "radius":            ["40%", "70%"],
            "avoidLabelOverlap": True,
            "label":             {"show": True, "formatter": "{b}: {c}"},
            "data":              [],
        }
    ],
}


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "tipo":          None,   # str | None — uno de los 9 IDs de tipo
        "grupo_id":      None,
        "asignacion_id": None,
        "periodo_id":    None,
        "grupos":        [],
        "asignaciones":  [],
        "periodos":      [],
        "todas_asignaciones_docente": [],  # solo usado cuando rol == "profesor"
        "datos":         None,   # list | dict | None
        "datos_listos":  False,
    }


# ── Helpers de carga ──────────────────────────────────────────────────────────

def _cargar_grupos(ctx: SessionContext, _s: dict) -> None:
    """
    Carga los grupos visibles según el rol:
    - profesor: solo los grupos de sus asignaciones propias.
    - admin / director / coordinador: todos los grupos.

    Para el rol profesor también pre-carga _s["todas_asignaciones_docente"]
    con sus asignaciones completas, para filtrarlas después cuando cambia el grupo.
    """
    if ctx.usuario_rol == "profesor":
        try:
            todas = Container.asignacion_service().listar_por_docente(ctx.usuario_id)
            _s["todas_asignaciones_docente"] = todas
            grupos_ids   = {a.grupo_id for a in todas}
            grupos_infra = Container.infraestructura_service().listar_grupos()
            _s["grupos"] = [g for g in grupos_infra if g.id in grupos_ids]
        except Exception as exc:
            logger.error("Error cargando grupos del docente: %s", exc)
            _s["grupos"] = []
            _s["todas_asignaciones_docente"] = []
    else:
        _s["todas_asignaciones_docente"] = []
        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error cargando grupos: %s", exc)
            _s["grupos"] = []


def _cargar_asignaciones(ctx: SessionContext, _s: dict) -> None:
    """
    Carga las asignaciones del grupo seleccionado según el rol:
    - profesor: filtra dentro de sus propias asignaciones (ya cargadas).
    - otros roles: consulta todas las asignaciones del grupo.
    """
    if not _s["grupo_id"]:
        _s["asignaciones"] = []
        return
    if ctx.usuario_rol == "profesor":
        # Filtrar las asignaciones del docente por el grupo seleccionado
        _s["asignaciones"] = [
            a for a in _s.get("todas_asignaciones_docente", [])
            if a.grupo_id == _s["grupo_id"]
        ]
    else:
        try:
            filtro = FiltroAsignacionesDTO(grupo_id=_s["grupo_id"])
            _s["asignaciones"] = Container.asignacion_service().listar_con_info(filtro)
        except Exception as exc:
            logger.error("Error cargando asignaciones: %s", exc)
            _s["asignaciones"] = []


def _cargar_periodos(ctx: SessionContext, _s: dict) -> None:
    try:
        anio_id = ctx.anio_id
        _s["periodos"] = Container.periodo_service().listar_por_anio(anio_id) if anio_id else []
    except Exception as exc:
        logger.error("Error cargando periodos: %s", exc)
        _s["periodos"] = []


def _tipo_activo(_s: dict) -> dict | None:
    return _TIPOS_MAP.get(_s["tipo"])


def _filtros_completos(_s: dict) -> bool:
    tipo = _tipo_activo(_s)
    if not tipo:
        return False
    filtros = tipo["filtros"]
    if "grupo" in filtros and not _s["grupo_id"]:
        return False
    if "asignatura" in filtros and not _s["asignacion_id"]:
        return False
    if "periodo" in filtros and not _s["periodo_id"]:
        return False
    return True


def _cargar_datos(ctx: SessionContext, _s: dict) -> None:
    svc   = Container.estadisticos_service()
    tipo  = _s["tipo"]
    gid   = _s["grupo_id"]
    aid   = _s["asignacion_id"]
    pid   = _s["periodo_id"]
    anio  = ctx.anio_id

    try:
        if tipo == "consolidado_notas":
            _s["datos"] = svc.consolidado_notas_grupo(gid, pid)
        elif tipo == "consolidado_asistencia":
            _s["datos"] = svc.consolidado_asistencia_grupo(gid, pid)
        elif tipo == "ranking_grupo":
            _s["datos"] = svc.ranking_grupo(gid, pid)
        elif tipo == "distribucion_desempenos":
            _s["datos"] = svc.distribucion_desempenos(
                grupo_id=gid, asignacion_id=aid, periodo_id=pid, anio_id=anio
            )
        elif tipo == "comparativo_periodos":
            _s["datos"] = svc.comparativo_periodos(
                grupo_id=gid, asignacion_id=aid, anio_id=anio
            )
        elif tipo == "promedios_area":
            _s["datos"] = svc.promedios_por_area(gid, pid)
        elif tipo == "tendencia_asistencia":
            _s["datos"] = svc.tendencia_asistencia(gid, aid, pid)
        elif tipo == "estados_asistencia":
            _s["datos"] = svc.distribucion_estados_asistencia(gid, aid, pid)
        elif tipo == "consolidado_anual":
            _s["datos"] = svc.consolidado_anual_grupo(gid, anio_id=anio)
        else:
            _s["datos"] = None
        _s["datos_listos"] = True
    except Exception as exc:
        logger.error("Error cargando datos para %s: %s", tipo, exc)
        ui.notify(f"Error al obtener datos: {exc}", type="negative")
        _s["datos"] = None
        _s["datos_listos"] = False


def _nombre_archivo(_s: dict) -> str:
    tipo = _s["tipo"] or "informe"
    gid  = _s["grupo_id"] or "sg"
    pid  = _s["periodo_id"] or ("anual" if _s["tipo"] == "consolidado_anual" else "sp")
    hoy  = date.today().strftime("%Y%m%d")
    return f"{tipo}_{gid}_{pid}_{hoy}"


# ── Renders de preview ────────────────────────────────────────────────────────

def _render_stats_summary(_s: dict) -> None:
    """Renderiza tarjetas de estadísticos resumidos según el tipo de informe."""
    datos = _s["datos"]
    tipo  = _s["tipo"]
    if not datos:
        return

    stats: list[tuple[str, str, str, str]] = []  # (titulo, valor, icono, variante)

    if tipo in ("consolidado_notas", "ranking_grupo") and isinstance(datos, list) and datos:
        prom_field = "promedio_periodo" if "promedio_periodo" in datos[0] else "promedio"
        n = len(datos)
        promedios = [float(r.get(prom_field, 0) or 0) for r in datos]
        promedio_grupal = sum(promedios) / n if n else 0
        aprobados = sum(1 for p in promedios if p >= 60)
        stats = [
            ("Estudiantes",     str(n),                                                        Icons.STUDENTS, "primary"),
            ("Promedio grupal", f"{promedio_grupal:.1f}",                                      Icons.GRADES,   "info"),
            ("Aprobados",       f"{aprobados} ({aprobados * 100 // n if n else 0}%)",          Icons.CHECK,    "success"),
            ("Reprobados",      str(n - aprobados),                                            Icons.WARNING,  "danger"),
        ]
        if tipo == "ranking_grupo":
            mejor = max(promedios) if promedios else 0
            menor = min(promedios) if promedios else 0
            stats.append(("Mejor nota", f"{mejor:.1f}", Icons.GRADES,  "success"))
            stats.append(("Menor nota", f"{menor:.1f}", Icons.WARNING, "danger"))

    elif tipo == "consolidado_asistencia" and isinstance(datos, list) and datos:
        n = len(datos)
        porcentajes = [float(r.get("porcentaje", 0) or 0) for r in datos]
        pct_prom = sum(porcentajes) / n if n else 0
        bajo_70 = sum(1 for p in porcentajes if p < 70)
        stats = [
            ("Estudiantes",        str(n),             Icons.STUDENTS, "primary"),
            ("% Asistencia prom.", f"{pct_prom:.1f}%", Icons.CHECK,    "success"),
            ("Bajo 70%",           str(bajo_70),        Icons.WARNING,  "danger"),
        ]

    elif tipo == "consolidado_anual" and isinstance(datos, list) and datos:
        n = len(datos)
        defs = [float(r.get("definitiva", 0) or 0) for r in datos]
        prom = sum(defs) / n if n else 0
        promovidos = sum(1 for r in datos if str(r.get("estado", "")).lower() == "promovido")
        stats = [
            ("Estudiantes",      str(n),             Icons.STUDENTS, "primary"),
            ("Definitiva prom.", f"{prom:.1f}",       Icons.GRADES,   "info"),
            ("Promovidos",       str(promovidos),     Icons.CHECK,    "success"),
            ("Reprobados",       str(n - promovidos), Icons.WARNING,  "danger"),
        ]

    elif isinstance(datos, dict):
        total = sum(datos.values()) if datos else 0
        stats = [("Total registros", str(total), Icons.GRADES, "primary")]

    elif isinstance(datos, list):
        stats = [("Total registros", str(len(datos)), Icons.GRADES, "primary")]

    if not stats:
        return

    with ui.element("div").classes("stats-summary-row"):
        for titulo, valor, icono, variante in stats:
            stat_card(titulo=titulo, valor=valor, icono=icono, variante=variante)


def _render_consolidado_notas(datos: list[dict]) -> None:
    if not datos:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos para los filtros seleccionados").classes("tablero-empty-hint")
        return

    primer = datos[0]
    keys_excl  = {"estudiante_id", "nombre_completo", "promedio", "promedio_periodo"}
    asignaturas = [k for k in primer.keys() if k not in keys_excl]

    col_defs = [{"headerName": "Estudiante", "field": "nombre_completo", "minWidth": 200}]
    for asig in asignaturas:
        col_defs.append({"headerName": asig, "field": asig, "width": 130})
    # Columna de promedio — puede llamarse "promedio" o "promedio_periodo"
    prom_field = "promedio_periodo" if "promedio_periodo" in primer else "promedio"
    col_defs.append({"headerName": "Promedio", "field": prom_field, "width": 110})

    with ui.element("div").classes("aggrid-scroll-wrapper"):
        ui.aggrid({
            "columnDefs":    col_defs,
            "rowData":       datos,
            "defaultColDef": {"resizable": True, "sortable": True},
        }).classes("w-full h-full")
    ui.label(f"Vista previa: {len(datos)} filas").classes("text-secondary")


def _render_consolidado_asistencia(datos: list[dict]) -> None:
    if not datos:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos para los filtros seleccionados").classes("tablero-empty-hint")
        return

    col_defs = [
        {"headerName": "Estudiante",  "field": "nombre_completo",       "minWidth": 200},
        {"headerName": "Asignatura",  "field": "nombre_asignatura",     "minWidth": 150},
        {"headerName": "P",           "field": "presentes",              "width": 70},
        {"headerName": "FJ",          "field": "faltas_justificadas",    "width": 70},
        {"headerName": "FI",          "field": "faltas_injustificadas",  "width": 70},
        {"headerName": "R",           "field": "retrasos",               "width": 70},
        {"headerName": "E",           "field": "excusas",                "width": 70},
        {"headerName": "%",           "field": "porcentaje",             "width": 80},
    ]
    with ui.element("div").classes("aggrid-scroll-wrapper"):
        ui.aggrid({
            "columnDefs":    col_defs,
            "rowData":       datos,
            "defaultColDef": {"resizable": True, "sortable": True},
        }).classes("w-full h-full")
    ui.label(f"Vista previa: {len(datos)} filas").classes("text-secondary")


def _render_ranking(datos: list[dict]) -> None:
    if not datos:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos para los filtros seleccionados").classes("tablero-empty-hint")
        return

    col_defs = [
        {"headerName": "#",          "field": "posicion",       "width": 70},
        {"headerName": "Estudiante", "field": "nombre_completo", "minWidth": 200},
        {"headerName": "Promedio",   "field": "promedio",        "width": 110},
    ]
    with ui.element("div").classes("aggrid-scroll-wrapper"):
        ui.aggrid({
            "columnDefs":    col_defs,
            "rowData":       datos,
            "defaultColDef": {"resizable": True, "sortable": True},
        }).classes("w-full h-full")
    ui.label(f"Vista previa: {len(datos)} filas").classes("text-secondary")


def _render_consolidado_anual(datos: list[dict]) -> None:
    if not datos:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos para los filtros seleccionados").classes("tablero-empty-hint")
        return

    primer = datos[0]
    keys_fijas = {"estudiante_id", "nombre_completo", "definitiva", "estado"}
    periodos   = [k for k in primer.keys() if k not in keys_fijas]

    col_defs = [{"headerName": "Estudiante",  "field": "nombre_completo", "minWidth": 200}]
    for p in periodos:
        col_defs.append({"headerName": p, "field": p, "width": 110})
    col_defs.append({"headerName": "Definitiva", "field": "definitiva", "width": 110})
    col_defs.append({"headerName": "Estado",     "field": "estado",     "width": 120})

    with ui.element("div").classes("aggrid-scroll-wrapper"):
        ui.aggrid({
            "columnDefs":    col_defs,
            "rowData":       datos,
            "defaultColDef": {"resizable": True, "sortable": True},
        }).classes("w-full h-full")
    ui.label(f"Vista previa: {len(datos)} filas").classes("text-secondary")


def _render_donut(datos: dict) -> None:
    if not datos:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos para los filtros seleccionados").classes("tablero-empty-hint")
        return

    opts = copy.deepcopy(_EC_DONUT_OPTIONS)
    opts["series"][0]["data"] = [
        {
            "name":      nivel,
            "value":     cant,
            "itemStyle": {"color": _NIVEL_COLORES.get(nivel, "#999")},
        }
        for nivel, cant in datos.items()
    ]
    ui.echart(opts).classes("echart-md")
    total = sum(datos.values())
    ui.label(f"Vista previa: {total} registros").classes("text-secondary")


def _render_linea_comparativo(datos: list[dict]) -> None:
    if not datos:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos para los filtros seleccionados").classes("tablero-empty-hint")
        return

    opts = copy.deepcopy(_EC_LINE_OPTIONS)
    opts["xAxis"]["data"]      = [r.get("periodo_nombre", str(r.get("periodo_numero", ""))) for r in datos]
    opts["series"][0]["data"]  = [round(r.get("promedio", 0), 1) for r in datos]
    ui.echart(opts).classes("echart-md")
    ui.label(f"Vista previa: {len(datos)} registros").classes("text-secondary")


def _render_linea_tendencia(datos: list[dict]) -> None:
    if not datos:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos para los filtros seleccionados").classes("tablero-empty-hint")
        return

    opts = copy.deepcopy(_EC_LINE_ASISTENCIA_OPTIONS)
    opts["xAxis"]["data"]     = [r.get("semana", r.get("fecha", str(i))) for i, r in enumerate(datos)]
    opts["series"][0]["data"] = [round(r.get("porcentaje", r.get("pct", 0)), 1) for r in datos]
    ui.echart(opts).classes("echart-md")
    ui.label(f"Vista previa: {len(datos)} registros").classes("text-secondary")


def _render_barras(datos: list[dict]) -> None:
    if not datos:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos para los filtros seleccionados").classes("tablero-empty-hint")
        return

    opts = copy.deepcopy(_EC_BAR_OPTIONS)
    opts["yAxis"]["data"]     = [r.get("area", r.get("nombre_area", str(i))) for i, r in enumerate(datos)]
    opts["series"][0]["data"] = [round(r.get("promedio", 0), 1) for r in datos]
    ui.echart(opts).classes("echart-lg")
    ui.label(f"Vista previa: {len(datos)} registros").classes("text-secondary")


def _render_pie_asistencia(datos: dict) -> None:
    if not datos:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Sin datos para los filtros seleccionados").classes("tablero-empty-hint")
        return

    opts = copy.deepcopy(_EC_PIE_OPTIONS)
    opts["series"][0]["data"] = [
        {
            "name":      estado,
            "value":     cant,
            "itemStyle": {"color": _ASISTENCIA_COLORES.get(estado, "#999")},
        }
        for estado, cant in datos.items()
    ]
    ui.echart(opts).classes("echart-md")
    total = sum(datos.values()) if isinstance(datos, dict) else len(datos)
    ui.label(f"Vista previa: {total} registros").classes("text-secondary")


def _render_preview(_s: dict) -> None:
    tipo = _s["tipo"]
    if not _s["datos_listos"] or _s["datos"] is None:
        with ui.element("div").classes("tablero-empty"):
            ui.label(
                "Selecciona un tipo de informe y haz clic en Previsualizar"
            ).classes("tablero-empty-hint")
        return

    datos = _s["datos"]

    if tipo == "consolidado_notas":
        _render_consolidado_notas(datos)
    elif tipo == "consolidado_asistencia":
        _render_consolidado_asistencia(datos)
    elif tipo == "ranking_grupo":
        _render_ranking(datos)
    elif tipo == "consolidado_anual":
        _render_consolidado_anual(datos)
    elif tipo == "distribucion_desempenos":
        _render_donut(datos)
    elif tipo == "comparativo_periodos":
        _render_linea_comparativo(datos)
    elif tipo == "tendencia_asistencia":
        _render_linea_tendencia(datos)
    elif tipo == "promedios_area":
        _render_barras(datos)
    elif tipo == "estados_asistencia":
        _render_pie_asistencia(datos)
    else:
        with ui.element("div").classes("tablero-empty"):
            ui.label("Tipo de informe no soportado.").classes("tablero-empty-hint")


# ── Helpers de exportación ───────────────────────────────────────────────────

def _exportar_excel(ctx: SessionContext, _s: dict) -> None:
    tipo  = _s["tipo"]
    gid   = _s["grupo_id"]
    pid   = _s["periodo_id"]
    anio  = ctx.anio_id
    datos = _s["datos"]
    nombre = _nombre_archivo(_s) + ".xlsx"

    try:
        svc_inf  = Container.informe_service()
        exporter = svc_inf._get_exporter_o_lanzar()

        # Para tipos tabulares (list[dict]), sanitizar antes de exportar
        if tipo == "consolidado_notas":
            content = exporter.exportar_excel(
                sanitizar_datos_exportacion(datos or []),
                nombre_hoja="Consolidado Notas",
            )
        elif tipo == "consolidado_asistencia":
            content = exporter.exportar_excel(
                sanitizar_datos_exportacion(datos or []),
                nombre_hoja="Consolidado Asistencia",
            )
        elif tipo == "consolidado_anual":
            # generar_consolidado_anual ya aplica sanitizar_datos_exportacion internamente
            content = svc_inf.generar_consolidado_anual(
                gid, anio, formato=FormatoInforme.EXCEL
            )
        elif tipo == "ranking_grupo":
            content = exporter.exportar_excel(
                sanitizar_datos_exportacion(datos if isinstance(datos, list) else []),
                nombre_hoja="Ranking",
            )
        elif tipo == "estados_asistencia":
            _LABEL_ESTADO = {"P": "Presente", "FJ": "Falta Justificada",
                             "FI": "Falta Injustificada", "R": "Retraso", "E": "Excusa"}
            filas = [{"Estado": _LABEL_ESTADO.get(k, k), "Registros": v}
                     for k, v in (datos or {}).items()]
            content = exporter.exportar_excel(filas, nombre_hoja="Estados Asistencia")
        elif tipo == "distribucion_desempenos":
            filas = [{"Nivel de Desempeño": k, "Estudiantes": v}
                     for k, v in (datos or {}).items()]
            content = exporter.exportar_excel(filas, nombre_hoja="Distribución Desempeños")
        elif tipo == "comparativo_periodos":
            raw = sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])
            filas = [
                {"Periodo": r.get("periodo_nombre", r.get("Periodo", "")),
                 "Promedio": r.get("promedio", r.get("Promedio", 0))}
                for r in raw
            ]
            content = exporter.exportar_excel(filas, nombre_hoja="Comparativo Periodos")
        elif tipo == "promedios_area":
            filas = sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])
            content = exporter.exportar_excel(filas, nombre_hoja="Promedios por Área")
        elif tipo == "tendencia_asistencia":
            filas = [{"Semana": r.get("semana", ""), "% Asistencia": r.get("porcentaje", 0)}
                     for r in (datos if isinstance(datos, list) else [])]
            content = exporter.exportar_excel(filas, nombre_hoja="Tendencia Asistencia")
        else:
            filas = sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])
            content = exporter.exportar_excel(filas, nombre_hoja=tipo)

        ui.download(content, nombre)
    except Exception as exc:
        logger.error("Error exportando Excel (%s): %s", tipo, exc)
        ui.notify(f"Error al exportar: {exc}", type="negative")


def _exportar_pdf(ctx: SessionContext, _s: dict) -> None:
    tipo   = _s["tipo"]
    gid    = _s["grupo_id"]
    pid    = _s["periodo_id"]
    anio   = ctx.anio_id
    datos  = _s["datos"]
    nombre = _nombre_archivo(_s) + ".pdf"

    try:
        svc_inf  = Container.informe_service()
        exporter = svc_inf._get_exporter_o_lanzar()

        def _inyectar_meta(html_str: str) -> str:
            """Inyecta <meta> tags de informe en el <head> del HTML para el membrete PDF."""
            grupo_nombre = next(
                (g.nombre or g.codigo for g in _s["grupos"] if g.id == _s["grupo_id"]), ""
            )
            periodo_nombre = next(
                (getattr(p, "nombre", str(p.id)) for p in _s["periodos"] if p.id == _s["periodo_id"]), ""
            )
            asig_nombre = next(
                (
                    getattr(a, "asignatura_nombre", "")
                    for a in _s["asignaciones"]
                    if getattr(a, "asignacion_id", None) == _s["asignacion_id"]
                ),
                "",
            ) if _s.get("asignacion_id") else ""
            metas = (
                f'<meta name="report-grupo" content="{grupo_nombre}">'
                f'<meta name="report-periodo" content="{periodo_nombre}">'
                f'<meta name="report-asignatura" content="{asig_nombre}">'
            )
            return html_str.replace("</head>", f"{metas}</head>", 1)

        if tipo == "consolidado_notas":
            filas   = sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])
            html    = svc_inf._datos_a_html(filas, titulo="Consolidado de Notas")
            content = exporter.exportar_pdf(_inyectar_meta(html))
        elif tipo == "consolidado_asistencia":
            filas   = sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])
            html    = svc_inf._datos_a_html(filas, titulo="Consolidado de Asistencia")
            content = exporter.exportar_pdf(_inyectar_meta(html))
        elif tipo == "consolidado_anual":
            # generar_consolidado_anual ya aplica sanitizar_datos_exportacion internamente
            content = svc_inf.generar_consolidado_anual(
                gid, anio, formato=FormatoInforme.PDF
            )
        elif tipo == "ranking_grupo":
            filas   = sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])
            html    = svc_inf._datos_a_html(filas, titulo="Ranking del Grupo")
            content = exporter.exportar_pdf(_inyectar_meta(html))
        elif tipo == "distribucion_desempenos":
            filas = [{"Nivel de Desempeño": k, "Estudiantes": v} for k, v in (datos or {}).items()]
            html  = svc_inf._datos_a_html(filas, titulo="Distribución de Desempeños")
            content = exporter.exportar_pdf(_inyectar_meta(html))
        elif tipo == "estados_asistencia":
            _LABEL_ESTADO = {"P": "Presente", "FJ": "Falta Justificada",
                             "FI": "Falta Injustificada", "R": "Retraso", "E": "Excusa"}
            filas = [{"Estado": _LABEL_ESTADO.get(k, k), "Registros": v}
                     for k, v in (datos or {}).items()]
            html  = svc_inf._datos_a_html(filas, titulo="Estados de Asistencia")
            content = exporter.exportar_pdf(_inyectar_meta(html))
        elif tipo == "comparativo_periodos":
            filas = sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])
            # Renombrar campos específicos de este tipo
            filas = [
                {"Periodo": r.get("periodo_nombre", r.get("Periodo", "")),
                 "Promedio": r.get("promedio", r.get("Promedio", 0))}
                for r in filas
            ]
            html  = svc_inf._datos_a_html(filas, titulo="Comparativo por Periodos")
            content = exporter.exportar_pdf(_inyectar_meta(html))
        elif tipo == "promedios_area":
            filas = sanitizar_datos_exportacion(datos if isinstance(datos, list) else [])
            html  = svc_inf._datos_a_html(filas, titulo="Promedios por Área")
            content = exporter.exportar_pdf(_inyectar_meta(html))
        elif tipo == "tendencia_asistencia":
            filas = [{"Semana": r.get("semana", ""), "% Asistencia": r.get("porcentaje", 0)}
                     for r in (datos if isinstance(datos, list) else [])]
            html  = svc_inf._datos_a_html(filas, titulo="Tendencia de Asistencia")
            content = exporter.exportar_pdf(_inyectar_meta(html))
        else:
            ui.notify("Tipo de informe no reconocido.", type="warning")
            return

        ui.download(content, nombre)
    except Exception as exc:
        logger.error("Error exportando PDF (%s): %s", tipo, exc)
        ui.notify(f"Error al exportar PDF: {exc}", type="negative")


# ── Página ────────────────────────────────────────────────────────────────────

@ui.page("/informes/estadisticos")
def estadisticos_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()

    # Cargar datos iniciales
    # _cargar_grupos ya gestiona el rol internamente:
    # - profesor → solo sus grupos + pre-carga todas_asignaciones_docente
    # - otros    → todos los grupos
    _cargar_grupos(ctx, _s)
    _cargar_periodos(ctx, _s)

    # Pre-seleccionar grupo para profesor (si tiene uno en contexto)
    if ctx.usuario_rol == "profesor" and ctx.grupo_id:
        _s["grupo_id"] = ctx.grupo_id

    if _s["grupo_id"]:
        _cargar_asignaciones(ctx, _s)

    # ── Refreshables ─────────────────────────────────────────────────────────

    @ui.refreshable
    def filtros_refreshable() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("panel-header"):
                ui.label("Configuración del Informe").classes("panel-title")

            # Selector de tipo de informe
            ui.select(
                label="Tipo de Informe",
                options=_TIPOS_SELECT_OPTS,
                value=_s["tipo"],
                on_change=lambda e: on_tipo_change(e.value),
            ).classes("w-full q-mb-md")

            tipo = _tipo_activo(_s)
            if not tipo:
                return

            filtros_req = tipo["filtros"]
            num_cols    = len(filtros_req)
            grid_cls    = "form-grid-3" if num_cols >= 3 else "form-grid-2" if num_cols == 2 else "w-full"

            with ui.element("div").classes(grid_cls):
                # Selector de Grupo
                # NOTA: las claves del dict deben ser str para que NiceGUI/Quasar
                # haga el match correcto entre options y value (JSON serializa int
                # keys como strings, rompiendo la comparación de igualdad en Quasar).
                if "grupo" in filtros_req:
                    grupos_opts = {
                        str(g.id): g.nombre or g.codigo
                        for g in _s["grupos"]
                    }
                    ui.select(
                        label="Grupo",
                        options=grupos_opts or {"": "Sin grupos"},
                        value=str(_s["grupo_id"]) if _s["grupo_id"] is not None else None,
                        on_change=lambda e: on_grupo_change(e.value),
                    ).classes("w-full")

                # Selector de Asignatura (depende de Grupo)
                if "asignatura" in filtros_req:
                    asig_opts = {
                        str(a.asignacion_id): a.asignatura_nombre
                        for a in _s["asignaciones"]
                    }
                    ui.select(
                        label="Asignatura",
                        options=asig_opts,
                        value=str(_s["asignacion_id"]) if _s["asignacion_id"] is not None else None,
                        on_change=lambda e: on_asignatura_change(e.value),
                    ).classes("w-full")

                # Selector de Periodo
                if "periodo" in filtros_req:
                    per_opts = {
                        str(p.id): getattr(p, "nombre", str(p.id))
                        for p in _s["periodos"]
                    }
                    ui.select(
                        label="Periodo",
                        options=per_opts,
                        value=str(_s["periodo_id"]) if _s["periodo_id"] is not None else None,
                        on_change=lambda e: on_periodo_change(e.value),
                    ).classes("w-full")

            with ui.row().classes("justify-end q-mt-md"):
                btn_primary(
                    "Previsualizar",
                    icon=Icons.GRADES,
                    on_click=on_previsualizar,
                    disabled=not _filtros_completos(_s),
                )

    @ui.refreshable
    def preview_refreshable() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("panel-header"):
                ui.label("Vista Previa").classes("panel-title")
            if _s["datos_listos"] and _s["datos"] is not None:
                _render_stats_summary(_s)
            _render_preview(_s)

    @ui.refreshable
    def export_refreshable() -> None:
        with ui.element("div").classes("panel-card"):
            with ui.element("div").classes("panel-header"):
                ui.label("Exportar").classes("panel-title")

            if not _s["datos_listos"]:
                ui.label(
                    "Haz clic en 'Previsualizar' para habilitar la descarga."
                ).classes("text-caption text-grey-6 q-pa-sm")
                return

            tipo_info = _tipo_activo(_s)
            if not tipo_info:
                return

            with ui.row().classes("q-gutter-sm"):
                btn_primary(
                    "Descargar Excel (.xlsx)",
                    icon=Icons.EXPORT,
                    on_click=lambda: _exportar_excel(ctx, _s),
                )
                if tipo_info.get("pdf"):
                    btn_secondary(
                        "Descargar PDF",
                        icon=Icons.EXPORT,
                        on_click=lambda: _exportar_pdf(ctx, _s),
                    )

    # ── Handlers de eventos ──────────────────────────────────────────────────

    def _limpiar_datos() -> None:
        _s["datos"]        = None
        _s["datos_listos"] = False

    def on_tipo_change(nuevo_tipo: str | None) -> None:
        _s["tipo"]          = nuevo_tipo
        _s["asignacion_id"] = None
        _s["periodo_id"]    = None
        _limpiar_datos()
        filtros_refreshable.refresh()
        preview_refreshable.refresh()
        export_refreshable.refresh()

    def on_grupo_change(grupo_id) -> None:
        _s["grupo_id"]      = int(grupo_id) if grupo_id is not None else None
        _s["asignacion_id"] = None
        _limpiar_datos()
        _cargar_asignaciones(ctx, _s)
        filtros_refreshable.refresh()
        preview_refreshable.refresh()
        export_refreshable.refresh()

    def on_asignatura_change(asignacion_id) -> None:
        _s["asignacion_id"] = int(asignacion_id) if asignacion_id is not None else None
        _limpiar_datos()
        filtros_refreshable.refresh()
        preview_refreshable.refresh()
        export_refreshable.refresh()

    def on_periodo_change(periodo_id) -> None:
        _s["periodo_id"] = int(periodo_id) if periodo_id is not None else None
        _limpiar_datos()
        filtros_refreshable.refresh()
        preview_refreshable.refresh()
        export_refreshable.refresh()

    def on_previsualizar() -> None:
        if not _filtros_completos(_s):
            ui.notify("Completa todos los filtros requeridos.", type="warning")
            return
        _cargar_datos(ctx, _s)
        preview_refreshable.refresh()
        export_refreshable.refresh()

    # ── Contenido ────────────────────────────────────────────────────────────

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            filtros_refreshable()
            preview_refreshable()
            export_refreshable()

    app_layout(
        titulo_pagina="Estadísticos",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/informes/estadisticos",
        contenido=contenido,
        ctx=ctx,
    )


__all__ = ["estadisticos_page"]
