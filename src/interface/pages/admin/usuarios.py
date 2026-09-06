"""
src/interface/pages/admin/usuarios.py
======================================
Página de auditoría de usuarios de la plataforma.
Ruta: /admin/usuarios
Acceso: admin

Admin (auditor de plataforma):
 - Ve la lista completa de usuarios con filtros (para auditoría).
 - Puede impersonar cualquier usuario activo ("Ver como", solo lectura).
 - Gestiona solo directores (restablecer contraseña / desactivar / reactivar).
 - NO crea usuarios desde aquí (los directores se crean vía
   /admin/instituciones con el flujo de aprovisionamiento).

La gestión de coordinadores y profesores es responsabilidad del director
desde /director/equipo.

El RBAC real vive en el servicio; la vista solo consulta la política para
mostrar u ocultar controles (defensa en profundidad).
"""

from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.components import (
    badge_estado_general,
    confirm_dialog,
    empty_state,
    form_dialog,
    status_badge,
    toast_error,
    toast_success,
    toast_warning,
)
from src.interface.design.components.buttons import btn_icon
from src.interface.design.components.form_fields import filter_select
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.interface.presenters.admin.usuarios_presenter import UsuariosPresenter
from src.services.usuario_service import FiltroUsuariosDTO

logger = logging.getLogger("ADMIN.USUARIOS")

_ROLES_OPCIONES = {
    "admin": "Administrador",
    "director": "Director",
    "coordinador": "Coordinador",
    "profesor": "Profesor",
}


def usuarios_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    svc = Container.usuario_service()

    # -- Scope multi-tenant: admin puede filtrar por institución ---
    instituciones_opts: dict = {None: "Todas las instituciones"}
    try:
        for i in Container.institucion_service().listar():
            instituciones_opts[i.id] = i.nombre
    except Exception as exc:
        logger.error("Error al cargar instituciones: %s", exc)

    logger.info("Usuarios admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # -- Estado mutable ---
    presenter = UsuariosPresenter()
    _s = presenter.estado

    # -- Carga de datos ---
    def _cargar_estado() -> None:
        try:
            filtro = FiltroUsuariosDTO(
                rol=_s["filtro_rol"] or None,
                solo_activos=_s["filtro_activos"],
                institucion_id=_s["filtro_institucion"],
            )
            presenter.set_usuarios(Container.usuario_service().listar_resumenes(filtro))
        except Exception as exc:
            logger.error("Error al cargar usuarios: %s", exc)
            presenter.set_usuarios([])

    _cargar_estado()

    # -- Acciones ---
    def _confirmar_desactivar(usuario_id: int, nombre: str) -> None:
        try:
            svc.desactivar(
                usuario_id,
                desactivado_por_id=ctx.usuario_id,
                actor_rol=ctx.usuario_rol,
            )
            toast_success(f"Usuario '{nombre}' desactivado")
            _cargar_estado()
            tabla.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al desactivar usuario %s: %s", usuario_id, exc)
            toast_error("Error al desactivar el usuario")

    def _desactivar_usuario(usuario_id: int, nombre: str, rol_actual: str) -> None:
        if not svc.puede_gestionar(ctx.usuario_rol, rol_actual):
            toast_warning("No tienes permiso para desactivar a este usuario")
            return
        confirm_dialog(
            titulo="Desactivar usuario",
            mensaje=f"¿Desactivar la cuenta de '{nombre}'? No podrá iniciar sesión.",
            on_confirm=lambda: _confirmar_desactivar(usuario_id, nombre),
            variante="danger",
            texto_confirmar="Desactivar",
        )

    def _reactivar_usuario(usuario_id: int, nombre: str, rol_actual: str) -> None:
        if not svc.puede_gestionar(ctx.usuario_rol, rol_actual):
            toast_warning("No tienes permiso para reactivar a este usuario")
            return
        try:
            svc.reactivar(
                usuario_id,
                reactivado_por_id=ctx.usuario_id,
                actor_rol=ctx.usuario_rol,
            )
            toast_success(f"Usuario '{nombre}' reactivado")
            _cargar_estado()
            tabla.refresh()
        except ValueError as exc:
            toast_warning(str(exc))
        except Exception as exc:
            logger.error("Error al reactivar usuario %s: %s", usuario_id, exc)
            toast_error("Error al reactivar el usuario")

    def _resetear_password(usuario_id: int, nombre: str, username: str, rol_actual: str) -> None:
        if not svc.puede_gestionar(ctx.usuario_rol, rol_actual):
            toast_warning("No tienes permiso para restablecer la contraseña de este usuario")
            return

        def _aplicar(datos: dict) -> bool | None:
            try:
                nueva = datos.get("password") or ""
                svc.resetear_password(
                    usuario_id,
                    nueva,
                    actor_rol=ctx.usuario_rol,
                    reset_por_id=ctx.usuario_id,
                )
                usada = "el nombre de usuario" if not nueva.strip() else "la nueva contraseña"
                toast_success(f"Contraseña de '{nombre}' restablecida con {usada}")
                _cargar_estado()
                tabla.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al restablecer contraseña %s: %s", usuario_id, exc)
                toast_error("Error al restablecer la contraseña")
                return False

        form_dialog(
            titulo=f"Restablecer contraseña de '{nombre}'",
            campos=[
                {
                    "key": "password",
                    "label": "Nueva contraseña",
                    "tipo": "password",
                    "hint": f"Dejar vacío usa el username ({username})",
                },
            ],
            on_submit=_aplicar,
            texto_submit="Restablecer",
            max_width="max-w-sm",
        )

    def _ver_como(
        usuario_id: int,
        nombre: str,
        rol: str,
        institucion_id: int | None = None,
    ) -> None:
        if usuario_id == ctx.usuario_id:
            toast_warning("No puedes verte como tú mismo")
            return
        try:
            ctx.iniciar_ver_como(
                target_usuario_id=usuario_id,
                target_rol=rol,
                target_nombre=nombre,
                target_institucion_id=institucion_id,
            )
            toast_success(f"Viendo como '{nombre}' (solo lectura)")
            ui.navigate.to("/inicio")
        except Exception as exc:
            logger.error("Error al iniciar 'Ver como' %s: %s", usuario_id, exc)
            toast_error("No se pudo iniciar el modo 'Ver como'")

    def _on_filtros_cambio() -> None:
        _cargar_estado()
        tabla.refresh()

    # -- Tabla refreshable ---
    @ui.refreshable
    def tabla() -> None:
        usuarios = _s["usuarios"]
        if not usuarios:
            empty_state(
                variante="search",
                titulo="No hay usuarios con los filtros actuales",
                descripcion="Ajusta el rol o el estado para ver más resultados.",
            )
            return

        _ROL_CLASES = {
            "admin": "badge-error",
            "director": "badge-purple",
            "coordinador": "badge-info",
            "profesor": "badge-success",
        }

        with ui.element("div").classes("w-full"):
            row_classes = "flex items-center gap-4"

            with ui.element("div").classes(
                "flex items-center gap-4 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Nombre completo").classes("flex-1")
                ui.label("Usuario").classes("w-32")
                ui.label("Institución").classes("w-48")
                ui.label("Rol").classes("w-28")
                ui.label("Estado").classes("w-20")
                ui.label("Acciones").classes("w-56 text-right")

            for u in usuarios:
                rol_str = u.rol.value if hasattr(u.rol, "value") else str(u.rol)
                gestionable = svc.puede_gestionar(ctx.usuario_rol, rol_str)
                with ui.element("div").classes(f"{row_classes} py-2 border-b"):
                    ui.label(u.nombre_completo).classes("flex-1")
                    ui.label(u.usuario).classes("w-32 cell-mono")
                    ui.label(instituciones_opts.get(u.institucion_id, "—")).classes(
                        "w-48 text-truncate"
                    )
                    with ui.element("div").classes("w-28 form-row-center"):
                        status_badge(
                            _ROLES_OPCIONES.get(rol_str, rol_str),
                            _ROL_CLASES.get(rol_str, "badge-neutral").replace("badge-", ""),
                        )
                    with ui.element("div").classes("w-20 form-row-center"):
                        badge_estado_general(bool(u.activo))
                    with ui.element("div").classes("table-row-actions"):
                        if u.id != ctx.usuario_id and u.activo:
                            btn_icon(
                                "visibility",
                                on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str, inst=u.institucion_id: (
                                    _ver_como(uid, nom, r, inst)
                                ),
                                tooltip="Ver como (solo lectura)",
                            ).mark(f"ver-como-{u.usuario}")
                        if gestionable and u.activo:
                            btn_icon(
                                "key",
                                on_click=lambda uid=u.id, nom=u.nombre_completo, un=u.usuario, r=rol_str: (
                                    _resetear_password(uid, nom, un, r)
                                ),
                                tooltip="Restablecer contraseña",
                                variante="secondary",
                            )
                            btn_icon(
                                "person_off",
                                on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str: (
                                    _desactivar_usuario(uid, nom, r)
                                ),
                                tooltip="Desactivar",
                                variante="danger",
                            )
                        if gestionable and not u.activo:
                            btn_icon(
                                "restart_alt",
                                on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str: (
                                    _reactivar_usuario(uid, nom, r)
                                ),
                                tooltip="Reactivar",
                                variante="primary",
                            )
                            btn_icon(
                                "key",
                                on_click=lambda uid=u.id, nom=u.nombre_completo, un=u.usuario, r=rol_str: (
                                    _resetear_password(uid, nom, un, r)
                                ),
                                tooltip="Restablecer contraseña",
                                variante="secondary",
                            )

    # -- Contenido principal ---
    def contenido() -> None:
        with ui.element("div").classes("page-stack"), ui.element("div").classes("panel-card"):
                with ui.row().classes("gap-4 items-center justify-between flex-wrap mb-4"), ui.row().classes("form-row-center-md"):
                        ui.label("Filtros:").classes("text-sm font-semibold")
                        roles_opts = {None: "Todos los roles"}
                        roles_opts.update(_ROLES_OPCIONES)
                        filter_select(
                            label="Rol",
                            options=roles_opts,
                            value=None,
                            on_change=lambda e: (
                                presenter.set_filtro_rol(e.value),
                                _on_filtros_cambio(),
                            ),
                            cls_extra="w-40",
                        )
                        filter_select(
                            label="Institución",
                            options=instituciones_opts,
                            value=None,
                            on_change=lambda e: (
                                presenter.set_filtro_institucion(e.value),
                                _on_filtros_cambio(),
                            ),
                            cls_extra="w-52",
                        )
                        ui.checkbox(
                            "Solo activos",
                            value=_s["filtro_activos"],
                            on_change=lambda e: (
                                presenter.set_filtro_activos(e.value),
                                _on_filtros_cambio(),
                            ),
                        )
                        status_badge(str(len(_s["usuarios"])), "primary")
                        btn_icon(
                            "refresh",
                            on_click=lambda: (_cargar_estado(), tabla.refresh()),
                            tooltip="Recargar",
                        )

                tabla()

    app_layout(
        ctx,
        contenido,
        page_titulo="Usuarios de la Plataforma",
        page_subtitulo="Auditoría e impersonación — gestión de directores",
        page_icono=Icons.TEACHERS,
    )


__all__ = ["usuarios_page"]
