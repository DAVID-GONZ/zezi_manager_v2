"""
src/interface/pages/admin/asignaciones.py
==========================================
Página de administración de asignaciones docente-grupo-asignatura.
Ruta: /admin/asignaciones
Acceso: admin, director

Permite:
 - Listar asignaciones del periodo activo con filtros.
 - Crear nuevas asignaciones.
 - Desactivar asignaciones (soft-delete).
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_danger, btn_ghost, btn_icon
from src.services.asignacion_service import NuevaAsignacionDTO, FiltroAsignacionesDTO

logger = logging.getLogger("ADMIN.ASIGNACIONES")


@ui.page("/admin/asignaciones")
def asignaciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director"):
        ui.notify("Acceso no autorizado", type="negative")
        ui.navigate.to("/inicio")
        return

    logger.info("Asignaciones admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "asignaciones":      [],
        "docentes":          [],
        "grupos":            [],
        "asignaturas":       [],
        "periodos":          [],
        "filtro_docente_id": None,
        "filtro_grupo_id":   None,
        # datos configuración activa
        "anio_id":           None,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_catalogo() -> None:
        try:
            config = Container.configuracion_service().get_activa()
            _s["anio_id"] = config.id if config else None
        except Exception:
            _s["anio_id"] = None

        try:
            _s["docentes"] = Container.usuario_service().listar_docentes()
        except Exception as exc:
            logger.error("Error al cargar docentes: %s", exc)
            _s["docentes"] = []

        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error al cargar grupos: %s", exc)
            _s["grupos"] = []

        try:
            _s["asignaturas"] = Container.infraestructura_service().listar_asignaturas()
        except Exception as exc:
            logger.error("Error al cargar asignaturas: %s", exc)
            _s["asignaturas"] = []

        try:
            anio_id = _s["anio_id"]
            if anio_id:
                _s["periodos"] = Container.periodo_service().listar_por_anio(anio_id)
            else:
                _s["periodos"] = []
        except Exception as exc:
            logger.error("Error al cargar periodos: %s", exc)
            _s["periodos"] = []

    def _cargar_asignaciones() -> None:
        try:
            filtro = FiltroAsignacionesDTO(
                usuario_id=_s["filtro_docente_id"] if _s["filtro_docente_id"] else None,
                grupo_id=_s["filtro_grupo_id"] if _s["filtro_grupo_id"] else None,
                solo_activas=False,
            )
            _s["asignaciones"] = Container.asignacion_service().listar_con_info(filtro)
        except Exception as exc:
            logger.error("Error al cargar asignaciones: %s", exc)
            _s["asignaciones"] = []

    _cargar_catalogo()
    _cargar_asignaciones()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _abrir_crear_asignacion() -> None:
        docentes_opts  = {d.id: d.nombre_completo for d in _s["docentes"]}
        grupos_opts    = {g.id: g.codigo for g in _s["grupos"]}
        asigs_opts     = {a.id: a.nombre for a in _s["asignaturas"]}
        periodos_opts  = {p.id: p.nombre for p in _s["periodos"]}

        if not docentes_opts:
            ui.notify("No hay docentes disponibles", type="warning")
            return
        if not grupos_opts:
            ui.notify("No hay grupos disponibles", type="warning")
            return
        if not asigs_opts:
            ui.notify("No hay asignaturas disponibles", type="warning")
            return
        if not periodos_opts:
            ui.notify("No hay periodos disponibles para el año activo", type="warning")
            return

        with ui.dialog() as dlg, ui.card().classes("w-full max-w-lg"):
            ui.label("Nueva asignación").classes("text-lg font-bold mb-2")

            doc_sel  = ui.select(docentes_opts,  label="Docente *").classes("w-full")
            grp_sel  = ui.select(grupos_opts,    label="Grupo *").classes("w-full")
            asig_sel = ui.select(asigs_opts,     label="Asignatura *").classes("w-full")
            per_sel  = ui.select(periodos_opts,  label="Periodo *").classes("w-full")

            def _crear() -> None:
                try:
                    if not all([doc_sel.value, grp_sel.value, asig_sel.value, per_sel.value]):
                        ui.notify("Todos los campos son obligatorios", type="warning")
                        return
                    dto = NuevaAsignacionDTO(
                        usuario_id=doc_sel.value,
                        grupo_id=grp_sel.value,
                        asignatura_id=asig_sel.value,
                        periodo_id=per_sel.value,
                    )
                    Container.asignacion_service().crear_asignacion(dto)
                    ui.notify("Asignación creada", type="positive")
                    dlg.close()
                    _cargar_asignaciones()
                    tabla.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al crear asignación: %s", exc)
                    ui.notify("Error al crear la asignación", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_primary("Crear", on_click=_crear)

        dlg.open()

    def _desactivar_asignacion(asig_id: int, label: str) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label(
                f"¿Desactivar asignación '{label}'?"
            ).classes("text-base font-medium")
            ui.label(
                "El histórico de notas y asistencia se conserva."
            ).classes("text-sm text-grey-6 mt-1")
            with ui.row().classes("gap-2 mt-4"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_danger(
                    "Desactivar",
                    on_click=lambda: _confirmar_desactivar(dlg, asig_id, label),
                )
        dlg.open()

    def _confirmar_desactivar(dlg, asig_id: int, label: str) -> None:
        try:
            Container.asignacion_service().desactivar(asig_id)
            ui.notify(f"Asignación '{label}' desactivada", type="positive")
            dlg.close()
            _cargar_asignaciones()
            tabla.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al desactivar asignación %s: %s", asig_id, exc)
            ui.notify("Error al desactivar la asignación", type="negative")
            dlg.close()

    def _on_filtros_cambio() -> None:
        _cargar_asignaciones()
        tabla.refresh()

    # ── Sección refreshable ───────────────────────────────────────────────────
    @ui.refreshable
    def tabla() -> None:
        asigs = _s["asignaciones"]
        if not asigs:
            ui.label("No hay asignaciones con los filtros actuales.").classes("text-empty mt-4")
            return

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-3 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Docente").classes("flex-1")
                ui.label("Grupo").classes("w-24")
                ui.label("Asignatura").classes("w-44")
                ui.label("Periodo").classes("w-28")
                ui.label("Estado").classes("w-20")
                ui.label("Acciones").classes("w-20 text-right")

            for a in asigs:
                with ui.element("div").classes("flex items-center gap-3 p-2 border-b"):
                    ui.label(a.docente_nombre).classes("flex-1 text-sm")
                    ui.label(a.grupo_codigo).classes("w-24 font-mono text-sm")
                    ui.label(a.asignatura_nombre).classes("w-44 text-sm")
                    ui.label(a.periodo_nombre).classes("w-28 text-sm")
                    if a.activo:
                        ui.badge("Activa").classes("w-20 badge-success")
                    else:
                        ui.badge("Inactiva").classes("w-20 badge-neutral")
                    with ui.row().classes("w-20 justify-end"):
                        if a.activo:
                            btn_icon("link_off", on_click=lambda aid=a.asignacion_id, lbl=a.display_corto: _desactivar_asignacion(aid, lbl), tooltip="Desactivar", variante="danger")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4 flex-wrap"):
                    ThemeManager.icono(Icons.SCHEDULE, size=22, color="var(--color-primary)")
                    ui.label("Gestión de Asignaciones").classes("text-xl font-bold")
                    btn_primary("Nueva asignación", on_click=_abrir_crear_asignacion, icon="add_link").classes("ml-auto")

                # Filtros
                docentes_filtro = {None: "Todos los docentes"}
                docentes_filtro.update({d.id: d.nombre_completo for d in _s["docentes"]})
                grupos_filtro = {None: "Todos los grupos"}
                grupos_filtro.update({g.id: g.codigo for g in _s["grupos"]})

                with ui.row().classes("gap-4 items-center flex-wrap mb-4"):
                    ui.label("Filtros:").classes("text-sm font-semibold")
                    ui.select(
                        docentes_filtro,
                        value=None,
                        label="Docente",
                        on_change=lambda e: (
                            _s.__setitem__("filtro_docente_id", e.value),
                            _on_filtros_cambio(),
                        ),
                    ).classes("w-56")
                    ui.select(
                        grupos_filtro,
                        value=None,
                        label="Grupo",
                        on_change=lambda e: (
                            _s.__setitem__("filtro_grupo_id", e.value),
                            _on_filtros_cambio(),
                        ),
                    ).classes("w-32")
                    ui.badge(str(len(_s["asignaciones"]))).classes("badge-primary")
                    btn_icon("refresh", on_click=lambda: (_cargar_asignaciones(), tabla.refresh()), tooltip="Recargar")

                tabla()

    app_layout(
        titulo_pagina="Administración · Asignaciones",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/admin/asignaciones",
        contenido=contenido,
        ctx=ctx,
    )


__all__ = ["asignaciones_page"]
