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
from src.interface.design.components.inline_selectors import inline_periodo_grupo_asignatura
from src.interface.design.layout import app_layout

logger = logging.getLogger("REPORTE_PERIODO_CONVIVENCIA")

_MSG_NO_AUTORIZADO = (
    "Solo el director de grupo, la coordinación o la dirección pueden "
    "generar el reporte de convivencia de este grupo."
)

# Columnas mostradas en la grilla (misma clave que expone el servicio para
# exportación). La página SOLO decide cómo se ven; la composición de datos
# y la generación de PDF/Excel viven en `ConvivenciaService`.
_COL_DEFS = [
    {"headerName": "Estudiante",   "field": "estudiante",   "flex": 2, "sortable": True, "pinned": "left"},
    {"headerName": "Nota",         "field": "nota",         "width": 100, "type": "numericColumn"},
    {"headerName": "Nivel",        "field": "nivel",        "width": 140},
    {"headerName": "Concepto",     "field": "concepto",     "flex": 2},
    {"headerName": "# Obs.",       "field": "num_obs",      "width": 90, "type": "numericColumn"},
    {"headerName": "Observaciones", "field": "observaciones", "flex": 3, "wrapText": True, "autoHeight": True},
]


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
        "grupo_id":              None,
        "periodo_id":            None,
        "filas":                 [],  # list[ReporteConvivenciaFilaDTO]
        # sel_* gestionados por el inline selector
        "sel_periodo_id":        None,
        "sel_periodo_nombre":    "",
        "sel_grupo_id":          None,
        "sel_grupo_nombre":      "",
        "sel_asignacion_id":     None,
        "sel_asignacion_nombre": "",
    }


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


# ── Helpers de presentación ──────────────────────────────────────────────────
# La página SOLO transforma los DTOs a filas para la grilla NiceGUI y presenta
# el nombre del grupo/periodo en el título de descarga. TODA la composición
# del reporte (columnas, aplanado, HTML del PDF) vive en ConvivenciaService.

def _grupo_nombre(_s: dict) -> str:
    return _s.get("sel_grupo_nombre", "") or ""


def _periodo_nombre(_s: dict) -> str:
    return _s.get("sel_periodo_nombre", "") or ""


def _filas_grilla(_s: dict) -> list[dict]:
    """Aplana los DTOs SOLO para la grilla de la página (añade `num_obs`
    para el contador visible; no participa en la exportación)."""
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


def _slug_descarga(_s: dict) -> str:
    grupo   = (_grupo_nombre(_s) or "grupo").replace(" ", "_")
    periodo = (_periodo_nombre(_s) or f"p{_s['periodo_id']}").replace(" ", "_")
    return f"reporte_convivencia_{grupo}_{periodo}"


def _exportar(_s: dict, formato: str) -> None:
    """Pide al servicio los bytes del reporte y ofrece la descarga.
    Sin lógica de composición: eso vive en `ConvivenciaService`."""
    if not _s["filas"]:
        toast_info("No hay datos para exportar.")
        return
    if not _s["grupo_id"] or not _s["periodo_id"]:
        return
    titulo = f"Reporte de convivencia — {_grupo_nombre(_s)} · {_periodo_nombre(_s)}"
    ext = "xlsx" if formato == "excel" else "pdf"
    try:
        contenido = Container.convivencia_service().exportar_reporte_periodo_grupo(
            int(_s["grupo_id"]), int(_s["periodo_id"]), formato, titulo=titulo,
        )
        ui.download(src=contenido, filename=f"{_slug_descarga(_s)}.{ext}")
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
    _cargar_reporte(_s)

    @ui.refreshable
    def _contenido() -> None:
        def on_sel_change(s: dict) -> None:
            _s["grupo_id"]           = s["sel_grupo_id"]
            _s["periodo_id"]         = s["sel_periodo_id"]
            _s["sel_grupo_nombre"]   = s["sel_grupo_nombre"]
            _s["sel_periodo_nombre"] = s["sel_periodo_nombre"]
            _cargar_reporte(_s)
            _contenido.refresh()

        inline_periodo_grupo_asignatura(
            _s, on_sel_change,
            usuario_id=ctx.usuario_id,
            institucion_id=ctx.institucion_id,
            usuario_rol=ctx.usuario_rol,
            preselect_periodo=True,
        )

        autorizado = _autorizado_para_grupo(ctx, _s["grupo_id"])

        def contenido_pagina() -> None:
            with ui.element("div").classes("page-stack"):
                # Exportar
                with ui.element("div").classes("panel-card"):
                    with ui.row().classes("panel-toolbar"):
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

                filas_dict = _filas_grilla(_s)
                with ui.element("div").classes("panel-card"):
                    if not filas_dict:
                        empty_state(
                            titulo="Sin estudiantes",
                            descripcion="No hay estudiantes en este grupo.",
                        )
                    else:
                        with ui.element("div").classes("aggrid-scroll-wrapper"):
                            ui.aggrid({
                                "columnDefs":    _COL_DEFS,
                                "rowData":       filas_dict,
                                "defaultColDef": {"resizable": True, "sortable": True},
                            }).classes("w-full")

        app_layout(
            ctx, contenido_pagina,
            page_titulo="Reporte de convivencia por periodo",
        )

    _contenido()


__all__ = ["reporte_periodo_page"]
