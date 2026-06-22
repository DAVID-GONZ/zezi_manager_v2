"""
src/interface/pages/informes/consolidado_asistencia.py
======================================================
Página para generar el informe consolidado de asistencia por grupo y periodo.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.
  DTOs importados desde src.services.informe_service (re-exports).

Flujo:
  1. Selección de grupo → recarga opciones de asignación y periodo.
  2. Usuario completa filtros.
  3. "Generar" → construye InformeAsistenciaDTO → informe_service.generar_asistencia().
  4. ui.download() con los bytes retornados.
"""
from __future__ import annotations

import logging
from datetime import date

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary
from src.services.informe_service import InformeAsistenciaDTO
from src.services.asignacion_service import FiltroAsignacionesDTO
from src.interface.design.components import date_input, toast_error, toast_success, toast_warning

logger = logging.getLogger("CONSOLIDADO_ASISTENCIA")


# ── Estado ────────────────────────────────────────────────────────────────────

def _estado_inicial() -> dict:
    return {
        "grupo_id":      None,
        "asignacion_id": None,
        "periodo_id":    None,
        "fecha_desde":   None,
        "fecha_hasta":   None,
        "formato":       "excel",
        "grupos":        [],
        "asignaciones":  [],
        "periodos":      [],
    }


def _cargar_listas(ctx: SessionContext, _s: dict) -> None:
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


# ── Página ────────────────────────────────────────────────────────────────────

# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def consolidado_asistencia_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    _s = _estado_inicial()
    _s["grupo_id"] = ctx.grupo_id
    _cargar_listas(ctx, _s)

    @ui.refreshable
    def filtros_refreshable() -> None:
        with ui.element("div").classes("andes-card"):
            ui.label("Filtros del informe").classes("text-subtitle1 text-weight-medium u-mb-md")

            with ui.element("div").classes("form-grid-2"):
                grupos_opts = {g.id: g.nombre or g.codigo for g in _s["grupos"]}
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

                ui.select(
                    label="Formato",
                    options={"excel": "Excel (.xlsx)", "pdf": "PDF"},
                    value=_s["formato"],
                    on_change=lambda e: _s.update({"formato": e.value}),
                ).classes("w-full")

                date_input(
                    label="Fecha desde",
                    value=_s["fecha_desde"].isoformat() if _s["fecha_desde"] else "",
                    on_change=lambda v: on_fecha(v, "fecha_desde"),
                    classes="w-full",
                )

                date_input(
                    label="Fecha hasta",
                    value=_s["fecha_hasta"].isoformat() if _s["fecha_hasta"] else "",
                    on_change=lambda v: on_fecha(v, "fecha_hasta"),
                    classes="w-full",
                )

            with ui.row().classes("justify-end u-mt-md"):
                btn_primary(
                    "Generar informe",
                    icon=Icons.EXPORT,
                    on_click=on_generar,
                )

    def on_grupo_change(grupo_id) -> None:
        _s["grupo_id"] = grupo_id
        _s["asignacion_id"] = None
        _s["periodo_id"] = None
        _cargar_listas(ctx, _s)
        filtros_refreshable.refresh()

    def on_fecha(valor: str, campo: str) -> None:
        try:
            _s[campo] = date.fromisoformat(valor) if valor else None
        except ValueError:
            pass

    def on_generar() -> None:
        if not _s["grupo_id"]:
            toast_warning("Selecciona un grupo.")
            return
        if not _s["asignacion_id"]:
            toast_warning("Selecciona una asignación.")
            return
        if not _s["periodo_id"]:
            toast_warning("Selecciona un periodo.")
            return
        if not _s["fecha_desde"] or not _s["fecha_hasta"]:
            toast_warning("Completa las fechas.")
            return
        try:
            dto = InformeAsistenciaDTO(
                grupo_id=_s["grupo_id"],
                asignacion_id=_s["asignacion_id"],
                periodo_id=_s["periodo_id"],
                fecha_desde=_s["fecha_desde"],
                fecha_hasta=_s["fecha_hasta"],
                formato=_s["formato"],
            )
            contenido_bytes = Container.informe_service().generar_asistencia(dto)
            ext = "xlsx" if _s["formato"] == "excel" else "pdf"
            ui.download(content=contenido_bytes, filename=f"asistencia_grupo{_s['grupo_id']}.{ext}")
            toast_success("Informe generado.")
        except ValueError as exc:
            toast_error(f"Exportador no disponible: {exc}")
        except Exception as exc:
            logger.error("Error generando informe de asistencia: %s", exc, exc_info=True)
            toast_error("Error al generar el informe.")

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            filtros_refreshable()

    app_layout(
        ctx, contenido,
        page_titulo="Consolidado de Asistencia",
        mostrar_contexto=False,  # filtros internos periodo/grupo; no depende del chip (paso_41)
    )


__all__ = ["consolidado_asistencia_page"]
