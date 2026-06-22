"""
src/interface/pages/admin/disponibilidad_docente.py
====================================================
Página para gestionar la disponibilidad horaria y límites de carga
de los docentes.
Ruta: /admin/disponibilidad-docente
Acceso: admin, director, coordinador
"""
from __future__ import annotations

import logging
from typing import Any

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.components.buttons import btn_primary, btn_ghost
from src.interface.design.components import (
    empty_state,
    toast_error,
    toast_success,
    toast_warning,
)

logger = logging.getLogger("ADMIN.DISPONIBILIDAD_DOCENTE")


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def disponibilidad_docente_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info(
        "Disponibilidad docente: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol
    )

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict[str, Any] = {
        "docentes":       [],
        "docente_id":     None,
        "franjas":        [],   # franjas lectivas de la plantilla activa
        "dias_activos":   [],
        "disponibilidad": {},   # dict[(dia, orden), bool] — True=disponible
        "min_horas_dia":  0,
        "max_horas_dia":  8,
        "plantilla_ok":   True,
    }

    # ── Carga inicial ─────────────────────────────────────────────────────────
    def _cargar_docentes() -> None:
        try:
            _s["docentes"] = Container.usuario_service().listar_docentes()
        except Exception as exc:
            logger.error("Error cargando docentes: %s", exc)
            _s["docentes"] = []

    def _cargar_plantilla() -> None:
        try:
            plantilla = Container.infraestructura_service().plantilla_activa("UNICA")
            if plantilla is None:
                _s["plantilla_ok"] = False
                _s["franjas"] = []
                _s["dias_activos"] = []
                return
            _s["plantilla_ok"] = True
            _s["dias_activos"] = list(getattr(plantilla, "dias_activos", []) or [])
            franjas_todas = Container.infraestructura_service().listar_franjas(plantilla.id)
            _s["franjas"] = [
                f for f in franjas_todas
                if (f.tipo if isinstance(f.tipo, str) else f.tipo.value) == "lectiva"
            ]
        except Exception as exc:
            logger.error("Error cargando plantilla activa: %s", exc)
            _s["plantilla_ok"] = False
            _s["franjas"] = []
            _s["dias_activos"] = []

    def _cargar_disponibilidad_docente(docente_id: int) -> None:
        try:
            disp_bd = Container.infraestructura_service().listar_disponibilidad_docente(
                docente_id
            )
            disp_dict = {
                (d.dia_semana, d.franja_orden): d.disponible for d in disp_bd
            }
            nueva_disp: dict[tuple, bool] = {}
            for dia in _s["dias_activos"]:
                for franja in _s["franjas"]:
                    clave = (dia, franja.orden)
                    nueva_disp[clave] = disp_dict.get(clave, True)
            _s["disponibilidad"] = nueva_disp
        except Exception as exc:
            logger.error("Error cargando disponibilidad: %s", exc)
            _s["disponibilidad"] = {}

        try:
            limites = Container.infraestructura_service().get_limites_docente(docente_id)
            _s["min_horas_dia"] = limites.min_horas_dia if limites else 0
            _s["max_horas_dia"] = limites.max_horas_dia if limites else 8
        except Exception as exc:
            logger.error("Error cargando límites docente: %s", exc)
            _s["min_horas_dia"] = 0
            _s["max_horas_dia"] = 8

    _cargar_docentes()
    _cargar_plantilla()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _toggle_celda(clave: tuple) -> None:
        _s["disponibilidad"][clave] = not _s["disponibilidad"].get(clave, True)
        _rejilla_disponibilidad.refresh()

    def _marcar_todo_disponible() -> None:
        for clave in _s["disponibilidad"]:
            _s["disponibilidad"][clave] = True
        _rejilla_disponibilidad.refresh()

    def _guardar_disponibilidad() -> None:
        docente_id = _s["docente_id"]
        if not docente_id:
            toast_warning("Selecciona un docente primero")
            return
        try:
            slots_no_disponibles = [
                {"dia_semana": dia, "franja_orden": orden, "disponible": False}
                for (dia, orden), disponible in _s["disponibilidad"].items()
                if not disponible
            ]
            Container.infraestructura_service().guardar_disponibilidad_docente(
                docente_id, slots_no_disponibles
            )
            toast_success("Disponibilidad guardada")
        except Exception as exc:
            logger.error("Error guardando disponibilidad: %s", exc)
            toast_error("Error al guardar la disponibilidad")

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def _rejilla_disponibilidad() -> None:
        if not _s["docente_id"]:
            empty_state(
                titulo="Selecciona un docente",
                descripcion="Elige un docente para ver y editar su disponibilidad horaria.",
            )
            return
        if not _s["franjas"]:
            empty_state(
                titulo="Sin franjas lectivas",
                descripcion="No hay plantilla activa con franjas lectivas configuradas.",
            )
            return

        dias = _s["dias_activos"]
        franjas = sorted(_s["franjas"], key=lambda f: f.orden)

        with ui.element("div").classes("overflow-x-auto"):
            with ui.element("table").classes("w-full border-collapse text-sm"):
                # Header
                with ui.element("thead"):
                    with ui.element("tr"):
                        ui.element("th").classes(
                            "p-2 text-left border font-semibold bg-surface w-24"
                        ).text = "Franja"
                        for dia in dias:
                            th = ui.element("th").classes(
                                "p-2 text-center border font-semibold bg-surface w-28"
                            )
                            with th:
                                ui.label(dia[:3])
                # Body
                with ui.element("tbody"):
                    for franja in franjas:
                        with ui.element("tr"):
                            td_hora = ui.element("td").classes(
                                "p-2 border text-xs text-center font-mono"
                            )
                            with td_hora:
                                ui.label(f"{franja.hora_inicio}–{franja.hora_fin}")
                            for dia in dias:
                                clave = (dia, franja.orden)
                                disponible = _s["disponibilidad"].get(clave, True)
                                estado_cls = (
                                    "slot-disponible" if disponible else "slot-no-disponible"
                                )
                                td = ui.element("td").classes(
                                    f"p-2 border text-center slot-cell {estado_cls}"
                                )
                                td.on("click", lambda _, c=clave: _toggle_celda(c))
                                with td:
                                    ui.label("✓" if disponible else "✗").classes(
                                        "text-xs font-bold"
                                    )

    @ui.refreshable
    def _panel_limites() -> None:
        if not _s["docente_id"]:
            ui.label("Selecciona un docente para ver sus límites.").classes(
                "text-sm text-muted"
            )
            return

        with ui.row().classes("items-end gap-4 flex-wrap"):
            with ui.element("div").classes("flex flex-col gap-1"):
                ui.label("Mín. horas/día").classes("text-sm font-medium")
                in_min = ui.number(
                    value=_s["min_horas_dia"], min=0, max=12, step=1
                ).classes("andes-input w-32").props("outlined")
            with ui.element("div").classes("flex flex-col gap-1"):
                ui.label("Máx. horas/día").classes("text-sm font-medium")
                in_max = ui.number(
                    value=_s["max_horas_dia"], min=1, max=12, step=1
                ).classes("andes-input w-32").props("outlined")

            def _guardar_limites() -> None:
                docente_id = _s["docente_id"]
                if not docente_id:
                    return
                try:
                    min_val = int(in_min.value or 0)
                    max_val = int(in_max.value or 8)
                    Container.infraestructura_service().set_limites_docente_simple(
                        usuario_id=docente_id,
                        min_horas_dia=min_val,
                        max_horas_dia=max_val,
                    )
                    _s["min_horas_dia"] = min_val
                    _s["max_horas_dia"] = max_val
                    toast_success("Límites guardados")
                except ValueError as exc:
                    toast_warning(str(exc))
                except Exception as exc:
                    logger.error("Error guardando límites: %s", exc)
                    toast_error("Error al guardar los límites")

            btn_primary("Guardar límites", icon="save", on_click=_guardar_limites)

    # ── Layout ────────────────────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Panel selector de docente
            with ui.element("div").classes("panel-card"):
                ui.label("Docente").classes("text-sm font-semibold mb-1")
                docente_opts = {d.id: d.nombre_completo for d in _s["docentes"]}

                def _on_select_docente(e) -> None:
                    _s["docente_id"] = e.value
                    if e.value:
                        _cargar_disponibilidad_docente(e.value)
                    _rejilla_disponibilidad.refresh()
                    _panel_limites.refresh()

                ui.select(
                    docente_opts,
                    label="Selecciona un docente",
                    on_change=_on_select_docente,
                    value=_s["docente_id"],
                ).classes("andes-input w-72").props("outlined")

            # Panel rejilla de disponibilidad
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center justify-between mb-3"):
                    ui.label("Disponibilidad horaria").classes("text-lg font-bold")
                    with ui.row().classes("gap-2"):
                        with ui.element("div").classes("flex items-center gap-1"):
                            ui.element("div").classes("slot-legend slot-legend--disponible")
                            ui.label("Disponible").classes("text-xs")
                        with ui.element("div").classes("flex items-center gap-1"):
                            ui.element("div").classes("slot-legend slot-legend--no-disponible")
                            ui.label("No disponible").classes("text-xs")

                _rejilla_disponibilidad()

                with ui.row().classes("gap-2 mt-3"):
                    btn_primary(
                        "Guardar disponibilidad",
                        icon="save",
                        on_click=_guardar_disponibilidad,
                    )
                    btn_ghost(
                        "Marcar todo disponible",
                        icon="done_all",
                        on_click=_marcar_todo_disponible,
                    )

            # Panel de límites
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Límites de carga diaria").classes("text-lg font-bold mb-3")
                _panel_limites()

    app_layout(
        ctx,
        contenido,
        page_titulo="Disponibilidad docente",
        page_subtitulo="Gestión de disponibilidad horaria y límites de carga por docente",
        page_icono="event_available",
        mostrar_contexto=False,
    )


__all__ = ["disponibilidad_docente_page"]
