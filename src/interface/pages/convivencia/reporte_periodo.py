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


# ── Helpers de presentación ──────────────────────────────────────────────────
# La página SOLO transforma los DTOs a filas para la grilla NiceGUI y presenta
# el nombre del grupo/periodo en el título de descarga. TODA la composición
# del reporte (columnas, aplanado, HTML del PDF) vive en ConvivenciaService.

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
            ctx_actual, contenido_pagina,
            page_titulo="Reporte de convivencia por periodo",
            mostrar_asignatura=False,
        )

    _contenido()


__all__ = ["reporte_periodo_page"]
