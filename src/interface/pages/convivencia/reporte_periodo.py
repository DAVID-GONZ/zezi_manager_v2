"""
src/interface/pages/convivencia/reporte_periodo.py
==================================================
Reporte de notas + observaciones del periodo por grupo (convivencia_06).

Uso: director de grupo (profesor que dirige), coordinación y dirección.
La página aplica gating por objeto con
`CatalogoAcademicoService.puede_gestionar_comportamiento_en_grupo`.

Regla de capas:
  Esta página NO importa símbolos de `src.domain.models.*`. Solo Container
  (servicios) y componentes del design system.

Flujo:
  1. Guard de sesión → /login.
  2. Carga de grupos: dir/coord ve todos; profesor solo los que dirige.
  3. Carga de periodos del año activo.
  4. Si no autorizado sobre el grupo → empty_state y sin acciones.
  5. Autorizado → tabla por estudiante (nota, nivel, concepto, #obs).
  6. Botones "Exportar PDF" / "Exportar Excel" via `Container.exporter_service()`.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    empty_state,
    toast_error,
    toast_info,
    toast_warning,
)
from src.interface.design.components.buttons import btn_primary, btn_secondary
from src.interface.design.layout import app_layout

logger = logging.getLogger("REPORTE_PERIODO_CONVIVENCIA")

_MSG_NO_AUTORIZADO = (
    "Solo el director de grupo, la coordinación o la dirección pueden "
    "generar el reporte de convivencia de este grupo."
)


# ── Autorización ──────────────────────────────────────────────────────────────

def _autorizado_para_grupo(ctx: SessionContext, grupo_id: int | None) -> bool:
    if not grupo_id:
        return False
    try:
        return Container.catalogo_academico_service().puede_gestionar_comportamiento_en_grupo(
            ctx.usuario_rol, ctx.usuario_id, int(grupo_id)
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed
        logger.warning("No se pudo resolver autorización de reporte: %s", exc)
        return False


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "grupo_id":   None,
        "periodo_id": None,
        "grupos":     [],
        "periodos":   [],
        "filas":      [],  # list[ReporteConvivenciaFilaDTO]
    }


def _cargar_grupos(ctx: SessionContext, _s: dict) -> None:
    """Dir/coord: todos los grupos. Profesor: solo los que dirige (es
    director_grupo_id). Admin: sin grupos (auditor técnico)."""
    try:
        todos = Container.catalogo_academico_service().listar_grupos()
    except Exception as exc:
        logger.error("Error cargando grupos: %s", exc)
        _s["grupos"] = []
        return
    rol = (ctx.usuario_rol or "").lower()
    if rol in ("director", "coordinador"):
        _s["grupos"] = todos
    elif rol == "profesor":
        _s["grupos"] = [
            g for g in todos
            if getattr(g, "director_grupo_id", None) == ctx.usuario_id
        ]
    else:
        _s["grupos"] = []


def _cargar_periodos(ctx: SessionContext, _s: dict) -> None:
    try:
        config = Container.configuracion_service().get_activa()
        anio_id = getattr(config, "id", None) if config else None
        _s["periodos"] = (
            Container.periodo_service().listar_por_anio(anio_id) if anio_id else []
        )
    except Exception as exc:
        logger.warning("Error cargando periodos: %s", exc)
        _s["periodos"] = []


def _cargar_reporte(_s: dict) -> None:
    if not _s["grupo_id"] or not _s["periodo_id"]:
        _s["filas"] = []
        return
    try:
        _s["filas"] = Container.convivencia_service().reporte_periodo_grupo(
            int(_s["grupo_id"]), int(_s["periodo_id"])
        )
    except Exception as exc:
        logger.error("Error cargando reporte de convivencia: %s", exc, exc_info=True)
        _s["filas"] = []


# ── Helpers de presentación / exportación ────────────────────────────────────

def _grupo_nombre(_s: dict) -> str:
    for g in _s["grupos"]:
        if getattr(g, "id", None) == _s["grupo_id"]:
            return getattr(g, "nombre", None) or getattr(g, "codigo", "") or ""
    return ""


def _periodo_nombre(_s: dict) -> str:
    for p in _s["periodos"]:
        if getattr(p, "id", None) == _s["periodo_id"]:
            return getattr(p, "nombre", str(p.id))
    return ""


def _filas_a_dicts(_s: dict) -> list[dict]:
    """Aplana los DTOs a primitivos para la grilla y los exportadores."""
    out: list[dict] = []
    for f in _s["filas"]:
        out.append({
            "estudiante":   f.nombre,
            "nota":         f.valor if f.valor is not None else "",
            "nivel":        f.nivel_nombre or "",
            "concepto":     f.concepto or "",
            "observaciones": "\n".join(f.observaciones) if f.observaciones else "",
            "num_obs":      len(f.observaciones),
        })
    return out


def _datos_a_html(datos: list[dict], titulo: str) -> str:
    """HTML mínimo para el exporter de PDF (tabla plana)."""
    if not datos:
        cuerpo = "<p>Sin datos.</p>"
    else:
        heads = [k for k in datos[0].keys() if k != "num_obs"]
        thead = "".join(f"<th>{h}</th>" for h in heads)
        rows = []
        for r in datos:
            cells = "".join(
                f"<td>{str(r.get(h, '')).replace(chr(10), '<br/>')}</td>"
                for h in heads
            )
            rows.append(f"<tr>{cells}</tr>")
        cuerpo = f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    return (
        f"<html><head><meta charset='utf-8'><title>{titulo}</title>"
        "<style>table{border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:11px}"
        "th,td{border:1px solid #999;padding:4px;vertical-align:top;text-align:left}"
        "th{background:#eee}</style></head>"
        f"<body><h2>{titulo}</h2>{cuerpo}</body></html>"
    )


def _exportar(_s: dict, formato: str) -> None:
    if not _s["filas"]:
        toast_info("No hay datos para exportar.")
        return
    datos = _filas_a_dicts(_s)
    # Para exportación quitamos la columna interna num_obs
    datos_exp = [{k: v for k, v in d.items() if k != "num_obs"} for d in datos]
    grupo = (_grupo_nombre(_s) or "grupo").replace(" ", "_")
    periodo = (_periodo_nombre(_s) or f"p{_s['periodo_id']}").replace(" ", "_")
    base = f"reporte_convivencia_{grupo}_{periodo}"
    try:
        exporter = Container.exporter_service()
        if formato == "excel":
            contenido = exporter.exportar_excel(
                datos_exp, nombre_hoja="Reporte Convivencia"
            )
            ui.download(src=contenido, filename=f"{base}.xlsx")
        else:
            html = _datos_a_html(
                datos_exp,
                titulo=f"Reporte de convivencia — {_grupo_nombre(_s)} · {_periodo_nombre(_s)}",
            )
            contenido = exporter.exportar_pdf(html)
            ui.download(src=contenido, filename=f"{base}.pdf")
    except NotImplementedError:
        toast_warning("Formato no disponible. Verifica las dependencias instaladas.")
    except Exception as exc:
        logger.error("Error exportando reporte (%s): %s", formato, exc, exc_info=True)
        toast_error(f"Error al exportar: {exc}")


# ── Página ────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py.
def reporte_periodo_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _s["grupo_id"]   = ctx.grupo_id
    _s["periodo_id"] = ctx.periodo_id
    _cargar_grupos(ctx, _s)
    _cargar_periodos(ctx, _s)
    _cargar_reporte(_s)

    def on_grupo_change(valor) -> None:
        _s["grupo_id"] = int(valor) if valor is not None else None
        _cargar_reporte(_s)
        _contenido.refresh()

    def on_periodo_change(valor) -> None:
        _s["periodo_id"] = int(valor) if valor is not None else None
        _cargar_reporte(_s)
        _contenido.refresh()

    @ui.refreshable
    def _contenido() -> None:
        ctx_actual = SessionContext.desde_storage() or ctx
        autorizado = _autorizado_para_grupo(ctx_actual, _s["grupo_id"])

        grupos_opts = {
            getattr(g, "id", None): (getattr(g, "nombre", None) or getattr(g, "codigo", ""))
            for g in _s["grupos"]
        }
        periodos_opts = {
            getattr(p, "id", None): getattr(p, "nombre", f"Periodo {getattr(p, 'id', '')}")
            for p in _s["periodos"]
        }

        def contenido_pagina() -> None:
            with ui.element("div").classes("page-stack"):
                # Selectores
                with ui.element("div").classes("panel-card"):
                    with ui.row().classes("panel-toolbar"):
                        ui.select(
                            options=grupos_opts or {None: "Sin grupos disponibles"},
                            label="Grupo",
                            value=_s["grupo_id"],
                            on_change=lambda e: on_grupo_change(e.value),
                        ).classes("andes-input input-min-md").props("outlined dense")

                        ui.select(
                            options=periodos_opts or {None: "Sin periodos"},
                            label="Periodo",
                            value=_s["periodo_id"],
                            on_change=lambda e: on_periodo_change(e.value),
                        ).classes("andes-input input-min-md").props("outlined dense")

                        if autorizado and _s["filas"]:
                            ui.element("div").classes("panel-toolbar-spacer")
                            btn_secondary(
                                "Exportar Excel",
                                icon="table_view",
                                on_click=lambda: _exportar(_s, "excel"),
                            )
                            btn_primary(
                                "Exportar PDF",
                                icon="picture_as_pdf",
                                on_click=lambda: _exportar(_s, "pdf"),
                            )

                # Cuerpo
                if not _s["grupo_id"] or not _s["periodo_id"]:
                    with ui.element("div").classes("panel-card"):
                        empty_state(
                            titulo="Selecciona grupo y periodo",
                            descripcion="Elige un grupo y un periodo para generar el reporte.",
                        )
                    return

                if not autorizado:
                    with ui.element("div").classes("panel-card"):
                        empty_state(
                            titulo="No autorizado para este grupo",
                            descripcion=_MSG_NO_AUTORIZADO,
                        )
                    return

                filas_dict = _filas_a_dicts(_s)
                with ui.element("div").classes("panel-card"):
                    if not filas_dict:
                        empty_state(
                            titulo="Sin estudiantes",
                            descripcion="No hay estudiantes en este grupo.",
                        )
                    else:
                        col_defs = [
                            {"headerName": "Estudiante", "field": "estudiante",
                             "flex": 2, "sortable": True, "pinned": "left"},
                            {"headerName": "Nota", "field": "nota",
                             "width": 100, "type": "numericColumn"},
                            {"headerName": "Nivel", "field": "nivel", "width": 140},
                            {"headerName": "Concepto", "field": "concepto", "flex": 2},
                            {"headerName": "# Obs.", "field": "num_obs", "width": 90,
                             "type": "numericColumn"},
                            {"headerName": "Observaciones", "field": "observaciones",
                             "flex": 3, "wrapText": True, "autoHeight": True},
                        ]
                        with ui.element("div").classes("aggrid-scroll-wrapper"):
                            ui.aggrid({
                                "columnDefs":    col_defs,
                                "rowData":       filas_dict,
                                "defaultColDef": {"resizable": True, "sortable": True},
                            }).classes("w-full")

        app_layout(
            ctx_actual, contenido_pagina,
            page_titulo="Reporte de convivencia por periodo",
            mostrar_asignatura=False,
        )

    _contenido()


__all__ = ["reporte_periodo_page"]
