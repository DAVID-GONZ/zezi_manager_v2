"""
src/interface/pages/admin/asignaturas.py
=========================================
Página de administración de asignaturas y áreas de conocimiento.
Ruta: /admin/asignaturas
Acceso: admin, director

Permite:
 - CRUD de áreas de conocimiento.
 - CRUD de asignaturas filtradas por área.
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager
from src.interface.design.tokens import Icons
from src.services.infraestructura_service import AreaConocimiento, Asignatura

logger = logging.getLogger("ADMIN.ASIGNATURAS")


@ui.page("/admin/asignaturas")
def asignaturas_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director"):
        ui.notify("Acceso no autorizado", type="negative")
        ui.navigate.to("/inicio")
        return

    logger.info("Asignaturas admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "areas":              [],
        "asignaturas":        [],
        "area_filtro_id":     None,
        # formulario área
        "area_nombre":        "",
        "area_codigo":        "",
        # formulario asignatura
        "asig_nombre":        "",
        "asig_codigo":        "",
        "asig_area_id":       None,
        "asig_intensidad":    1,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_areas() -> None:
        try:
            _s["areas"] = Container.infraestructura_service().listar_areas()
        except Exception as exc:
            logger.error("Error al cargar áreas: %s", exc)
            _s["areas"] = []

    def _cargar_asignaturas() -> None:
        try:
            area_id = _s["area_filtro_id"] if _s["area_filtro_id"] else None
            _s["asignaturas"] = Container.infraestructura_service().listar_asignaturas(
                area_id=area_id
            )
        except Exception as exc:
            logger.error("Error al cargar asignaturas: %s", exc)
            _s["asignaturas"] = []

    _cargar_areas()
    _cargar_asignaturas()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _nombre_area(area_id) -> str:
        for a in _s["areas"]:
            if a.id == area_id:
                return a.nombre
        return "—"

    # ── CRUD Áreas ────────────────────────────────────────────────────────────
    def _crear_area() -> None:
        try:
            nombre = _s["area_nombre"].strip()
            codigo = _s["area_codigo"].strip() or None
            if not nombre:
                ui.notify("El nombre del área no puede estar vacío", type="warning")
                return
            area = AreaConocimiento(id=None, nombre=nombre, codigo=codigo)
            Container.infraestructura_service().guardar_area(area)
            ui.notify(f"Área '{nombre}' creada", type="positive")
            _s["area_nombre"] = ""
            _s["area_codigo"] = ""
            _cargar_areas()
            _cargar_asignaturas()
            tabla_areas.refresh()
            filtro_area.refresh()
            tabla_asignaturas.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al crear área: %s", exc)
            ui.notify("Error al crear el área", type="negative")

    def _eliminar_area(area_id: int, nombre: str) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label(
                f"¿Eliminar área '{nombre}'? Esta acción es irreversible."
            ).classes("text-base font-medium")
            with ui.row().classes("gap-2 mt-4"):
                ui.button("Cancelar", on_click=dlg.close).props("flat")
                ui.button(
                    "Eliminar",
                    color="negative",
                    on_click=lambda: _confirmar_eliminar_area(dlg, area_id, nombre),
                )
        dlg.open()

    def _confirmar_eliminar_area(dlg, area_id: int, nombre: str) -> None:
        try:
            Container.infraestructura_service().eliminar_area(area_id)
            ui.notify(f"Área '{nombre}' eliminada", type="positive")
            dlg.close()
            _cargar_areas()
            _cargar_asignaturas()
            tabla_areas.refresh()
            filtro_area.refresh()
            tabla_asignaturas.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al eliminar área %s: %s", area_id, exc)
            ui.notify("Error al eliminar el área", type="negative")
            dlg.close()

    def _editar_area(area: AreaConocimiento) -> None:
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            ui.label("Editar área").classes("text-lg font-bold mb-2")
            nom = ui.input("Nombre *", value=area.nombre).classes("w-full")
            cod = ui.input("Código", value=area.codigo or "").classes("w-full")

            def _guardar() -> None:
                try:
                    area_act = AreaConocimiento(
                        id=area.id,
                        nombre=str(nom.value).strip(),
                        codigo=str(cod.value).strip() or None,
                    )
                    Container.infraestructura_service().actualizar_area(area_act)
                    ui.notify(f"Área '{area_act.nombre}' actualizada", type="positive")
                    dlg.close()
                    _cargar_areas()
                    _cargar_asignaturas()
                    tabla_areas.refresh()
                    filtro_area.refresh()
                    tabla_asignaturas.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al actualizar área: %s", exc)
                    ui.notify("Error al actualizar el área", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                ui.button("Cancelar", on_click=dlg.close).props("flat")
                ui.button("Guardar", on_click=_guardar, color="primary")
        dlg.open()

    # ── CRUD Asignaturas ──────────────────────────────────────────────────────
    def _crear_asignatura() -> None:
        try:
            nombre     = _s["asig_nombre"].strip()
            codigo     = _s["asig_codigo"].strip() or None
            area_id    = _s["asig_area_id"]
            intensidad = int(_s["asig_intensidad"])
            if not nombre:
                ui.notify("El nombre de la asignatura no puede estar vacío", type="warning")
                return
            asig = Asignatura(
                id=None,
                nombre=nombre,
                codigo=codigo,
                area_id=area_id if area_id else None,
                horas_semanales=intensidad,
            )
            Container.infraestructura_service().guardar_asignatura(asig)
            ui.notify(f"Asignatura '{nombre}' creada", type="positive")
            _s["asig_nombre"]     = ""
            _s["asig_codigo"]     = ""
            _s["asig_area_id"]    = None
            _s["asig_intensidad"] = 1
            _cargar_asignaturas()
            tabla_asignaturas.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al crear asignatura: %s", exc)
            ui.notify("Error al crear la asignatura", type="negative")

    def _eliminar_asignatura(asig_id: int, nombre: str) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label(
                f"¿Eliminar asignatura '{nombre}'? Esta acción es irreversible."
            ).classes("text-base font-medium")
            with ui.row().classes("gap-2 mt-4"):
                ui.button("Cancelar", on_click=dlg.close).props("flat")
                ui.button(
                    "Eliminar",
                    color="negative",
                    on_click=lambda: _confirmar_eliminar_asig(dlg, asig_id, nombre),
                )
        dlg.open()

    def _confirmar_eliminar_asig(dlg, asig_id: int, nombre: str) -> None:
        try:
            Container.infraestructura_service().eliminar_asignatura(asig_id)
            ui.notify(f"Asignatura '{nombre}' eliminada", type="positive")
            dlg.close()
            _cargar_asignaturas()
            tabla_asignaturas.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al eliminar asignatura %s: %s", asig_id, exc)
            ui.notify("Error al eliminar la asignatura", type="negative")
            dlg.close()

    def _editar_asignatura(asig: Asignatura) -> None:
        areas_dict = {a.id: a.nombre for a in _s["areas"]}
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            ui.label("Editar asignatura").classes("text-lg font-bold mb-2")
            nom = ui.input("Nombre *", value=asig.nombre).classes("w-full")
            cod = ui.input("Código", value=asig.codigo or "").classes("w-full")
            are = ui.select(areas_dict, value=asig.area_id, label="Área").classes("w-full")
            hor = ui.number("Horas semanales", value=asig.horas_semanales, min=1).classes("w-full")

            def _guardar() -> None:
                try:
                    asig_act = Asignatura(
                        id=asig.id,
                        nombre=str(nom.value).strip(),
                        codigo=str(cod.value).strip() or None,
                        area_id=are.value if are.value else None,
                        horas_semanales=int(hor.value),
                    )
                    Container.infraestructura_service().actualizar_asignatura(asig_act)
                    ui.notify(f"Asignatura '{asig_act.nombre}' actualizada", type="positive")
                    dlg.close()
                    _cargar_asignaturas()
                    tabla_asignaturas.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al actualizar asignatura: %s", exc)
                    ui.notify("Error al actualizar la asignatura", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                ui.button("Cancelar", on_click=dlg.close).props("flat")
                ui.button("Guardar", on_click=_guardar, color="primary")
        dlg.open()

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def filtro_area() -> None:
        areas_opts = {None: "Todas las áreas"}
        for a in _s["areas"]:
            areas_opts[a.id] = a.nombre

        def _on_filtro_change(v) -> None:
            _s["area_filtro_id"] = v
            _cargar_asignaturas()
            tabla_asignaturas.refresh()

        ui.select(
            areas_opts,
            value=_s["area_filtro_id"],
            label="Filtrar por área",
            on_change=lambda e: _on_filtro_change(e.value),
        ).classes("w-56")

    @ui.refreshable
    def tabla_areas() -> None:
        areas = _s["areas"]
        if not areas:
            ui.label("No hay áreas registradas.").classes("text-empty mt-2")
            return
        for a in areas:
            with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                ui.label(a.nombre).classes("flex-1 font-medium")
                if a.codigo:
                    ui.badge(a.codigo).classes("badge-neutral")
                with ui.row().classes("gap-1 ml-auto"):
                    ui.button(
                        icon="edit",
                        on_click=lambda area=a: _editar_area(area),
                    ).props("flat round dense").tooltip("Editar")
                    ui.button(
                        icon="delete",
                        color="negative",
                        on_click=lambda aid=a.id, nom=a.nombre: _eliminar_area(aid, nom),
                    ).props("flat round dense").tooltip("Eliminar")

    @ui.refreshable
    def tabla_asignaturas() -> None:
        asigs = _s["asignaturas"]
        if not asigs:
            ui.label("No hay asignaturas en esta área.").classes("text-empty mt-2")
            return
        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-4 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Nombre").classes("flex-1")
                ui.label("Código").classes("w-24")
                ui.label("Área").classes("w-36")
                ui.label("Hrs/sem").classes("w-20")
                ui.label("Acciones").classes("w-24 text-right")
            for a in asigs:
                with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                    ui.label(a.nombre).classes("flex-1")
                    ui.label(a.codigo or "—").classes("w-24 font-mono text-sm")
                    ui.label(_nombre_area(a.area_id)).classes("w-36 text-sm")
                    ui.label(str(a.horas_semanales)).classes("w-20")
                    with ui.row().classes("w-24 gap-1 justify-end"):
                        ui.button(
                            icon="edit",
                            on_click=lambda asig=a: _editar_asignatura(asig),
                        ).props("flat round dense").tooltip("Editar")
                        ui.button(
                            icon="delete",
                            color="negative",
                            on_click=lambda aid=a.id, nom=a.nombre: _eliminar_asignatura(aid, nom),
                        ).props("flat round dense").tooltip("Eliminar")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # ── Sección: Áreas de conocimiento ───────────────────────────────
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ThemeManager.icono("category", size=20, color="var(--color-info)")
                    ui.label("Áreas de conocimiento").classes("text-lg font-bold")

                ui.label("Nueva área").classes("text-sm font-semibold mb-1")
                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input("Nombre *", placeholder="Matemáticas").classes("w-48").bind_value(
                        _s, "area_nombre"
                    )
                    ui.input("Código", placeholder="MAT").classes("w-28").bind_value(
                        _s, "area_codigo"
                    )
                    with ui.button("Crear área", on_click=_crear_area, color="primary"):
                        ThemeManager.icono("add")

                ui.separator().classes("my-3")
                tabla_areas()

            # ── Sección: Asignaturas ─────────────────────────────────────────
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center gap-2 mb-3 flex-wrap"):
                    ThemeManager.icono(Icons.GRADES, size=20, color="var(--color-primary)")
                    ui.label("Asignaturas").classes("text-lg font-bold")
                    filtro_area()
                    ui.button(
                        icon="refresh",
                        on_click=lambda: (
                            _cargar_areas(),
                            _cargar_asignaturas(),
                            tabla_areas.refresh(),
                            filtro_area.refresh(),
                            tabla_asignaturas.refresh(),
                        ),
                    ).props("flat round dense").tooltip("Recargar")

                ui.label("Nueva asignatura").classes("text-sm font-semibold mb-1")
                areas_opts = {a.id: a.nombre for a in _s["areas"]}
                with ui.row().classes("gap-3 items-end flex-wrap"):
                    ui.input("Nombre *", placeholder="Álgebra").classes("w-48").bind_value(
                        _s, "asig_nombre"
                    )
                    ui.input("Código", placeholder="ALG").classes("w-28").bind_value(
                        _s, "asig_codigo"
                    )
                    ui.select(
                        areas_opts,
                        label="Área",
                    ).classes("w-44").bind_value(_s, "asig_area_id")
                    ui.number("Hrs/sem", value=1, min=1).classes("w-24").bind_value(
                        _s, "asig_intensidad"
                    )
                    ui.button(
                        "Crear asignatura", icon="add", on_click=_crear_asignatura, color="primary"
                    )

                ui.separator().classes("my-3")
                tabla_asignaturas()

    app_layout(
        titulo_pagina="Administración · Asignaturas",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/admin/asignaturas",
        contenido=contenido,
    )


__all__ = ["asignaturas_page"]
