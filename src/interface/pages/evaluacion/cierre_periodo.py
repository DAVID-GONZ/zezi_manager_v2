"""
src/interface/pages/evaluacion/cierre_periodo.py
=================================================
Cierre de periodo académico por asignación.
Ruta: /evaluacion/cierre-periodo
Acceso: admin, director, coordinador

Lógica:
  - Selector de periodo + grupo → muestra todas las asignaciones del grupo.
  - Por cada asignación: estado (Abierta / Cerrada), promedio del grupo,
    fecha del último cierre, usuario que lo ejecutó.
  - "Cerrar en bloque": cierra todas las asignaciones del grupo a la vez.
  - Por asignación: Cerrar | Recalcular | Abrir (con motivo auditable).
  - "Cerrar" = calcular notas definitivas y guardar CierrePeriodo (UPSERT).
  - "Abrir"  = eliminar CierrePeriodo del grupo para esa asignación, dejando
               al docente volver a editar notas.  Requiere motivo.
"""
from __future__ import annotations

import logging
from statistics import mean

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import (
    btn_primary, btn_danger, btn_ghost, btn_secondary, btn_icon,
)
from src.services.asignacion_service import FiltroAsignacionesDTO
from src.services.cierre_service import ContextoAcademicoDTO

logger = logging.getLogger("EVALUACION.CIERRE_PERIODO")

_ROLES_PERMITIDOS = ("admin", "director", "coordinador")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cargar_asigs_grupo(grupo_id: int, periodo_id: int) -> list:
    """Asignaciones del grupo en el periodo, ordenadas por asignatura."""
    try:
        filtro = FiltroAsignacionesDTO(solo_activas=True)
        todas = Container.asignacion_service().listar_con_info(filtro)
        return sorted(
            [a for a in todas if a.grupo_id == grupo_id and a.periodo_id == periodo_id],
            key=lambda a: a.asignatura_nombre,
        )
    except Exception as exc:
        logger.error("Error cargando asignaciones: %s", exc)
        return []


def _estado_cierres(_s: dict) -> None:
    """Carga el estado de cierres para las asignaciones actuales."""
    asigs = _s.get("asignaciones", [])
    if not asigs or not _s.get("periodo_id"):
        _s["estado_cierres"] = {}
        return
    ids = [a.asignacion_id for a in asigs]
    try:
        _s["estado_cierres"] = Container.cierre_service().estado_cierres_por_asignaciones(
            ids, _s["periodo_id"]
        )
    except Exception as exc:
        logger.error("Error cargando estado cierres: %s", exc)
        _s["estado_cierres"] = {}


def _nombre_usuario(usuario_id: int | None) -> str:
    if not usuario_id:
        return "—"
    try:
        u = Container.usuario_service().get_by_id(usuario_id)
        return u.nombre if u else f"#{usuario_id}"
    except Exception:
        return f"#{usuario_id}"


# ── Página ────────────────────────────────────────────────────────────────────

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

    # ── Estado mutable ────────────────────────────────────────────────────
    _s: dict = {
        "anio_id":       None,
        "periodos":      [],
        "grupos":        [],
        "periodo_id":    ctx.periodo_id,
        "grupo_id":      ctx.grupo_id,
        "asignaciones":  [],
        "estado_cierres": {},   # asignacion_id → list[CierrePeriodo]
    }

    # ── Carga inicial ─────────────────────────────────────────────────────
    def _cargar_listas() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            _s["anio_id"] = config.id if config else None
            if _s["anio_id"]:
                _s["periodos"] = Container.periodo_service().listar_por_anio(_s["anio_id"])
        except Exception as exc:
            logger.error("Error cargando periodos: %s", exc)
            _s["periodos"] = []

        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error cargando grupos: %s", exc)
            _s["grupos"] = []

    def _recargar_asignaciones() -> None:
        if _s["grupo_id"] and _s["periodo_id"]:
            _s["asignaciones"] = _cargar_asigs_grupo(_s["grupo_id"], _s["periodo_id"])
        else:
            _s["asignaciones"] = []
        _estado_cierres(_s)

    _cargar_listas()
    _recargar_asignaciones()

    # ── Acciones ──────────────────────────────────────────────────────────

    def _ejecutar_cierre_asig(asig_id: int) -> None:
        """Cierra o recalcula UNA asignación."""
        grupo_id   = _s["grupo_id"]
        periodo_id = _s["periodo_id"]
        anio_id    = _s["anio_id"] or 0
        if not grupo_id or not periodo_id:
            ui.notify("Selecciona periodo y grupo primero.", type="warning")
            return
        try:
            ctx_dto = ContextoAcademicoDTO(
                usuario_id    = ctx.usuario_id,
                anio_id       = anio_id,
                periodo_id    = periodo_id,
                grupo_id      = grupo_id,
                asignacion_id = asig_id,
            )
            cierres = Container.cierre_service().cerrar_periodo(
                asig_id, periodo_id, ctx_dto, usuario_id=ctx.usuario_id
            )
            ui.notify(f"Definitivas calculadas: {len(cierres)} estudiantes.", type="positive")
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error cerrando asignación %s: %s", asig_id, exc)
            ui.notify("Error al cerrar. Revisa el log.", type="negative")
        _estado_cierres(_s)
        lista_refreshable.refresh()

    def _abrir_dialog_cierre(asig_id: int, nombre: str, ya_cerrado: bool) -> None:
        asigs_count = sum(
            1 for a in _s["asignaciones"]
            if _s["estado_cierres"].get(a.asignacion_id)
        )
        accion = "Recalcular definitivas" if ya_cerrado else "Cerrar periodo"

        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ThemeManager.icono(Icons.WARNING, size=22, color="var(--color-warning)")
                ui.label(f"{accion}").classes("text-lg font-bold")
            ui.label(f"Asignatura: {nombre}").classes("text-sm font-semibold mb-1")
            if ya_cerrado:
                ui.label(
                    "Esta asignación ya tiene definitivas calculadas. "
                    "Recalcular reemplazará los valores anteriores con las notas actuales."
                ).classes("text-sm text-grey-7 mb-3")
            else:
                ui.label(
                    "Se calcularán las notas definitivas para todos los estudiantes "
                    "del grupo usando las categorías y actividades registradas."
                ).classes("text-sm text-grey-7 mb-3")
            ui.label("Esta operación queda auditada.").classes("text-xs text-grey-6 mb-4")

            with ui.row().classes("gap-2 justify-end"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_danger(
                    accion,
                    icon="lock",
                    on_click=lambda: (_ejecutar_cierre_asig(asig_id), dlg.close()),
                )
        dlg.open()

    def _abrir_dialog_reabrir(asig_id: int, nombre: str) -> None:
        motivo_ref = {"v": ""}

        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ThemeManager.icono("lock_open", size=22, color="var(--color-info)")
                ui.label("Reabrir asignación").classes("text-lg font-bold")
            ui.label(f"Asignatura: {nombre}").classes("text-sm font-semibold mb-1")
            ui.label(
                "Esto eliminará los registros de cierre y permitirá al docente "
                "modificar las notas nuevamente. Deberás volver a cerrar la asignación "
                "para generar las definitivas oficiales."
            ).classes("text-sm text-grey-7 mb-3")
            ui.input(
                label="Motivo de la reapertura *",
                placeholder="Ej: corrección de nota de actividad 3",
                on_change=lambda e: motivo_ref.__setitem__("v", e.value),
            ).classes("w-full mb-4")

            def _confirmar_reabrir() -> None:
                if not motivo_ref["v"].strip():
                    ui.notify("El motivo es obligatorio.", type="warning")
                    return
                try:
                    n = Container.cierre_service().reabrir_asignacion(
                        asig_id, _s["periodo_id"], ctx.usuario_id, motivo_ref["v"].strip()
                    )
                    ui.notify(
                        f"Asignación reabierta. {n} registro(s) eliminado(s).",
                        type="positive",
                    )
                    dlg.close()
                except Exception as exc:
                    logger.error("Error reabriendo asignación %s: %s", asig_id, exc)
                    ui.notify("Error al reabrir.", type="negative")
                _estado_cierres(_s)
                lista_refreshable.refresh()

            with ui.row().classes("gap-2 justify-end"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_secondary("Reabrir", icon="lock_open", on_click=_confirmar_reabrir)
        dlg.open()

    def _abrir_dialog_bloque() -> None:
        asigs = _s["asignaciones"]
        if not asigs:
            ui.notify("No hay asignaciones para cerrar.", type="warning")
            return

        ya_cerradas = sum(
            1 for a in asigs if _s["estado_cierres"].get(a.asignacion_id)
        )
        abiertas    = len(asigs) - ya_cerradas

        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ThemeManager.icono("lock_clock", size=22, color="var(--color-warning)")
                ui.label("Cerrar en bloque").classes("text-lg font-bold")

            with ui.element("div").classes("flex gap-6 mb-4"):
                with ui.element("div").classes("flex-col items-center"):
                    ui.label(str(len(asigs))).classes("text-2xl font-bold")
                    ui.label("Asignaturas totales").classes("text-xs text-grey-6")
                with ui.element("div").classes("flex-col items-center"):
                    ui.label(str(abiertas)).classes("text-2xl font-bold text-green-700")
                    ui.label("Se calcularán").classes("text-xs text-grey-6")
                with ui.element("div").classes("flex-col items-center"):
                    ui.label(str(ya_cerradas)).classes("text-2xl font-bold text-orange-600")
                    ui.label("Se recalcularán").classes("text-xs text-grey-6")

            ui.label(
                "Las asignaciones ya cerradas serán recalculadas con las notas actuales. "
                "La operación queda auditada por asignatura."
            ).classes("text-sm text-grey-7 mb-4")

            def _ejecutar_bloque() -> None:
                ids    = [a.asignacion_id for a in asigs]
                gid    = _s["grupo_id"]
                pid    = _s["periodo_id"]
                anio   = _s["anio_id"] or 0
                ctx_dto = ContextoAcademicoDTO(
                    usuario_id = ctx.usuario_id,
                    anio_id    = anio,
                    periodo_id = pid,
                    grupo_id   = gid,
                )
                try:
                    res = Container.cierre_service().cerrar_grupo(
                        ids, gid, pid, ctx_dto, usuario_id=ctx.usuario_id
                    )
                    ok  = sum(1 for v in res.values() if isinstance(v, list))
                    err = len(res) - ok
                    msg = f"Cierre en bloque: {ok} asignaciones cerradas."
                    if err:
                        msg += f" {err} con error (ver log)."
                    ui.notify(msg, type="positive" if not err else "warning")
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error cierre en bloque: %s", exc)
                    ui.notify("Error en el cierre en bloque.", type="negative")
                _estado_cierres(_s)
                lista_refreshable.refresh()
                dlg.close()

            with ui.row().classes("gap-2 justify-end"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_danger(
                    f"Cerrar {len(asigs)} asignaturas",
                    icon="lock",
                    on_click=_ejecutar_bloque,
                )
        dlg.open()

    # ── Refreshables ──────────────────────────────────────────────────────

    @ui.refreshable
    def lista_refreshable() -> None:
        """Lista de asignaciones con su estado de cierre."""
        asigs = _s.get("asignaciones", [])
        estado = _s.get("estado_cierres", {})

        if not _s["grupo_id"] or not _s["periodo_id"]:
            with ui.element("div").classes("tablero-empty"):
                ThemeManager.icono("filter_list", size=40)
                ui.label("Selecciona un periodo y un grupo para continuar.").classes(
                    "tablero-empty-hint"
                )
            return

        if not asigs:
            with ui.element("div").classes("tablero-empty"):
                ui.label("Sin asignaciones activas para este grupo y periodo.").classes(
                    "tablero-empty-hint"
                )
            return

        # Botón de cierre en bloque
        cerradas = sum(1 for a in asigs if estado.get(a.asignacion_id))
        with ui.row().classes("items-center justify-between mb-4 flex-wrap gap-2"):
            ui.label(
                f"{len(asigs)} asignaturas · {cerradas} cerradas · "
                f"{len(asigs) - cerradas} abiertas"
            ).classes("text-sm text-grey-7")
            btn_danger(
                "Cerrar en bloque",
                icon="lock_clock",
                on_click=_abrir_dialog_bloque,
            )

        # Tarjeta por asignación
        for asig in asigs:
            cierres = estado.get(asig.asignacion_id, [])
            cerrado = bool(cierres)

            with ui.element("div").classes(
                "panel-card mb-3" + (" border-l-4 border-green-500" if cerrado else " border-l-4 border-grey-300")
            ):
                with ui.row().classes("items-start justify-between flex-wrap gap-2"):

                    # Columna izquierda: info
                    with ui.element("div").classes("flex-1 min-w-0"):
                        with ui.row().classes("items-center gap-2 mb-1"):
                            if cerrado:
                                ThemeManager.icono("lock", size=18, color="var(--color-success)")
                                ui.label("CERRADA").classes("text-xs font-bold text-green-700")
                            else:
                                ThemeManager.icono("lock_open", size=18, color="var(--color-text-secondary)")
                                ui.label("ABIERTA").classes("text-xs font-bold text-grey-6")

                        ui.label(asig.asignatura_nombre).classes("text-base font-semibold")
                        ui.label(f"Docente: {asig.docente_nombre}").classes("text-sm text-grey-7")

                        if cerrado:
                            promedios = [c.nota_definitiva for c in cierres]
                            prom = round(mean(promedios), 1) if promedios else 0.0
                            fecha_str = (
                                cierres[0].fecha_cierre.strftime("%d/%m/%Y")
                                if cierres[0].fecha_cierre else "—"
                            )
                            usr_str = _nombre_usuario(cierres[0].usuario_cierre_id)

                            with ui.row().classes("gap-4 mt-2 flex-wrap"):
                                with ui.element("div").classes("flex-col"):
                                    ui.label("Promedio del grupo").classes("text-xs text-grey-6")
                                    ui.label(f"{prom:.1f}").classes("text-xl font-bold")
                                with ui.element("div").classes("flex-col"):
                                    ui.label("Estudiantes").classes("text-xs text-grey-6")
                                    ui.label(str(len(cierres))).classes("text-xl font-bold")
                                with ui.element("div").classes("flex-col"):
                                    ui.label("Fecha cierre").classes("text-xs text-grey-6")
                                    ui.label(fecha_str).classes("text-sm")
                                with ui.element("div").classes("flex-col"):
                                    ui.label("Cerrado por").classes("text-xs text-grey-6")
                                    ui.label(usr_str).classes("text-sm")

                    # Columna derecha: acciones
                    with ui.element("div").classes("flex gap-2 items-center flex-shrink-0"):
                        if cerrado:
                            btn_secondary(
                                "Recalcular",
                                icon="refresh",
                                on_click=lambda _, aid=asig.asignacion_id, nom=asig.asignatura_nombre: (
                                    _abrir_dialog_cierre(aid, nom, True)
                                ),
                            )
                            btn_ghost(
                                "Abrir",
                                on_click=lambda _, aid=asig.asignacion_id, nom=asig.asignatura_nombre: (
                                    _abrir_dialog_reabrir(aid, nom)
                                ),
                            )
                        else:
                            btn_danger(
                                "Cerrar",
                                icon="lock",
                                on_click=lambda _, aid=asig.asignacion_id, nom=asig.asignatura_nombre: (
                                    _abrir_dialog_cierre(aid, nom, False)
                                ),
                            )

    # ── Contenido principal ───────────────────────────────────────────────

    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Panel de selección
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ThemeManager.icono(Icons.CLOSE_PERIOD, size=22, color="var(--color-warning)")
                    ui.label("Cierre de Periodo por Asignación").classes("text-xl font-bold")

                periodos_opts = {p.id: p.nombre for p in _s["periodos"]}
                grupos_opts   = {g.id: g.codigo for g in _s["grupos"] if g.id}

                def _on_periodo(v):
                    _s["periodo_id"] = v
                    _recargar_asignaciones()
                    lista_refreshable.refresh()

                def _on_grupo(v):
                    _s["grupo_id"] = v
                    _recargar_asignaciones()
                    lista_refreshable.refresh()

                with ui.row().classes("gap-4 items-center flex-wrap"):
                    ui.select(
                        periodos_opts or {"": "Sin periodos"},
                        value=_s["periodo_id"],
                        label="Periodo *",
                        on_change=lambda e: _on_periodo(e.value),
                    ).classes("w-44").props("outlined dense")

                    ui.select(
                        grupos_opts or {"": "Sin grupos"},
                        value=_s["grupo_id"],
                        label="Grupo *",
                        on_change=lambda e: _on_grupo(e.value),
                    ).classes("w-36").props("outlined dense")

                    btn_icon(
                        "refresh",
                        on_click=lambda: (_recargar_asignaciones(), lista_refreshable.refresh()),
                        tooltip="Recargar",
                    )

            # Lista de asignaciones
            with ui.element("div").classes("panel-card"):
                lista_refreshable()

    def on_context_change() -> None:
        nuevo = SessionContext.desde_storage()
        if nuevo:
            _s["periodo_id"] = nuevo.periodo_id
            _s["grupo_id"]   = nuevo.grupo_id
            _recargar_asignaciones()
        lista_refreshable.refresh()

    app_layout(
        titulo_pagina     = "Evaluación · Cierre de Periodo",
        usuario_nombre    = ctx.usuario_nombre,
        usuario_rol       = ctx.usuario_rol,
        ruta_activa       = "/evaluacion/cierre-periodo",
        contenido         = contenido,
        ctx               = ctx,
        on_context_change = on_context_change,
    )


__all__ = ["cierre_periodo_page"]
