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
from src.interface.design.components import confirm_dialog, badge_estado_general, status_badge, form_dialog
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
    puede_crear = ctx.usuario_rol in ("admin", "director")
    # Roles que puede crear según el rol del usuario actual
    _roles_crear_admin = {"admin": "Administrador", "director": "Director", "coordinador": "Coordinador", "profesor": "Profesor"}
    _roles_crear_director = {"coordinador": "Coordinador", "profesor": "Profesor"}
    roles_disponibles_crear = _roles_crear_admin if es_admin else _roles_crear_director

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
        if not puede_crear:
            ui.notify("No tienes permisos para crear usuarios", type="warning")
            return

        def _crear(datos: dict) -> "bool | None":
            try:
                nombre   = str(datos.get("nombre_completo", "")).strip()
                usuario  = str(datos.get("usuario", "")).strip()
                password = str(datos.get("password", "")).strip() or None
                rol_str  = datos.get("rol", "profesor")
                email    = str(datos.get("email", "")).strip() or None

                if not nombre or not usuario:
                    ui.notify("Nombre completo y usuario son obligatorios", type="warning")
                    return False

                # Director no puede crear admin ni director
                if not es_admin and rol_str in ("admin", "director"):
                    ui.notify("No puedes crear usuarios con ese rol", type="warning")
                    return False

                dto = NuevoUsuarioDTO(
                    usuario=usuario,
                    nombre_completo=nombre,
                    rol=Rol(rol_str),
                    email=email,
                    password=password,
                )
                Container.usuario_service().crear_usuario(dto)
                ui.notify(f"Usuario '{usuario}' creado", type="positive")
                _cargar_estado()
                tabla.refresh()
            except ValueError as exc:
                ui.notify(str(exc), type="warning")
                return False
            except Exception as exc:
                logger.error("Error al crear usuario: %s", exc)
                ui.notify("Error al crear el usuario", type="negative")
                return False

        form_dialog(
            titulo    = "Crear nuevo usuario",
            campos    = [
                {"key": "nombre_completo", "label": "Nombre completo *",  "tipo": "text",
                 "requerido": True, "placeholder": "Carlos López García"},
                {"key": "usuario",         "label": "Nombre de usuario *", "tipo": "text",
                 "requerido": True, "placeholder": "c.lopez"},
                {"key": "password",        "label": "Contraseña inicial",  "tipo": "password",
                 "placeholder": "dejar vacío = usa username"},
                {"key": "rol",             "label": "Rol",                 "tipo": "select",
                 "opciones": roles_disponibles_crear, "valor": "profesor"},
                {"key": "email",           "label": "Email (opcional)",    "tipo": "email",
                 "placeholder": "usuario@institucion.edu.co"},
            ],
            on_submit    = _crear,
            texto_submit = "Crear",
            max_width    = "max-w-lg",
            columnas     = 2,
        )

    def _confirmar_desactivar(usuario_id: int, nombre: str) -> None:
        try:
            Container.usuario_service().desactivar(usuario_id)
            ui.notify(f"Usuario '{nombre}' desactivado", type="positive")
            _cargar_estado()
            tabla.refresh()
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
        except Exception as exc:
            logger.error("Error al desactivar usuario %s: %s", usuario_id, exc)
            ui.notify("Error al desactivar el usuario", type="negative")

    def _desactivar_usuario(usuario_id: int, nombre: str) -> None:
        if not es_admin:
            ui.notify("Solo el administrador puede desactivar usuarios", type="warning")
            return
        confirm_dialog(
            titulo          = "Desactivar usuario",
            mensaje         = f"¿Desactivar la cuenta de '{nombre}'? No podrá iniciar sesión.",
            on_confirm      = lambda: _confirmar_desactivar(usuario_id, nombre),
            variante        = "danger",
            texto_confirmar = "Desactivar",
        )

    def _cambiar_rol(usuario_id: int, nombre: str, rol_actual: str) -> None:
        if not es_admin:
            ui.notify("Solo el administrador puede cambiar roles", type="warning")
            return

        def _aplicar(datos: dict) -> "bool | None":
            try:
                nuevo_rol = datos.get("rol", rol_actual)
                Container.usuario_service().cambiar_rol(usuario_id, nuevo_rol)
                ui.notify(f"Rol actualizado a '{_ROLES_OPCIONES.get(nuevo_rol, nuevo_rol)}'", type="positive")
                _cargar_estado()
                tabla.refresh()
            except ValueError as exc:
                ui.notify(str(exc), type="warning")
                return False
            except Exception as exc:
                logger.error("Error al cambiar rol %s: %s", usuario_id, exc)
                ui.notify("Error al cambiar el rol", type="negative")
                return False

        form_dialog(
            titulo    = f"Cambiar rol de '{nombre}'",
            campos    = [
                {"key": "rol", "label": "Nuevo rol *", "tipo": "select",
                 "opciones": _ROLES_OPCIONES,
                 "valor": rol_actual if rol_actual in _ROLES_OPCIONES else "profesor",
                 "requerido": True},
            ],
            on_submit    = _aplicar,
            texto_submit = "Cambiar rol",
            max_width    = "max-w-sm",
        )

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
                    status_badge(
                        _ROLES_OPCIONES.get(rol_str, rol_str),
                        _ROL_CLASES.get(rol_str, "badge-neutral").replace("badge-", ""),
                    )
                    if u.activo:
                        badge_estado_general(True)
                    else:
                        badge_estado_general(False)
                    if es_admin:
                        with ui.row().classes("w-32 gap-1 justify-end"):
                            btn_icon("manage_accounts", on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str: _cambiar_rol(uid, nom, r), tooltip="Cambiar rol")
                            if u.activo:
                                btn_icon("person_off", on_click=lambda uid=u.id, nom=u.nombre_completo: _desactivar_usuario(uid, nom), tooltip="Desactivar", variante="danger")

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            with ui.element("div").classes("panel-card"):

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

    _acciones = [
        {"label": "Nuevo usuario", "on_click": _abrir_crear_usuario, "icono": "person_add", "variante": "primary"},
    ] if puede_crear else None

    app_layout(
        ctx,
        contenido,
        page_titulo    = "Gestión de Usuarios",
        page_subtitulo = "Cuentas de usuario y roles del sistema",
        page_icono     = Icons.TEACHERS,
        page_acciones  = _acciones,
    )


__all__ = ["usuarios_page"]
