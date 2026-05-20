"""
src/interface/pages/admin/grupos.py
====================================
Página de administración de grupos escolares.
Ruta: /admin/grupos
Acceso: admin, director

Permite listar, crear, editar y eliminar grupos.
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
from src.services.infraestructura_service import Grupo, Jornada

logger = logging.getLogger("ADMIN.GRUPOS")

# Opciones de jornada para selectores
_JORNADAS = {
    "Mañana (AM)": "AM",
    "Tarde (PM)":  "PM",
    "Única":       "UNICA",
}
_JORNADA_LABELS = {v: k for k, v in _JORNADAS.items()}


@ui.page("/admin/grupos")
def grupos_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director"):
        ui.notify("Acceso no autorizado", type="negative")
        ui.navigate.to("/inicio")
        return

    logger.info("Grupos admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "grupos":         [],
        "cargando":       False,
        # formulario crear
        "form_codigo":    "",
        "form_grado":     1,
        "form_jornada":   "UNICA",
        "form_capacidad": 40,
        # edición
        "edit_id":        None,
        "edit_codigo":    "",
        "edit_grado":     1,
        "edit_jornada":   "UNICA",
        "edit_capacidad": 40,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            _s["grupos"] = Container.infraestructura_service().listar_grupos()
        except Exception as exc:
            logger.error("Error al cargar grupos: %s", exc)
            _s["grupos"] = []

    _cargar_estado()

    # ── Acciones CRUD ─────────────────────────────────────────────────────────
    def _crear_grupo() -> None:
        try:
            codigo    = _s["form_codigo"].strip().upper()
            grado     = int(_s["form_grado"])
            jornada   = Jornada(_s["form_jornada"])
            capacidad = int(_s["form_capacidad"])
            if not codigo:
                ui.notify("El código no puede estar vacío", type="warning")
                return
            grupo = Grupo(
                id=None,
                codigo=codigo,
                grado=grado,
                jornada=jornada,
                capacidad_maxima=capacidad,
            )
            Container.infraestructura_service().guardar_grupo(grupo)
            ui.notify(f"Grupo {codigo} creado", type="positive")
            _s["form_codigo"] = ""
            _s["form_grado"]  = 1
            _s["form_jornada"] = "UNICA"
            _s["form_capacidad"] = 40
            _cargar_estado()
            tabla.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al crear grupo: %s", exc)
            ui.notify("Error al crear el grupo", type="negative")

    def _eliminar_grupo(grupo_id: int, codigo: str) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label(
                f"¿Eliminar grupo {codigo}? Esta acción es irreversible."
            ).classes("text-base font-medium")
            with ui.row().classes("gap-2 mt-4"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_danger(
                    "Eliminar",
                    on_click=lambda: _confirmar_eliminar(dlg, grupo_id, codigo),
                )
        dlg.open()

    def _confirmar_eliminar(dlg, grupo_id: int, codigo: str) -> None:
        try:
            Container.infraestructura_service().eliminar_grupo(grupo_id)
            ui.notify(f"Grupo {codigo} eliminado", type="positive")
            dlg.close()
            _cargar_estado()
            tabla.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al eliminar grupo %s: %s", grupo_id, exc)
            ui.notify("Error al eliminar el grupo", type="negative")
            dlg.close()

    def _abrir_editar(grupo: Grupo) -> None:
        _s["edit_id"]       = grupo.id
        _s["edit_codigo"]   = grupo.codigo
        _s["edit_grado"]    = grupo.grado or 1
        _s["edit_jornada"]  = grupo.jornada.value if hasattr(grupo.jornada, "value") else str(grupo.jornada)
        _s["edit_capacidad"] = grupo.capacidad_maxima

        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            ui.label("Editar grupo").classes("text-lg font-bold mb-2")

            cod_inp = ui.input("Código", value=_s["edit_codigo"]).classes("w-full")
            grd_inp = ui.number("Grado", value=_s["edit_grado"], min=1, max=13).classes("w-full")
            jor_sel = ui.select(
                {v: k for k, v in _JORNADAS.items()},
                value=_s["edit_jornada"],
                label="Jornada",
            ).classes("w-full")
            cap_inp = ui.number("Capacidad", value=_s["edit_capacidad"], min=1).classes("w-full")

            def _guardar_edicion() -> None:
                try:
                    codigo    = str(cod_inp.value).strip().upper()
                    grado     = int(grd_inp.value)
                    jornada   = Jornada(jor_sel.value)
                    capacidad = int(cap_inp.value)
                    if not codigo:
                        ui.notify("El código no puede estar vacío", type="warning")
                        return
                    grupo_act = Grupo(
                        id=_s["edit_id"],
                        codigo=codigo,
                        grado=grado,
                        jornada=jornada,
                        capacidad_maxima=capacidad,
                    )
                    Container.infraestructura_service().actualizar_grupo(grupo_act)
                    ui.notify(f"Grupo {codigo} actualizado", type="positive")
                    dlg.close()
                    _cargar_estado()
                    tabla.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al actualizar grupo: %s", exc)
                    ui.notify("Error al actualizar el grupo", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_primary("Guardar", on_click=_guardar_edicion)

        dlg.open()

    # ── Secciones refreshables ────────────────────────────────────────────────
    @ui.refreshable
    def tabla() -> None:
        grupos = _s["grupos"]
        if not grupos:
            ui.label("No hay grupos registrados.").classes("text-empty mt-4")
            return

        columnas = [
            {"headerName": "Código",    "field": "codigo",         "sortable": True},
            {"headerName": "Grado",     "field": "grado",          "sortable": True},
            {"headerName": "Jornada",   "field": "jornada_label",  "sortable": True},
            {"headerName": "Capacidad", "field": "capacidad",      "sortable": True},
            {"headerName": "Acciones",  "field": "acciones",       "sortable": False},
        ]

        filas = []
        for g in grupos:
            jornada_val = g.jornada.value if hasattr(g.jornada, "value") else str(g.jornada)
            filas.append({
                "id":           g.id,
                "codigo":       g.codigo,
                "grado":        g.grado or "—",
                "jornada_label": _JORNADA_LABELS.get(jornada_val, jornada_val),
                "capacidad":    g.capacidad_maxima,
            })

        with ui.element("div").classes("w-full"):
            for fila in filas:
                g_obj = next((x for x in grupos if x.id == fila["id"]), None)
                with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                    ui.label(fila["codigo"]).classes("font-mono font-bold w-24")
                    ui.label(f"Grado {fila['grado']}").classes("w-20")
                    ui.label(fila["jornada_label"]).classes("w-28")
                    ui.label(f"{fila['capacidad']} estudiantes").classes("w-32")
                    with ui.row().classes("gap-2 ml-auto"):
                        btn_icon("edit", on_click=lambda g=g_obj: _abrir_editar(g), tooltip="Editar")
                        btn_icon("delete", on_click=lambda gid=fila["id"], cod=fila["codigo"]: _eliminar_grupo(gid, cod), tooltip="Eliminar", variante="danger")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # Encabezado
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("items-center gap-2 mb-4"):
                    ThemeManager.icono(Icons.GROUPS, size=22, color="var(--color-primary)")
                    ui.label("Gestión de Grupos").classes("text-xl font-bold")

                # Formulario de creación
                ui.label("Crear nuevo grupo").classes("text-base font-semibold mb-2")
                with ui.row().classes("gap-3 flex-wrap items-end"):
                    cod = ui.input("Código *", placeholder="601").classes("w-28").bind_value(
                        _s, "form_codigo"
                    )
                    grd = ui.number("Grado", value=1, min=1, max=13).classes("w-24").bind_value(
                        _s, "form_grado"
                    )
                    jor = ui.select(
                        {v: k for k, v in _JORNADAS.items()},
                        value="UNICA",
                        label="Jornada",
                    ).classes("w-36").bind_value(_s, "form_jornada")
                    cap = ui.number("Capacidad", value=40, min=1).classes("w-28").bind_value(
                        _s, "form_capacidad"
                    )
                    btn_primary("Crear grupo", on_click=_crear_grupo, icon="add").classes("mt-1")

            # Tabla de grupos
            with ui.element("div").classes("panel-card mt-4"):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ui.label("Grupos registrados").classes("text-base font-semibold")
                    ui.badge(str(len(_s["grupos"]))).classes("badge-primary")
                    btn_icon("refresh", on_click=lambda: (_cargar_estado(), tabla.refresh()), tooltip="Recargar")
                tabla()

    app_layout(
        titulo_pagina="Administración · Grupos",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/admin/grupos",
        contenido=contenido,
        ctx=ctx,
    )


__all__ = ["grupos_page"]
