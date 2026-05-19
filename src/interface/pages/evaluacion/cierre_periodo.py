"""
src/interface/pages/evaluacion/cierre_periodo.py
=================================================
Cierre de periodo académico por asignación.
Ruta: /evaluacion/cierre-periodo
Acceso: admin, director, coordinador

Calcula y registra la nota definitiva de todos los estudiantes
en una asignación al cerrar un periodo. Operación irreversible.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.services.asignacion_service import FiltroAsignacionesDTO
from src.services.cierre_service import ContextoAcademicoDTO

logger = logging.getLogger("EVALUACION.CIERRE_PERIODO")

_ROLES_PERMITIDOS = ("admin", "director", "coordinador")


@ui.page("/evaluacion/cierre-periodo")
def cierre_periodo_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in _ROLES_PERMITIDOS:
        ui.notify("Acceso no autorizado", type="negative")
        ui.navigate.to("/inicio")
        return

    logger.info("Cierre periodo: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "periodos":       [],
        "asignaciones":   [],
        "planilla":       [],
        "resultado":      [],
        "periodo_id":     None,
        "asignacion_id":  None,
        "anio_id":        None,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            _s["anio_id"] = config.id if config else None
            anio_id = _s["anio_id"]
            if anio_id:
                _s["periodos"] = Container.periodo_service().listar_por_anio(anio_id)
            else:
                _s["periodos"] = []
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)
            _s["periodos"] = []

        try:
            filtro = FiltroAsignacionesDTO(solo_activas=True)
            _s["asignaciones"] = Container.asignacion_service().listar_con_info(filtro)
        except Exception as exc:
            logger.error("Error cargando asignaciones: %s", exc)
            _s["asignaciones"] = []

    def _cargar_planilla() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        if not asig_id or not per_id:
            _s["planilla"] = []
            return
        try:
            _s["planilla"] = Container.evaluacion_service().obtener_planilla(
                asig_id, per_id, ctx=None
            )
        except Exception as exc:
            logger.error("Error cargando planilla: %s", exc)
            _s["planilla"] = []

    _cargar_estado()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _abrir_confirmar_cierre() -> None:
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]
        if not asig_id or not per_id:
            ui.notify("Seleccione periodo y asignación", type="warning")
            return

        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            with ui.element("div").classes("flex items-center gap-2 mb-3"):
                ThemeManager.icono(Icons.WARNING, size=24, color="var(--color-warning)")
                ui.label("Confirmar cierre de periodo").classes("text-lg font-bold")

            ui.label(
                "Esta operación calcula las definitivas para todos los estudiantes "
                "de esta asignación en el periodo seleccionado."
            ).classes("text-sm mb-2")
            ui.label("No se puede deshacer.").classes(
                "text-sm font-semibold text-red-600 mb-4"
            )
            ui.label(
                f"Estudiantes en planilla: {len(_s['planilla'])}"
            ).classes("text-sm")

            def _ejecutar_cierre() -> None:
                try:
                    anio_id = _s["anio_id"] or 0
                    ctx_dto = ContextoAcademicoDTO(
                        usuario_id=ctx.usuario_id,
                        anio_id=anio_id,
                        periodo_id=per_id,
                        asignacion_id=asig_id,
                    )
                    resultado = Container.cierre_service().cerrar_periodo(
                        asig_id, per_id, ctx_dto, usuario_id=ctx.usuario_id
                    )
                    _s["resultado"] = resultado
                    ui.notify(
                        f"Periodo cerrado. {len(resultado)} registros generados.",
                        type="positive",
                    )
                    dlg.close()
                    tabla_resultado.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al cerrar periodo: %s", exc)
                    ui.notify("Error al cerrar el periodo", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                ui.button("Cancelar", on_click=dlg.close).props("flat")
                ui.button(
                    "Cerrar periodo",
                    icon="lock",
                    color="negative",
                    on_click=_ejecutar_cierre,
                )

        dlg.open()

    def _on_selector_cambio() -> None:
        _cargar_planilla()
        resumen_planilla.refresh()
        tabla_resultado.refresh()

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def resumen_planilla() -> None:
        planilla = _s["planilla"]
        asig_id = _s["asignacion_id"]
        per_id = _s["periodo_id"]

        if not asig_id or not per_id:
            ui.label("Seleccione periodo y asignación para ver el resumen.").classes(
                "text-sm text-grey-6 mt-2"
            )
            return

        notas_registradas = sum(1 for r in planilla if r.notas)
        with ui.element("div").classes("flex gap-6 items-center flex-wrap mt-2"):
            with ui.element("div").classes("flex-col"):
                ui.label("Estudiantes").classes("text-xs text-grey-6")
                ui.label(str(len(planilla))).classes("text-2xl font-bold")
            with ui.element("div").classes("flex-col"):
                ui.label("Con al menos una nota").classes("text-xs text-grey-6")
                ui.label(str(notas_registradas)).classes("text-2xl font-bold")

    @ui.refreshable
    def tabla_resultado() -> None:
        resultado = _s["resultado"]
        if not resultado:
            return

        ui.label(f"Resultado del cierre — {len(resultado)} registros").classes(
            "text-base font-semibold mb-2"
        )
        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-3 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Estudiante ID").classes("w-32")
                ui.label("Nota definitiva").classes("w-32 text-right")
                ui.label("Fecha cierre").classes("w-36")

            for c in resultado:
                with ui.element("div").classes("flex items-center gap-3 p-2 border-b"):
                    ui.label(str(c.estudiante_id)).classes("w-32 font-mono text-sm")
                    ui.label(f"{c.nota_definitiva:.1f}").classes(
                        "w-32 text-right font-mono font-semibold text-sm"
                    )
                    fecha_str = (
                        c.fecha_cierre.strftime("%d/%m/%Y")
                        if c.fecha_cierre
                        else "—"
                    )
                    ui.label(fecha_str).classes("w-36 text-sm text-grey-7")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ThemeManager.icono(Icons.CLOSE_PERIOD, size=22, color="var(--color-warning)")
                    ui.label("Cierre de Periodo").classes("text-xl font-bold")

                periodos_opts = {p.id: p.nombre for p in _s["periodos"]}
                asigs_opts = {
                    a.asignacion_id: a.display_corto for a in _s["asignaciones"]
                }

                with ui.row().classes("gap-4 items-center flex-wrap"):
                    ui.select(
                        periodos_opts or {"": "Sin periodos"},
                        value=None,
                        label="Periodo *",
                        on_change=lambda e: (
                            _s.__setitem__("periodo_id", e.value),
                            _on_selector_cambio(),
                        ),
                    ).classes("w-48")
                    ui.select(
                        asigs_opts or {"": "Sin asignaciones"},
                        value=None,
                        label="Asignación *",
                        on_change=lambda e: (
                            _s.__setitem__("asignacion_id", e.value),
                            _on_selector_cambio(),
                        ),
                    ).classes("w-64")
                    ui.button(
                        icon="refresh",
                        on_click=lambda: (_cargar_planilla(), resumen_planilla.refresh()),
                    ).props("flat round dense").tooltip("Recargar")

                resumen_planilla()

            # Botón de cierre
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Ejecutar cierre").classes("text-base font-semibold mb-2")
                ui.label(
                    "Al cerrar el periodo se calcularán las notas definitivas para "
                    "todos los estudiantes usando las categorías y actividades registradas."
                ).classes("text-sm text-grey-6 mb-4")
                ui.button(
                    "Cerrar periodo",
                    icon="lock",
                    color="negative",
                    on_click=_abrir_confirmar_cierre,
                )

            # Tabla resultado
            with ui.element("div").classes("panel-card mt-4"):
                tabla_resultado()

    app_layout(
        titulo_pagina="Evaluación · Cierre de Periodo",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/evaluacion/cierre-periodo",
        contenido=contenido,
    )


__all__ = ["cierre_periodo_page"]
