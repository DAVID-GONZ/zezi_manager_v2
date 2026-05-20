"""
src/interface/pages/admin/usuarios.py
======================================
Página de administración de usuarios.
Ruta: /admin/usuarios
Acceso: admin, director

Permite:
 - Listar usuarios con filtros (rol, solo activos).
 - Crear usuario (solo admin).
 - Desactivar usuario (solo admin).
 - Cambiar rol (solo admin).
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
from src.services.usuario_service import NuevoUsuarioDTO, FiltroUsuariosDTO, Rol

logger = logging.getLogger("ADMIN.USUARIOS")

_ROLES_OPCIONES = {
    "admin":        "Administrador",
    "director":     "Director",
    "coordinador":  "Coordinador",
    "profesor":     "Profesor",
}


@ui.page("/admin/usuarios")
def usuarios_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    if ctx.usuario_rol not in ("admin", "director"):
        ui.notify("Acceso no autorizado", type="negative")
        ui.navigate.to("/inicio")
        return

    es_admin = ctx.usuario_rol == "admin"

    logger.info("Usuarios admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "usuarios":        [],
        "filtro_rol":      None,
        "filtro_activos":  True,
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            rol_val = Rol(_s["filtro_rol"]) if _s["filtro_rol"] else None
            filtro  = FiltroUsuariosDTO(
                rol=rol_val,
                solo_activos=_s["filtro_activos"],
            )
            _s["usuarios"] = Container.usuario_service().listar_resumenes(filtro)
        except Exception as exc:
            logger.error("Error al cargar usuarios: %s", exc)
            _s["usuarios"] = []

    _cargar_estado()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _abrir_crear_usuario() -> None:
        if not es_admin:
            ui.notify("Solo el administrador puede crear usuarios", type="warning")
            return

        with ui.dialog() as dlg, ui.card().classes("w-full max-w-lg"):
            ui.label("Crear nuevo usuario").classes("text-lg font-bold mb-2")
            nombre_inp    = ui.input("Nombre completo *", placeholder="Carlos López García").classes("w-full")
            usuario_inp   = ui.input("Nombre de usuario *", placeholder="c.lopez").classes("w-full")
            password_inp  = ui.input("Contraseña inicial", placeholder="dejar vacío = usa username").classes("w-full")
            rol_sel       = ui.select(
                _ROLES_OPCIONES, value="profesor", label="Rol"
            ).classes("w-full")
            email_inp     = ui.input("Email (opcional)").classes("w-full")

            def _crear() -> None:
                try:
                    nombre   = str(nombre_inp.value).strip()
                    usuario  = str(usuario_inp.value).strip()
                    password = str(password_inp.value).strip() or None
                    rol_str  = rol_sel.value
                    email    = str(email_inp.value).strip() or None

                    if not nombre or not usuario:
                        ui.notify("Nombre completo y usuario son obligatorios", type="warning")
                        return

                    dto = NuevoUsuarioDTO(
                        usuario=usuario,
                        nombre_completo=nombre,
                        rol=Rol(rol_str),
                        email=email,
                        password=password,
                    )
                    Container.usuario_service().crear_usuario(dto)
                    ui.notify(f"Usuario '{usuario}' creado", type="positive")
                    dlg.close()
                    _cargar_estado()
                    tabla.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al crear usuario: %s", exc)
                    ui.notify("Error al crear el usuario", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_primary("Crear", on_click=_crear)

        dlg.open()

    def _desactivar_usuario(usuario_id: int, nombre: str) -> None:
        if not es_admin:
            ui.notify("Solo el administrador puede desactivar usuarios", type="warning")
            return
        with ui.dialog() as dlg, ui.card():
            ui.label(
                f"¿Desactivar al usuario '{nombre}'? No podrá iniciar sesión."
            ).classes("text-base font-medium")
            with ui.row().classes("gap-2 mt-4"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_danger(
                    "Desactivar",
                    on_click=lambda: _confirmar_desactivar(dlg, usuario_id, nombre),
                )
        dlg.open()

    def _confirmar_desactivar(dlg, usuario_id: int, nombre: str) -> None:
        try:
            Container.usuario_service().desactivar(usuario_id)
            ui.notify(f"Usuario '{nombre}' desactivado", type="positive")
            dlg.close()
            _cargar_estado()
            tabla.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al desactivar usuario %s: %s", usuario_id, exc)
            ui.notify("Error al desactivar el usuario", type="negative")
            dlg.close()

    def _cambiar_rol(usuario_id: int, nombre: str, rol_actual: str) -> None:
        if not es_admin:
            ui.notify("Solo el administrador puede cambiar roles", type="warning")
            return
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-sm"):
            ui.label(f"Cambiar rol de '{nombre}'").classes("text-lg font-bold mb-2")
            rol_sel = ui.select(
                _ROLES_OPCIONES,
                value=rol_actual if rol_actual in _ROLES_OPCIONES else "profesor",
                label="Nuevo rol",
            ).classes("w-full")

            def _aplicar() -> None:
                try:
                    Container.usuario_service().cambiar_rol(usuario_id, rol_sel.value)
                    ui.notify(f"Rol actualizado a '{_ROLES_OPCIONES.get(rol_sel.value)}'", type="positive")
                    dlg.close()
                    _cargar_estado()
                    tabla.refresh()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                except Exception as exc:
                    logger.error("Error al cambiar rol %s: %s", usuario_id, exc)
                    ui.notify("Error al cambiar el rol", type="negative")

            with ui.row().classes("gap-2 mt-4 justify-end"):
                btn_ghost("Cancelar", on_click=dlg.close)
                btn_primary("Aplicar", on_click=_aplicar)
        dlg.open()

    def _on_filtros_cambio() -> None:
        _cargar_estado()
        tabla.refresh()

    # ── Sección refreshable ───────────────────────────────────────────────────
    @ui.refreshable
    def tabla() -> None:
        usuarios = _s["usuarios"]
        if not usuarios:
            ui.label("No hay usuarios con los filtros actuales.").classes("text-empty mt-4")
            return

        _ROL_CLASES = {
            "admin":       "badge-error",
            "director":    "badge-purple",
            "coordinador": "badge-info",
            "profesor":    "badge-success",
        }

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-4 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Nombre completo").classes("flex-1")
                ui.label("Usuario").classes("w-32")
                ui.label("Rol").classes("w-28")
                ui.label("Estado").classes("w-20")
                if es_admin:
                    ui.label("Acciones").classes("w-32 text-right")

            for u in usuarios:
                rol_str = u.rol.value if hasattr(u.rol, "value") else str(u.rol)
                with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                    ui.label(u.nombre_completo).classes("flex-1")
                    ui.label(u.usuario).classes("w-32 font-mono text-sm")
                    ui.badge(
                        _ROLES_OPCIONES.get(rol_str, rol_str),
                    ).classes(f"w-28 {_ROL_CLASES.get(rol_str, 'badge-neutral')}")
                    if u.activo:
                        ui.badge("Activo").classes("w-20 badge-success")
                    else:
                        ui.badge("Inactivo").classes("w-20 badge-neutral")
                    if es_admin:
                        with ui.row().classes("w-32 gap-1 justify-end"):
                            btn_icon("manage_accounts", on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str: _cambiar_rol(uid, nom, r), tooltip="Cambiar rol")
                            if u.activo:
                                btn_icon("person_off", on_click=lambda uid=u.id, nom=u.nombre_completo: _desactivar_usuario(uid, nom), tooltip="Desactivar", variante="danger")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):
            with ui.element("div").classes("panel-card"):
                # Cabecera y botón crear
                with ui.row().classes("items-center gap-2 mb-4 flex-wrap"):
                    ThemeManager.icono(Icons.TEACHERS, size=22, color="var(--color-primary)")
                    ui.label("Gestión de Usuarios").classes("text-xl font-bold")
                    if es_admin:
                        btn_primary("Nuevo usuario", on_click=_abrir_crear_usuario, icon="person_add").classes("ml-auto")

                # Filtros
                with ui.row().classes("gap-4 items-center flex-wrap mb-4"):
                    ui.label("Filtros:").classes("text-sm font-semibold")
                    roles_opts = {None: "Todos los roles"}
                    roles_opts.update(_ROLES_OPCIONES)
                    ui.select(
                        roles_opts,
                        value=None,
                        label="Rol",
                        on_change=lambda e: (
                            _s.__setitem__("filtro_rol", e.value),
                            _on_filtros_cambio(),
                        ),
                    ).classes("w-44")
                    ui.checkbox(
                        "Solo activos",
                        value=_s["filtro_activos"],
                        on_change=lambda e: (
                            _s.__setitem__("filtro_activos", e.value),
                            _on_filtros_cambio(),
                        ),
                    )
                    ui.badge(str(len(_s["usuarios"]))).classes("badge-primary")
                    btn_icon("refresh", on_click=lambda: (_cargar_estado(), tabla.refresh()), tooltip="Recargar")

                tabla()

    app_layout(
        titulo_pagina="Administración · Usuarios",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/admin/usuarios",
        contenido=contenido,
        ctx=ctx,
    )


__all__ = ["usuarios_page"]
