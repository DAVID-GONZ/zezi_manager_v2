"""
src/interface/pages/evaluacion/planes_mejoramiento.py
======================================================
Gestión de planes de mejoramiento académico.
Ruta: /evaluacion/planes
Acceso: todos los autenticados

Permite:
 - Buscar planes de mejoramiento por estudiante.
 - Crear nuevos planes.
 - Cerrar planes (cumplido/incumplido) con observación.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.services.habilitacion_service import (
    EstadoPlanMejoramiento,
    NuevoPlanMejoramientoDTO,
    CerrarPlanMejoramientoDTO,
)
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("EVALUACION.PLANES")

_ESTADOS_CIERRE = {
    EstadoPlanMejoramiento.CUMPLIDO.value: "Cumplido",
    EstadoPlanMejoramiento.INCUMPLIDO.value: "Incumplido",
}


@ui.page("/evaluacion/planes")
def planes_mejoramiento_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Planes mejoramiento: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "periodos":       [],
        "asignaciones":   [],
        "planes":         [],
        "buscar_est_id":  "",
        # formulario nuevo plan
        "form_est_id":          "",
        "form_asig_id":         None,
        "form_periodo_id":      None,
        "form_descripcion":     "",
        "form_actividades":     "",
        "form_fecha_seguimiento": None,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            anio_id = config.id if config else None
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

    def _buscar_planes() -> None:
        est_id_raw = str(_s["buscar_est_id"]).strip()
        if not est_id_raw.isdigit():
            ui.notify("Ingrese un ID de estudiante válido (número)", type="warning")
            _s["planes"] = []
            tabla_planes.refresh()
            return
        try:
            _s["planes"] = Container.habilitacion_service().listar_planes_por_estudiante(
                int(est_id_raw)
            )
            tabla_planes.refresh()
        except Exception as exc:
            logger.error("Error buscando planes: %s", exc)
            ui.notify("Error al buscar planes", type="negative")
            _s["planes"] = []
            tabla_planes.refresh()

    _cargar_estado()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _crear_plan() -> None:
        est_id_raw = str(_s["form_est_id"]).strip()
        if not est_id_raw.isdigit():
            ui.notify("Ingrese un ID de estudiante válido", type="warning")
            return
        asig_id = _s["form_asig_id"]
        if not asig_id:
            ui.notify("Seleccione una asignación", type="warning")
            return
        per_id = _s["form_periodo_id"]
        if not per_id:
            ui.notify("Seleccione un periodo", type="warning")
            return
        descripcion = str(_s["form_descripcion"]).strip()
        if not descripcion:
            ui.notify("La descripción de dificultad no puede estar vacía", type="warning")
            return
        actividades = str(_s["form_actividades"]).strip()
        if not actividades:
            ui.notify("Las actividades propuestas no pueden estar vacías", type="warning")
            return

        try:
            dto = NuevoPlanMejoramientoDTO(
                estudiante_id=int(est_id_raw),
                asignacion_id=int(asig_id),
                periodo_id=int(per_id),
                descripcion_dificultad=descripcion,
                actividades_propuestas=actividades,
                fecha_seguimiento=_s["form_fecha_seguimiento"] or None,
            )
            Container.habilitacion_service().crear_plan(dto)
            ui.notify("Plan de mejoramiento creado", type="positive")
            # Limpiar formulario
            _s["form_est_id"] = ""
            _s["form_asig_id"] = None
            _s["form_periodo_id"] = None
            _s["form_descripcion"] = ""
            _s["form_actividades"] = ""
            _s["form_fecha_seguimiento"] = None
            # Si se buscaba el mismo estudiante, refrescar
            if str(est_id_raw) == str(_s["buscar_est_id"]).strip():
                _buscar_planes()
            else:
                tabla_planes.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al crear plan: %s", exc)
            ui.notify("Error al crear el plan de mejoramiento", type="negative")

    def _cerrar_plan_dialog(plan) -> None:
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            ui.label("Cerrar plan de mejoramiento").classes("text-lg font-bold mb-2")
            ui.label(
                f"Estudiante: {plan.estudiante_id} — Iniciado: {plan.fecha_inicio}"
            ).classes("text-sm text-grey-6 mb-3")

            estado_sel = ui.select(
                _ESTADOS_CIERRE,
                value=EstadoPlanMejoramiento.CUMPLIDO.value,
                label="Estado de cierre *",
            ).classes("w-full")
            obs_inp = ui.textarea(
                "Observación de cierre *",
                placeholder="Describa el resultado del plan...",
            ).classes("w-full")

            def _guardar_cierre() -> None:
                obs = str(obs_inp.value).strip()
                if not obs:
                    ui.notify("La observación es obligatoria", type="warning")
                    return
                try:
                    dto = CerrarPlanMejoramientoDTO(
                        estado=EstadoPlanMejoramiento(estado_sel.value),
                        observacion=obs,
                    )
                    Container.habilitacion_service().cerrar_plan(plan.id, dto)
                    ui.notify("Plan cerrado", type="positive")
                    dlg.close()
                    # Refrescar si aplica
                    est_id_raw = str(_s["buscar_est_id"]).strip()
                    if est_id_raw.isdigit() and int(est_id_raw) == plan.estudiante_id:
                        _buscar_planes()
                    else:
                        tabla_planes.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al cerrar plan: %s", exc)
                    ui.notify("Error al cerrar el plan", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                ui.button("Cancelar", on_click=dlg.close).props("flat")
                ui.button("Cerrar plan", on_click=_guardar_cierre, color="primary")

        dlg.open()

    # ── Sección refreshable ───────────────────────────────────────────────────
    @ui.refreshable
    def tabla_planes() -> None:
        planes = _s["planes"]
        if not planes:
            est_id_raw = str(_s["buscar_est_id"]).strip()
            if est_id_raw.isdigit():
                ui.label(
                    f"No hay planes para el estudiante {est_id_raw}."
                ).classes("text-empty mt-4")
            else:
                ui.label("Ingrese un ID y haga click en 'Buscar' para ver los planes.").classes(
                    "text-empty mt-4"
                )
            return

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-2 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Dificultad").classes("flex-1")
                ui.label("Actividades").classes("flex-1")
                ui.label("Inicio").classes("w-28")
                ui.label("Estado").classes("w-24 text-center")
                ui.label("Acciones").classes("w-20 text-right")

            for plan in planes:
                estado_val = plan.estado.value
                _ESTADO_CLASES = {
                    "activo":     "badge-info",
                    "cumplido":   "badge-success",
                    "incumplido": "badge-error",
                }
                with ui.element("div").classes("flex items-start gap-2 p-2 border-b"):
                    ui.label(plan.descripcion_dificultad[:80] + (
                        "..." if len(plan.descripcion_dificultad) > 80 else ""
                    )).classes("flex-1 text-sm")
                    ui.label(plan.actividades_propuestas[:60] + (
                        "..." if len(plan.actividades_propuestas) > 60 else ""
                    )).classes("flex-1 text-sm text-grey-7")
                    ui.label(plan.fecha_inicio.strftime("%d/%m/%Y")).classes("w-28 text-sm")
                    ui.badge(
                        estado_val.capitalize(),
                    ).classes(f"w-24 text-center {_ESTADO_CLASES.get(estado_val, 'badge-neutral')}")
                    with ui.row().classes("w-20 justify-end"):
                        if plan.esta_activo:
                            ui.button(
                                icon="lock",
                                color="warning",
                                on_click=lambda p=plan: _cerrar_plan_dialog(p),
                            ).props("flat round dense").tooltip("Cerrar plan")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Búsqueda de planes
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                    ui.label("Planes de Mejoramiento").classes("text-xl font-bold")

                with ui.row().classes("gap-3 items-end"):
                    ui.input(
                        "ID Estudiante",
                        placeholder="Ej: 1023",
                    ).classes("w-40").bind_value(_s, "buscar_est_id")
                    ui.button(
                        "Buscar",
                        icon="search",
                        on_click=_buscar_planes,
                        color="primary",
                    )
                    ui.badge(str(len(_s["planes"])), color="primary")

            # Tabla de planes
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Planes encontrados").classes("text-base font-semibold mb-3")
                tabla_planes()

            # Formulario nuevo plan
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Crear nuevo plan").classes("text-base font-semibold mb-3")
                asigs_opts = {
                    a.asignacion_id: a.display_corto for a in _s["asignaciones"]
                }
                periodos_opts = {p.id: p.nombre for p in _s["periodos"]}

                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input(
                        "ID Estudiante *",
                        placeholder="Ej: 1023",
                    ).classes("w-32").bind_value(_s, "form_est_id")
                    ui.select(
                        asigs_opts or {"": "Sin asignaciones"},
                        value=None,
                        label="Asignación *",
                        on_change=lambda e: _s.__setitem__("form_asig_id", e.value),
                    ).classes("w-60")
                    ui.select(
                        periodos_opts or {"": "Sin periodos"},
                        value=None,
                        label="Periodo *",
                        on_change=lambda e: _s.__setitem__("form_periodo_id", e.value),
                    ).classes("w-44")

                with ui.row().classes("gap-3 mt-3 flex-wrap"):
                    ui.textarea(
                        "Descripción de dificultad *",
                        placeholder="Describa las dificultades del estudiante...",
                    ).classes("flex-1 min-w-60").bind_value(_s, "form_descripcion")
                    ui.textarea(
                        "Actividades propuestas *",
                        placeholder="Liste las actividades de mejoramiento...",
                    ).classes("flex-1 min-w-60").bind_value(_s, "form_actividades")

                with ui.row().classes("gap-3 mt-3 items-end"):
                    ui.input(
                        "Fecha seguimiento (opcional)",
                        placeholder="YYYY-MM-DD",
                    ).classes("w-44").bind_value(_s, "form_fecha_seguimiento")
                    ui.button(
                        "Crear plan",
                        icon="add",
                        on_click=_crear_plan,
                        color="primary",
                    )

    app_layout(
        titulo_pagina="Evaluación · Planes de Mejoramiento",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/evaluacion/planes",
        contenido=contenido,
    )


__all__ = ["planes_mejoramiento_page"]
