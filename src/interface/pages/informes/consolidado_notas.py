"""
src/interface/pages/informes/consolidado_notas.py
=================================================
Página para generar el informe consolidado de notas por grupo y periodo.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*.
  Solo usa Container (servicios) e imports de la capa de interfaz.
  DTOs importados desde src.services.informe_service (re-exports).

Flujo:
  1. Selección de grupo → recarga opciones de asignación y periodo.
  2. Usuario completa filtros (grupo, asignación, periodo, fechas, formato).
  3. "Generar" → construye InformeNotasDTO → informe_service.generar_notas().
  4. ui.download() con los bytes retornados.
  5. Errores capturados → ui.notify con tipo negativo.

Refreshables:
  filtros_refreshable()  — re-renderiza el formulario cuando cambia el grupo.
"""

from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    date_input,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_primary
from src.interface.design.components.form_fields import filter_select
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.interface.presenters.informes.consolidado_presenter import ConsolidadoInformePresenter
from src.services.asignacion_service import FiltroAsignacionesDTO
from src.services.informe_service import InformeNotasDTO

logger = logging.getLogger("CONSOLIDADO_NOTAS")


# ── Estado ────────────────────────────────────────────────────────────────────


def _cargar_listas(ctx: SessionContext, _s: dict) -> None:
    """Carga grupos, asignaciones y periodos desde los servicios."""
    try:
        _s["grupos"] = Container.catalogo_academico_service().listar_grupos()
    except Exception as exc:
        logger.error("Error cargando grupos: %s", exc)
        _s["grupos"] = []

    # Si hay grupo seleccionado, cargar asignaciones y periodos
    if _s["grupo_id"]:
        try:
            filtro = FiltroAsignacionesDTO(grupo_id=_s["grupo_id"])
            _s["asignaciones"] = Container.asignacion_service().listar_con_info(filtro)
        except Exception as exc:
            logger.error("Error cargando asignaciones: %s", exc)
            _s["asignaciones"] = []

        try:
            if ctx.anio_id:
                _s["periodos"] = Container.periodo_service().listar_por_anio(ctx.anio_id)
            else:
                _s["periodos"] = []
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)
            _s["periodos"] = []
    else:
        _s["asignaciones"] = []
        _s["periodos"] = []


# ── Página ────────────────────────────────────────────────────────────────────


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def consolidado_notas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    presenter = ConsolidadoInformePresenter()
    _s = presenter.estado  # misma referencia: los refreshables leen el estado del presenter
    _cargar_listas(ctx, _s)

    @ui.refreshable
    def filtros_refreshable() -> None:
        with ui.element("div").classes("panel-card"):
            ui.label("Filtros del informe").classes("panel-title")

            with ui.element("div").classes("form-grid-2"):
                # Grupo
                grupos_opts = {g.id: g.nombre or g.codigo for g in _s["grupos"]}
                filter_select(
                    label="Grupo",
                    options=grupos_opts,
                    value=_s["grupo_id"],
                    on_change=lambda e: on_grupo_change(e.value),
                    clearable=False,
                )

                # Asignación
                asig_opts = {a.asignacion_id: a.asignatura_nombre for a in _s["asignaciones"]}
                filter_select(
                    label="Asignación",
                    options=asig_opts,
                    value=_s["asignacion_id"],
                    on_change=lambda e: presenter.set_asignacion(e.value),
                    clearable=False,
                )

                # Periodo
                per_opts = {p.id: getattr(p, "nombre", str(p.id)) for p in _s["periodos"]}
                filter_select(
                    label="Periodo",
                    options=per_opts,
                    value=_s["periodo_id"],
                    on_change=lambda e: presenter.set_periodo(e.value),
                    clearable=False,
                )

                # Formato
                filter_select(
                    label="Formato",
                    options={"excel": "Excel (.xlsx)", "pdf": "PDF"},
                    value=_s["formato"],
                    on_change=lambda e: presenter.set_formato(e.value),
                    clearable=False,
                )

                # Fecha desde
                date_input(
                    label="Fecha desde",
                    value=_s["fecha_desde"].isoformat() if _s["fecha_desde"] else "",
                    on_change=lambda v: on_fecha_desde(v or ""),
                    classes="w-full",
                )

                # Fecha hasta
                date_input(
                    label="Fecha hasta",
                    value=_s["fecha_hasta"].isoformat() if _s["fecha_hasta"] else "",
                    on_change=lambda v: on_fecha_hasta(v or ""),
                    classes="w-full",
                )

            with ui.row().classes("justify-end mt-4"):
                btn_primary(
                    "Generar informe",
                    on_click=on_generar,
                    icon=Icons.EXPORT,
                )

    def on_grupo_change(grupo_id) -> None:
        presenter.set_grupo(grupo_id)  # resetea asignación y periodo
        _cargar_listas(ctx, _s)
        filtros_refreshable.refresh()

    def on_fecha_desde(valor: str) -> None:
        presenter.set_fecha_desde(valor)

    def on_fecha_hasta(valor: str) -> None:
        presenter.set_fecha_hasta(valor)

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
            dto = InformeNotasDTO(
                grupo_id=_s["grupo_id"],
                asignacion_id=_s["asignacion_id"],
                periodo_id=_s["periodo_id"],
                fecha_desde=_s["fecha_desde"],
                fecha_hasta=_s["fecha_hasta"],
                formato=_s["formato"],
                incluir_piar=True,
            )
            contenido_bytes = Container.informe_service().generar_notas(dto)
            extension = "xlsx" if _s["formato"] == "excel" else "pdf"
            filename = f"consolidado_notas_grupo{_s['grupo_id']}.{extension}"
            ui.download(content=contenido_bytes, filename=filename)
            toast_success("Informe generado correctamente.")
        except ValueError as exc:
            toast_error(f"Exportador no disponible: {exc}")
        except Exception as exc:
            logger.error("Error generando informe de notas: %s", exc, exc_info=True)
            toast_error("Error al generar el informe. Intenta de nuevo.")

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            filtros_refreshable()

    app_layout(
        ctx,
        contenido,
        page_titulo="Consolidado de Notas",
    )


__all__ = ["consolidado_notas_page"]
