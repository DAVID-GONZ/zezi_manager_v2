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
from src.interface.design.components import badge_estado_general, confirm_dialog, form_dialog, toast_error, toast_success, toast_warning
from src.services.asignacion_service import NuevaAsignacionDTO, FiltroAsignacionesDTO

logger = logging.getLogger("ADMIN.ASIGNACIONES")


@ui.page("/admin/asignaciones")
def asignaciones_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director"):
        toast_error("Acceso no autorizado")
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
            toast_warning("No hay docentes disponibles")
            return
        if not grupos_opts:
            toast_warning("No hay grupos disponibles")
            return
        if not asigs_opts:
            toast_warning("No hay asignaturas disponibles")
            return
        if not periodos_opts:
            toast_warning("No hay periodos disponibles para el año activo")
            return

        def _crear(datos: dict) -> "bool | None":
            try:
                if not all([datos.get("usuario_id"), datos.get("grupo_id"),
                            datos.get("asignatura_id"), datos.get("periodo_id")]):
                    toast_warning("Todos los campos son obligatorios")
                    return False
                dto = NuevaAsignacionDTO(
                    usuario_id=datos["usuario_id"],
                    grupo_id=datos["grupo_id"],
                    asignatura_id=datos["asignatura_id"],
                    periodo_id=datos["periodo_id"],
                )
                Container.asignacion_service().crear_asignacion(dto)
                toast_success("Asignación creada")
                _cargar_asignaciones()
                tabla.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al crear asignación: %s", exc)
                toast_error("Error al crear la asignación")
                return False

        form_dialog(
            titulo    = "Nueva asignación",
            campos    = [
                {"key": "usuario_id",    "label": "Docente *",    "tipo": "select",
                 "opciones": docentes_opts, "requerido": True},
                {"key": "grupo_id",      "label": "Grupo *",      "tipo": "select",
                 "opciones": grupos_opts,   "requerido": True},
                {"key": "asignatura_id", "label": "Asignatura *", "tipo": "select",
                 "opciones": asigs_opts,    "requerido": True},
                {"key": "periodo_id",    "label": "Periodo *",    "tipo": "select",
                 "opciones": periodos_opts, "requerido": True},
            ],
            on_submit    = _crear,
            texto_submit = "Crear",
            max_width    = "max-w-lg",
        )

    def _confirmar_desactivar(asig_id: int, label: str) -> None:
        try:
            Container.asignacion_service().desactivar(asig_id)
            toast_success(f"Asignación '{label}' desactivada")
            _cargar_asignaciones()
            tabla.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al desactivar asignación %s: %s", asig_id, exc)
            toast_error("Error al desactivar la asignación")

    def _desactivar_asignacion(asig_id: int, label: str) -> None:
        confirm_dialog(
            titulo          = "Desactivar asignación",
            mensaje         = f"¿Desactivar asignación '{label}'? El histórico de notas y asistencia se conserva.",
            on_confirm      = lambda: _confirmar_desactivar(asig_id, label),
            variante        = "warning",
            texto_confirmar = "Desactivar",
        )

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
                        badge_estado_general(True)
                    else:
                        badge_estado_general(False)
                    with ui.row().classes("w-20 justify-end"):
                        if a.activo:
                            btn_icon("link_off", on_click=lambda aid=a.asignacion_id, lbl=a.display_corto: _desactivar_asignacion(aid, lbl), tooltip="Desactivar", variante="danger")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4 flex-wrap"):
                    btn_primary("Nueva asignación", on_click=_abrir_crear_asignacion, icon="add_link")

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
        ctx,
        contenido,
        page_titulo    = "Asignaciones Docentes",
        page_subtitulo = "Asignación de docentes a grupos y asignaturas por periodo",
        page_icono     = "assignment_ind",
    )


__all__ = ["asignaciones_page"]
