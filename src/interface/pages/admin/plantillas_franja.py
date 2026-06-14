"""
src/interface/pages/admin/plantillas_franja.py
===============================================
Página de administración de plantillas de franja horaria.
Ruta: /admin/plantillas-franja
Acceso: admin, director

Permite:
 - CRUD de plantillas de franja horaria.
 - Gestión de franjas dentro de una plantilla seleccionada.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_danger, btn_ghost
from src.interface.design.components import (
    confirm_dialog, empty_state, toast_error, toast_success, toast_warning
)

logger = logging.getLogger("ADMIN.PLANTILLAS_FRANJA")

DIAS_VALIDOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]

JORNADA_OPTS = {"UNICA": "Única", "AM": "Mañana", "PM": "Tarde"}
TIPO_FRANJA_OPTS = {"lectiva": "Lectiva", "descanso": "Descanso", "almuerzo": "Almuerzo"}


@ui.page("/admin/plantillas-franja")
def plantillas_franja_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director"):
        toast_error("Acceso no autorizado")
        ui.navigate.to("/inicio")
        return

    logger.info("Plantillas franja admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "plantillas":    [],   # list[PlantillaFranja]
        "plantilla_sel": None, # PlantillaFranja seleccionada
        "franjas":       [],   # list[Franja] de la plantilla seleccionada
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_plantillas() -> None:
        try:
            _s["plantillas"] = Container.infraestructura_service().listar_plantillas()
        except Exception as exc:
            logger.error("Error cargando plantillas: %s", exc)
            _s["plantillas"] = []

    def _cargar_franjas() -> None:
        p = _s["plantilla_sel"]
        if p is None:
            _s["franjas"] = []
            return
        try:
            _s["franjas"] = Container.infraestructura_service().listar_franjas(p.id)
        except Exception as exc:
            logger.error("Error cargando franjas: %s", exc)
            _s["franjas"] = []

    _cargar_plantillas()

    # ── CRUD Plantillas ───────────────────────────────────────────────────────
    def _dialogo_plantilla(plantilla=None) -> None:
        es_edicion = plantilla is not None

        ini_nombre = plantilla.nombre if es_edicion else ""
        ini_jornada = (plantilla.jornada.value if hasattr(plantilla.jornada, "value") else str(plantilla.jornada)) if es_edicion else "UNICA"
        ini_dias = list(plantilla.dias_activos) if es_edicion and plantilla.dias_activos else []

        with ui.dialog() as dlg, ui.card().classes("andes-card form-dialog-card max-w-md"):
            titulo = "Editar plantilla" if es_edicion else "Nueva plantilla"
            ui.label(titulo).classes("font-h3 form-dialog-title")

            in_nombre = ui.input(
                "Nombre *",
                placeholder="Ej: Plantilla Jornada Mañana",
                value=ini_nombre,
            ).classes("w-full")

            sel_jornada = ui.select(
                list(JORNADA_OPTS.keys()),
                label="Jornada",
                value=ini_jornada,
            ).classes("w-full")

            sel_dias = ui.select(
                DIAS_VALIDOS,
                label="Días activos",
                value=ini_dias,
                multiple=True,
            ).classes("w-full")

            def _guardar() -> None:
                nombre = str(in_nombre.value or "").strip()
                jornada = sel_jornada.value or "UNICA"
                dias = list(sel_dias.value or [])

                if not nombre:
                    toast_warning("El nombre de la plantilla no puede estar vacío")
                    return

                try:
                    if es_edicion:
                        toast_warning("La edición directa no está soportada. Elimina y crea de nuevo.")
                        dlg.close()
                        return
                    Container.infraestructura_service().crear_plantilla_simple(nombre, jornada, dias)
                    toast_success(f"Plantilla '{nombre}' creada")
                    _cargar_plantillas()
                    contenido_refreshable.refresh()
                    dlg.close()
                except ValueError as exc:
                    toast_warning(str(exc))
                except Exception as exc:
                    logger.error("Error al guardar plantilla: %s", exc)
                    toast_error("Error al guardar la plantilla")

            with ui.row().classes("gap-2 justify-end mt-4"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_primary("Guardar", on_click=_guardar, icon="save")

        dlg.open()

    def _activar_plantilla(plantilla_id: int, nombre: str) -> None:
        try:
            Container.infraestructura_service().activar_plantilla(plantilla_id)
            toast_success(f"Plantilla '{nombre}' activada")
            _cargar_plantillas()
            contenido_refreshable.refresh()
        except Exception as exc:
            logger.error("Error al activar plantilla %s: %s", plantilla_id, exc)
            toast_error("Error al activar la plantilla")

    def _confirmar_eliminar_plantilla(plantilla_id: int, nombre: str) -> None:
        try:
            Container.infraestructura_service().eliminar_plantilla(plantilla_id)
            toast_success(f"Plantilla '{nombre}' eliminada")
            if _s["plantilla_sel"] and _s["plantilla_sel"].id == plantilla_id:
                _s["plantilla_sel"] = None
                _s["franjas"] = []
            _cargar_plantillas()
            contenido_refreshable.refresh()
        except Exception as exc:
            logger.error("Error al eliminar plantilla %s: %s", plantilla_id, exc)
            toast_error("Error al eliminar la plantilla")

    def _eliminar_plantilla(plantilla_id: int, nombre: str) -> None:
        confirm_dialog(
            titulo="Eliminar plantilla",
            mensaje=f"¿Eliminar la plantilla '{nombre}'? Esta acción eliminará también sus franjas.",
            on_confirm=lambda: _confirmar_eliminar_plantilla(plantilla_id, nombre),
            variante="danger",
            texto_confirmar="Eliminar",
        )

    def _seleccionar_plantilla(plantilla) -> None:
        _s["plantilla_sel"] = plantilla
        _cargar_franjas()
        contenido_refreshable.refresh()

    # ── CRUD Franjas ──────────────────────────────────────────────────────────
    def _dialogo_franja(franja_orden: int | None = None) -> None:
        """Abre el diálogo para crear (franja_orden=None) o editar una franja existente."""
        p = _s["plantilla_sel"]
        if p is None:
            toast_warning("Selecciona una plantilla primero")
            return

        es_edicion = franja_orden is not None
        franja_existente = None
        if es_edicion:
            franja_existente = next((f for f in _s["franjas"] if f.orden == franja_orden), None)

        ini_hora_inicio = getattr(franja_existente, "hora_inicio", "") if es_edicion else ""
        ini_hora_fin    = getattr(franja_existente, "hora_fin", "") if es_edicion else ""
        ini_tipo_raw    = getattr(franja_existente, "tipo", "lectiva") if es_edicion else "lectiva"
        ini_tipo        = ini_tipo_raw if isinstance(ini_tipo_raw, str) else ini_tipo_raw.value
        ini_etiqueta    = getattr(franja_existente, "etiqueta", "") or "" if es_edicion else ""

        with ui.dialog() as dlg, ui.card().classes("andes-card form-dialog-card max-w-sm"):
            titulo = "Editar franja" if es_edicion else "Añadir franja"
            ui.label(titulo).classes("font-h3 form-dialog-title")

            in_inicio = ui.input(
                "Hora inicio *", placeholder="07:00", value=ini_hora_inicio,
            ).classes("w-full")

            in_fin = ui.input(
                "Hora fin *", placeholder="07:50", value=ini_hora_fin,
            ).classes("w-full")

            sel_tipo = ui.select(
                list(TIPO_FRANJA_OPTS.keys()),
                label="Tipo",
                value=ini_tipo,
            ).classes("w-full")

            in_etiqueta = ui.input(
                "Etiqueta (opcional)", placeholder="Ej: Período 1", value=ini_etiqueta,
            ).classes("w-full")

            def _guardar() -> None:
                hora_inicio = str(in_inicio.value or "").strip()
                hora_fin    = str(in_fin.value or "").strip()
                tipo        = str(sel_tipo.value or "lectiva")
                etiqueta    = str(in_etiqueta.value or "").strip() or None

                if not hora_inicio or not hora_fin:
                    toast_warning("La hora de inicio y fin son obligatorias")
                    return

                try:
                    infra = Container.infraestructura_service()
                    existentes = infra.listar_franjas(p.id)

                    if es_edicion:
                        filas = []
                        for f in existentes:
                            if f.orden == franja_orden:
                                filas.append({
                                    "orden": f.orden, "hora_inicio": hora_inicio,
                                    "hora_fin": hora_fin, "tipo": tipo, "etiqueta": etiqueta,
                                })
                            else:
                                filas.append({
                                    "orden": f.orden, "hora_inicio": f.hora_inicio,
                                    "hora_fin": f.hora_fin,
                                    "tipo": f.tipo if isinstance(f.tipo, str) else f.tipo.value,
                                    "etiqueta": f.etiqueta,
                                })
                    else:
                        siguiente = max((f.orden for f in existentes), default=0) + 1
                        filas = [
                            {
                                "orden": f.orden, "hora_inicio": f.hora_inicio,
                                "hora_fin": f.hora_fin,
                                "tipo": f.tipo if isinstance(f.tipo, str) else f.tipo.value,
                                "etiqueta": f.etiqueta,
                            }
                            for f in existentes
                        ]
                        filas.append({
                            "orden": siguiente, "hora_inicio": hora_inicio,
                            "hora_fin": hora_fin, "tipo": tipo, "etiqueta": etiqueta,
                        })

                    infra.guardar_franjas(p.id, filas)
                    accion = "actualizada" if es_edicion else "añadida"
                    toast_success(f"Franja {accion} correctamente")
                    _cargar_franjas()
                    contenido_refreshable.refresh()
                    dlg.close()
                except ValueError as exc:
                    toast_warning(str(exc))
                except Exception as exc:
                    logger.error("Error al guardar franja: %s", exc)
                    toast_error("Error al guardar la franja")

            with ui.row().classes("gap-2 justify-end mt-4"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_primary("Guardar", on_click=_guardar, icon="save")

        dlg.open()

    def _eliminar_franja(orden: int) -> None:
        p = _s["plantilla_sel"]
        if p is None:
            return

        def _confirmar_eliminar():
            try:
                infra = Container.infraestructura_service()
                existentes = infra.listar_franjas(p.id)
                # Filtrar la franja a eliminar y renumerar
                filtradas = [f for f in existentes if f.orden != orden]
                filas = [
                    {
                        "orden":       idx + 1,
                        "hora_inicio": f.hora_inicio,
                        "hora_fin":    f.hora_fin,
                        "tipo":        f.tipo if isinstance(f.tipo, str) else f.tipo.value,
                        "etiqueta":    f.etiqueta,
                    }
                    for idx, f in enumerate(sorted(filtradas, key=lambda x: x.orden))
                ]
                infra.guardar_franjas(p.id, filas)
                toast_success("Franja eliminada")
                _cargar_franjas()
                contenido_refreshable.refresh()
            except Exception as exc:
                logger.error("Error al eliminar franja orden=%s: %s", orden, exc)
                toast_error("Error al eliminar la franja")

        confirm_dialog(
            titulo="Eliminar franja",
            mensaje=f"¿Eliminar la franja en orden {orden}? Las restantes se renumerarán.",
            on_confirm=_confirmar_eliminar,
            variante="danger",
            texto_confirmar="Eliminar",
        )

    # ── Sección refreshable ───────────────────────────────────────────────────
    @ui.refreshable
    def contenido_refreshable() -> None:

        # ── Sección A: Lista de plantillas ────────────────────────────────────
        with ui.element("div").classes("panel-card"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ThemeManager.icono(Icons.SCHEDULE, size=20, color="var(--color-primary)")
                ui.label("Plantillas horarias").classes("text-lg font-bold flex-1")
                btn_primary("Nueva plantilla", on_click=_dialogo_plantilla, icon="add")

            plantillas = _s["plantillas"]
            if not plantillas:
                empty_state(
                    icono=Icons.SCHEDULE,
                    titulo="Sin plantillas",
                    descripcion="Crea tu primera plantilla de franja horaria.",
                )
            else:
                # Cabecera de tabla
                with ui.element("div").classes("flex gap-4 p-2 font-semibold text-sm border-b"):
                    ui.label("Nombre").classes("flex-1")
                    ui.label("Jornada").classes("w-24")
                    ui.label("Días").classes("w-40")
                    ui.label("Activa").classes("w-20")
                    ui.label("Acciones").classes("w-36 text-right")

                for p in plantillas:
                    jornada_val = p.jornada.value if hasattr(p.jornada, "value") else str(p.jornada)
                    jornada_label = JORNADA_OPTS.get(jornada_val, jornada_val)
                    dias_str = ", ".join(p.dias_activos) if p.dias_activos else "—"
                    es_activa = getattr(p, "activa", False)

                    is_selected = _s["plantilla_sel"] and _s["plantilla_sel"].id == p.id
                    row_cls = "flex items-center gap-4 p-2 border-b"
                    if is_selected:
                        row_cls += " bg-selected"  # DYNAMIC — resaltado de fila seleccionada

                    with ui.element("div").classes(row_cls):
                        ui.label(p.nombre).classes("flex-1 font-medium")
                        ui.label(jornada_label).classes("w-24 text-sm")
                        ui.label(dias_str).classes("w-40 text-sm")
                        with ui.element("div").classes("w-20"):
                            if es_activa:
                                ui.badge("Activa").classes("badge-success")
                            else:
                                ui.badge("Inactiva").classes("badge-neutral")
                        with ui.row().classes("w-36 gap-1 justify-end"):
                            btn_secondary(
                                "Seleccionar",
                                on_click=lambda plantilla=p: _seleccionar_plantilla(plantilla),
                            )
                            if not es_activa:
                                btn_ghost(
                                    "Activar",
                                    on_click=lambda pid=p.id, nom=p.nombre: _activar_plantilla(pid, nom),
                                    icon="check_circle",
                                )
                            btn_danger(
                                "Eliminar",
                                on_click=lambda pid=p.id, nom=p.nombre: _eliminar_plantilla(pid, nom),
                                icon="delete",
                            )

        # ── Sección B: Gestión de franjas ─────────────────────────────────────
        plantilla_sel = _s["plantilla_sel"]
        if plantilla_sel is not None:
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ThemeManager.icono("schedule", size=20, color="var(--color-secondary)")
                    ui.label(f"Franjas de: {plantilla_sel.nombre}").classes("text-lg font-bold flex-1")
                    btn_primary("Añadir franja", on_click=_dialogo_franja, icon="add")

                franjas = _s["franjas"]
                if not franjas:
                    empty_state(
                        icono="schedule",
                        titulo="Sin franjas",
                        descripcion="Añade la primera franja a esta plantilla.",
                    )
                else:
                    with ui.element("div").classes("flex gap-4 p-2 font-semibold text-sm border-b"):
                        ui.label("Orden").classes("w-16")
                        ui.label("Hora inicio").classes("w-28")
                        ui.label("Hora fin").classes("w-28")
                        ui.label("Tipo").classes("w-24")
                        ui.label("Etiqueta").classes("flex-1")
                        ui.label("Acciones").classes("w-24 text-right")

                    for f in sorted(franjas, key=lambda x: x.orden):
                        tipo_val = f.tipo if isinstance(f.tipo, str) else f.tipo.value
                        tipo_label = TIPO_FRANJA_OPTS.get(tipo_val, tipo_val)
                        with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                            ui.label(str(f.orden)).classes("w-16 font-mono")
                            ui.label(f.hora_inicio).classes("w-28 font-mono")
                            ui.label(f.hora_fin).classes("w-28 font-mono")
                            ui.label(tipo_label).classes("w-24 text-sm")
                            ui.label(f.etiqueta or "—").classes("flex-1 text-sm")
                            with ui.row().classes("w-24 gap-1 justify-end"):
                                btn_ghost(
                                    on_click=lambda orden=f.orden: _dialogo_franja(orden),
                                    icon="edit",
                                )
                                btn_danger(
                                    "Eliminar",
                                    on_click=lambda orden=f.orden: _eliminar_franja(orden),
                                    icon="delete",
                                )

    # ── Layout principal ──────────────────────────────────────────────────────
    app_layout(
        ctx,
        contenido_refreshable,
        page_titulo    = "Plantillas horarias",
        page_subtitulo = "Gestiona las rejillas de tiempo para el generador de horarios",
        page_icono     = Icons.SCHEDULE,
    )


__all__ = ["plantillas_franja_page"]
