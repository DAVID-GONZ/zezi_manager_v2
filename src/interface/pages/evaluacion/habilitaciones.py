"""
src/interface/pages/evaluacion/habilitaciones.py
================================================
Gestión de habilitaciones (actividades de recuperación).
Ruta: /evaluacion/habilitaciones
Acceso: todos los autenticados

Permite:
 - Listar habilitaciones con filtros por periodo, tipo y estado.
 - Programar nuevas habilitaciones.
 - Registrar la nota cuando el estudiante presenta la habilitación.
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
    TipoHabilitacion,
    EstadoHabilitacion,
    FiltroHabilitacionesDTO,
    NuevaHabilitacionDTO,
    RegistrarNotaHabilitacionDTO,
)
from src.interface.design.components.buttons import btn_primary, btn_ghost, btn_icon
from src.services.asignacion_service import FiltroAsignacionesDTO

logger = logging.getLogger("EVALUACION.HABILITACIONES")

_TIPOS_OPTS = {
    TipoHabilitacion.PERIODO.value: "Por periodo",
    TipoHabilitacion.ANUAL.value: "Anual",
}
_ESTADOS_OPTS = {
    "": "Todos",
    EstadoHabilitacion.PENDIENTE.value: "Pendiente",
    EstadoHabilitacion.REALIZADA.value: "Realizada",
    EstadoHabilitacion.APROBADA.value: "Aprobada",
    EstadoHabilitacion.REPROBADA.value: "Reprobada",
}


@ui.page("/evaluacion/habilitaciones")
def habilitaciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    logger.info("Habilitaciones: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "periodos":        [],
        "asignaciones":    [],
        "habilitaciones":  [],
        "filtro_periodo_id": None,
        "filtro_tipo":       "",
        "filtro_estado":     "",
        # formulario nueva habilitación
        "form_est_id":       "",
        "form_asig_id":      None,
        "form_tipo":         TipoHabilitacion.PERIODO.value,
        "form_periodo_id":   None,
        "form_nota_antes":   None,
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

    def _cargar_habilitaciones() -> None:
        try:
            tipo_val = _s["filtro_tipo"] or None
            estado_val = _s["filtro_estado"] or None
            filtro = FiltroHabilitacionesDTO(
                periodo_id=_s["filtro_periodo_id"] or None,
                tipo=TipoHabilitacion(tipo_val) if tipo_val else None,
                estado=EstadoHabilitacion(estado_val) if estado_val else None,
            )
            _s["habilitaciones"] = Container.habilitacion_service().listar_habilitaciones(
                filtro
            )
        except Exception as exc:
            logger.error("Error cargando habilitaciones: %s", exc)
            _s["habilitaciones"] = []

    _cargar_estado()
    _cargar_habilitaciones()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _programar_habilitacion() -> None:
        est_id_raw = str(_s["form_est_id"]).strip()
        if not est_id_raw.isdigit():
            ui.notify("Ingrese un ID de estudiante válido (número)", type="warning")
            return
        est_id = int(est_id_raw)
        asig_id = _s["form_asig_id"]
        if not asig_id:
            ui.notify("Seleccione una asignación", type="warning")
            return
        tipo_val = _s["form_tipo"]
        per_id = _s["form_periodo_id"] if tipo_val == TipoHabilitacion.PERIODO.value else None

        if tipo_val == TipoHabilitacion.PERIODO.value and not per_id:
            ui.notify("Seleccione el periodo para una habilitación por periodo", type="warning")
            return

        try:
            nota_antes_val = _s["form_nota_antes"]
            nota_antes = float(nota_antes_val) if nota_antes_val is not None else None
            dto = NuevaHabilitacionDTO(
                estudiante_id=est_id,
                asignacion_id=int(asig_id),
                tipo=TipoHabilitacion(tipo_val),
                periodo_id=int(per_id) if per_id else None,
                nota_antes=nota_antes,
            )
            Container.habilitacion_service().programar_habilitacion(dto)
            ui.notify("Habilitación programada", type="positive")
            _s["form_est_id"] = ""
            _s["form_asig_id"] = None
            _s["form_nota_antes"] = None
            _cargar_habilitaciones()
            tabla_habilitaciones.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al programar habilitación: %s", exc)
            ui.notify("Error al programar la habilitación", type="negative")

    def _registrar_nota_dialog(hab) -> None:
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-sm"):
            ui.label(
                f"Registrar nota — Estudiante {hab.estudiante_id}"
            ).classes("text-base font-bold mb-2")
            ui.label(
                f"Tipo: {hab.tipo.value.capitalize()} | Estado: {hab.estado.value}"
            ).classes("text-sm text-grey-6 mb-3")

            nota_inp = ui.number(
                "Nota (0–100)", value=0.0, min=0.0, max=100.0, step=0.5
            ).classes("w-full")
            obs_inp = ui.input("Observación (opcional)").classes("w-full")

            def _guardar_nota() -> None:
                try:
                    dto = RegistrarNotaHabilitacionDTO(
                        nota=float(nota_inp.value or 0.0),
                        usuario_id=ctx.usuario_id,
                        observacion=str(obs_inp.value).strip() or None,
                    )
                    Container.habilitacion_service().registrar_nota_habilitacion(
                        hab.id, dto
                    )
                    ui.notify("Nota registrada", type="positive")
                    dlg.close()
                    _cargar_habilitaciones()
                    tabla_habilitaciones.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al registrar nota habilitación: %s", exc)
                    ui.notify("Error al registrar la nota", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_primary("Registrar nota", on_click=_guardar_nota)

        dlg.open()

    def _on_filtros_cambio() -> None:
        _cargar_habilitaciones()
        tabla_habilitaciones.refresh()

    # ── Sección refreshable ───────────────────────────────────────────────────
    @ui.refreshable
    def tabla_habilitaciones() -> None:
        habs = _s["habilitaciones"]
        asigs_map = {a.asignacion_id: a.asignatura_nombre for a in _s["asignaciones"]}

        if not habs:
            ui.label("No hay habilitaciones con los filtros actuales.").classes(
                "text-empty mt-4"
            )
            return

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-2 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Est. ID").classes("w-20")
                ui.label("Asignatura").classes("flex-1")
                ui.label("Tipo").classes("w-24")
                ui.label("Nota antes").classes("w-24 text-right")
                ui.label("Nota hab.").classes("w-24 text-right")
                ui.label("Estado").classes("w-24 text-center")
                ui.label("Acciones").classes("w-20 text-right")

            for hab in habs:
                asig_nombre = asigs_map.get(hab.asignacion_id, f"Asig. {hab.asignacion_id}")
                estado_val = hab.estado.value
                _ESTADO_CLASES = {
                    "pendiente": "badge-neutral",
                    "realizada": "badge-info",
                    "aprobada": "badge-success",
                    "reprobada": "badge-error",
                }
                with ui.element("div").classes("flex items-center gap-2 p-2 border-b"):
                    ui.label(str(hab.estudiante_id)).classes("w-20 font-mono text-sm")
                    ui.label(asig_nombre).classes("flex-1 text-sm")
                    ui.label(hab.tipo.value.capitalize()).classes("w-24 text-sm")
                    nota_antes_str = f"{hab.nota_antes:.1f}" if hab.nota_antes is not None else "—"
                    ui.label(nota_antes_str).classes("w-24 text-right font-mono text-sm")
                    nota_hab_str = (
                        f"{hab.nota_habilitacion:.1f}"
                        if hab.nota_habilitacion is not None
                        else "—"
                    )
                    ui.label(nota_hab_str).classes("w-24 text-right font-mono text-sm")
                    ui.badge(
                        estado_val.capitalize(),
                    ).classes(f"w-24 text-center {_ESTADO_CLASES.get(estado_val, 'badge-neutral')}")
                    with ui.row().classes("w-20 justify-end"):
                        if hab.estado == EstadoHabilitacion.PENDIENTE:
                            btn_icon(
                                "grade",
                                on_click=lambda h=hab: _registrar_nota_dialog(h),
                                tooltip="Registrar nota",
                            )

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ThemeManager.icono(Icons.GRADES, size=22, color="var(--color-primary)")
                    ui.label("Habilitaciones").classes("text-xl font-bold")

                # Filtros
                periodos_filtro = {None: "Todos los periodos"}
                periodos_filtro.update({p.id: p.nombre for p in _s["periodos"]})
                tipos_filtro = {"": "Todos los tipos"}
                tipos_filtro.update(_TIPOS_OPTS)

                with ui.row().classes("gap-3 items-center flex-wrap mb-4"):
                    ui.label("Filtros:").classes("text-sm font-semibold")
                    ui.select(
                        periodos_filtro,
                        value=None,
                        label="Periodo",
                        on_change=lambda e: (
                            _s.__setitem__("filtro_periodo_id", e.value),
                            _on_filtros_cambio(),
                        ),
                    ).classes("w-40")
                    ui.select(
                        tipos_filtro,
                        value="",
                        label="Tipo",
                        on_change=lambda e: (
                            _s.__setitem__("filtro_tipo", e.value),
                            _on_filtros_cambio(),
                        ),
                    ).classes("w-36")
                    ui.select(
                        _ESTADOS_OPTS,
                        value="",
                        label="Estado",
                        on_change=lambda e: (
                            _s.__setitem__("filtro_estado", e.value),
                            _on_filtros_cambio(),
                        ),
                    ).classes("w-36")
                    ui.badge(str(len(_s["habilitaciones"])), color="primary")
                    btn_icon(
                        "refresh",
                        on_click=lambda: (_cargar_habilitaciones(), tabla_habilitaciones.refresh()),
                        tooltip="Recargar",
                    )

            # Formulario nueva habilitación
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Programar habilitación").classes("text-base font-semibold mb-3")
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
                        _TIPOS_OPTS,
                        value=TipoHabilitacion.PERIODO.value,
                        label="Tipo *",
                        on_change=lambda e: _s.__setitem__("form_tipo", e.value),
                    ).classes("w-36")
                    ui.select(
                        periodos_opts or {"": "Sin periodos"},
                        value=None,
                        label="Periodo (si tipo=Periodo)",
                        on_change=lambda e: _s.__setitem__("form_periodo_id", e.value),
                    ).classes("w-44")
                    ui.number(
                        "Nota anterior (opcional)",
                        value=None,
                        min=0.0,
                        max=100.0,
                        step=0.5,
                    ).classes("w-40").bind_value(_s, "form_nota_antes")
                    btn_primary("Programar", icon="add", on_click=_programar_habilitacion)

            # Tabla
            with ui.element("div").classes("panel-card mt-4"):
                ui.label("Habilitaciones registradas").classes("text-base font-semibold mb-3")
                tabla_habilitaciones()

    def on_context_change() -> None:
        ui.navigate.reload()

    app_layout(
        titulo_pagina="Evaluación · Habilitaciones",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/evaluacion/habilitaciones",
        contenido=contenido,
        ctx=ctx,
        on_context_change=on_context_change,
    )


__all__ = ["habilitaciones_page"]
