"""
src/interface/pages/director/gestion_usuarios.py
=================================================
Gestión de equipo docente — página exclusiva del director.
Ruta: /director/equipo
Acceso: director

El director crea, gestiona y asigna roles a los coordinadores y profesores
de su institución. Esta es la puerta de entrada para configurar el equipo
después de que el admin ha creado la institución y provisionado al director.

Funcionalidades:
 - Listar coordinadores y profesores del tenant.
 - Crear nuevos usuarios (coordinador / profesor).
 - Cambiar rol entre coordinador y profesor.
 - Restablecer contraseñas (genera temporal si se deja vacío).
 - Desactivar / reactivar cuentas.
 - Mostrar contraseña temporal tras creación (para comunicarla).

El RBAC real vive en el servicio; la vista solo consulta la política para
mostrar u ocultar controles (defensa en profundidad).
"""

from __future__ import annotations

import logging

from nicegui import ui
from pydantic import ValidationError

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
from src.interface.design.components.buttons import btn_icon, btn_primary
from src.interface.design.components.form_fields import filter_select
from src.interface.design.layout import app_layout
from src.interface.design.styles.tokens import Icons
from src.interface.presenters.director.gestion_usuarios_presenter import (
    GestionUsuariosPresenter,
)
from src.services.usuario_service import FiltroUsuariosDTO, NuevoUsuarioDTO

logger = logging.getLogger("DIRECTOR.EQUIPO")

_PREFIJO_VALUE_ERROR = "Value error, "


def _formatear_errores_validacion(exc: ValidationError) -> str:
    mensajes: list[str] = []
    for err in exc.errors():
        msg = str(err.get("msg", "")).strip()
        msg = msg.removeprefix(_PREFIJO_VALUE_ERROR)
        if msg and msg not in mensajes:
            mensajes.append(msg)
    return " ".join(mensajes) or "Revisa los datos del formulario."


_ROLES_EQUIPO = {
    "coordinador": "Coordinador",
    "profesor": "Profesor",
}


def gestion_usuarios_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    svc = Container.usuario_service()
    roles_asignables = svc.roles_asignables(ctx.usuario_rol)
    roles_disponibles_crear = {
        r: _ROLES_EQUIPO[r] for r in _ROLES_EQUIPO if r in roles_asignables
    }
    _rol_crear_default = "profesor"

    logger.info("Equipo docente: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # -- Estado mutable ---
    presenter = GestionUsuariosPresenter()
    _s = presenter.estado

    # -- Carga de datos ---
    def _cargar_estado() -> None:
        try:
            filtro = FiltroUsuariosDTO(
                rol=_s["filtro_rol"] or None,
                solo_activos=_s["filtro_activos"],
            )
            presenter.set_usuarios(Container.usuario_service().listar_resumenes(filtro))
        except Exception as exc:
            logger.error("Error al cargar equipo: %s", exc)
            presenter.set_usuarios([])

    _cargar_estado()

    # -- Acciones ---

    def _mostrar_credenciales(nombre: str, username: str, password_temporal: str | None) -> None:
        """Muestra un diálogo con las credenciales del usuario recién creado."""
        with ui.dialog() as dlg, ui.card().classes("p-6 max-w-md"):
            ui.label("Usuario creado").classes("text-lg font-semibold mb-2")
            ui.label(f"Se ha creado la cuenta de {nombre}.").classes("text-sm mb-4")

            with ui.element("div").classes("space-y-2 mb-4"):
                with ui.element("div").classes("flex items-center gap-2"):
                    ui.label("Usuario:").classes("text-sm font-medium w-24")
                    ui.label(username).classes("cell-mono text-sm")
                if password_temporal:
                    with ui.element("div").classes("flex items-center gap-2"):
                        ui.label("Contraseña:").classes("text-sm font-medium w-24")
                        ui.label(password_temporal).classes("cell-mono text-sm")
                    ui.label(
                        "Comunique estas credenciales al usuario. "
                        "Deberá cambiar la contraseña en su primer inicio de sesión."
                    ).classes("text-xs text-dim mt-2")
                else:
                    ui.label(
                        "Se usó la contraseña indicada. "
                        "El usuario deberá cambiarla en su primer inicio de sesión."
                    ).classes("text-xs text-dim mt-2")

            btn_primary("Entendido", on_click=dlg.close, size="sm")
        dlg.open()

    def _abrir_crear_usuario() -> None:
        def _crear(datos: dict) -> bool | None:
            rol_str = datos.get("rol", _rol_crear_default)
            try:
                dto = NuevoUsuarioDTO(
                    usuario=datos.get("usuario", ""),
                    nombre_completo=datos.get("nombre_completo", ""),
                    rol=rol_str,
                    email=datos.get("email"),
                    telefono=datos.get("telefono"),
                    password=datos.get("password") or None,
                )
                resultado = svc.crear_usuario(
                    dto,
                    creado_por_id=ctx.usuario_id,
                    actor_rol=ctx.usuario_rol,
                )
                toast_success(f"Usuario '{dto.usuario}' creado")
                _cargar_estado()
                tabla.refresh()
                _mostrar_credenciales(
                    dto.nombre_completo,
                    dto.usuario,
                    resultado.password_temporal,
                )
            except ValidationError as exc:
                toast_warning(_formatear_errores_validacion(exc))
                return False
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al crear usuario: %s", exc)
                toast_error("Error al crear el usuario")
                return False

        form_dialog(
            titulo="Nuevo miembro del equipo",
            campos=[
                {
                    "key": "nombre_completo",
                    "label": "Nombre completo",
                    "tipo": "text",
                    "requerido": True,
                    "minlength": 3,
                    "normalizar": "titulo",
                },
                {
                    "key": "usuario",
                    "label": "Nombre de usuario",
                    "tipo": "text",
                    "requerido": True,
                    "minlength": 3,
                    "normalizar": "minusculas",
                    "hint": "Sin espacios, será el login",
                },
                {
                    "key": "password",
                    "label": "Contraseña inicial",
                    "tipo": "password",
                    "hint": "Dejar vacío genera una temporal segura",
                },
                {
                    "key": "rol",
                    "label": "Rol",
                    "tipo": "select",
                    "opciones": roles_disponibles_crear,
                    "valor": _rol_crear_default,
                },
                {
                    "key": "email",
                    "label": "Email (opcional)",
                    "tipo": "email",
                    "normalizar": "minusculas",
                },
                {
                    "key": "telefono",
                    "label": "Teléfono (opcional)",
                    "tipo": "text",
                },
            ],
            on_submit=_crear,
            texto_submit="Crear usuario",
            max_width="max-w-lg",
            columnas=2,
        )

    def _confirmar_desactivar(usuario_id: int, nombre: str) -> None:
        try:
            svc.desactivar(
                usuario_id,
                desactivado_por_id=ctx.usuario_id,
                actor_rol=ctx.usuario_rol,
            )
            toast_success(f"'{nombre}' desactivado")
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
            toast_success(f"'{nombre}' reactivado")
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
                temporal = svc.resetear_password(
                    usuario_id,
                    nueva,
                    actor_rol=ctx.usuario_rol,
                    reset_por_id=ctx.usuario_id,
                )
                if temporal:
                    _mostrar_credenciales(nombre, username, temporal)
                else:
                    toast_success(f"Contraseña de '{nombre}' restablecida")
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
                    "hint": "Dejar vacío genera una temporal segura",
                },
            ],
            on_submit=_aplicar,
            texto_submit="Restablecer",
            max_width="max-w-sm",
        )

    def _cambiar_rol(usuario_id: int, nombre: str, rol_actual: str) -> None:
        if not svc.puede_gestionar(ctx.usuario_rol, rol_actual):
            toast_warning("No tienes permiso para cambiar el rol de este usuario")
            return
        if not roles_asignables:
            toast_warning("Tu rol no puede asignar roles")
            return

        opciones_rol = {
            r: _ROLES_EQUIPO[r] for r in _ROLES_EQUIPO if r in roles_asignables
        }
        valor_default = rol_actual if rol_actual in opciones_rol else next(iter(opciones_rol))

        def _aplicar(datos: dict) -> bool | None:
            try:
                nuevo_rol = datos.get("rol", rol_actual)
                svc.cambiar_rol(
                    usuario_id,
                    nuevo_rol,
                    cambiado_por_id=ctx.usuario_id,
                    actor_rol=ctx.usuario_rol,
                )
                toast_success(f"Rol de '{nombre}' actualizado a '{_ROLES_EQUIPO.get(nuevo_rol, nuevo_rol)}'")
                _cargar_estado()
                tabla.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al cambiar rol %s: %s", usuario_id, exc)
                toast_error("Error al cambiar el rol")
                return False

        form_dialog(
            titulo=f"Cambiar rol de '{nombre}'",
            campos=[
                {
                    "key": "rol",
                    "label": "Nuevo rol",
                    "tipo": "select",
                    "opciones": opciones_rol,
                    "valor": valor_default,
                    "requerido": True,
                },
            ],
            on_submit=_aplicar,
            texto_submit="Cambiar rol",
            max_width="max-w-sm",
        )

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
                descripcion="Crea tu primer docente o coordinador con el botón de arriba.",
            )
            return

        _ROL_CLASES = {
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
                ui.label("Rol").classes("w-28")
                ui.label("Estado").classes("w-20")
                ui.label("Acciones").classes("w-56 text-right")

            for u in usuarios:
                rol_str = u.rol.value if hasattr(u.rol, "value") else str(u.rol)
                gestionable = svc.puede_gestionar(ctx.usuario_rol, rol_str)
                with ui.element("div").classes(f"{row_classes} py-2 border-b"):
                    ui.label(u.nombre_completo).classes("flex-1")
                    ui.label(u.usuario).classes("w-32 cell-mono")
                    with ui.element("div").classes("w-28 form-row-center"):
                        status_badge(
                            _ROLES_EQUIPO.get(rol_str, rol_str),
                            _ROL_CLASES.get(rol_str, "badge-neutral").replace("badge-", ""),
                        )
                    with ui.element("div").classes("w-20 form-row-center"):
                        badge_estado_general(bool(u.activo))
                    with ui.element("div").classes("table-row-actions"):
                        if gestionable and u.activo:
                            btn_icon(
                                "manage_accounts",
                                on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str: (
                                    _cambiar_rol(uid, nom, r)
                                ),
                                tooltip="Cambiar rol",
                            )
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
        with ui.element("div").classes("page-stack"):
            with ui.element("div").classes("panel-card"):
                with ui.row().classes("gap-4 items-center justify-between flex-wrap mb-4"):
                    with ui.row().classes("form-row-center-md"):
                        ui.label("Filtros:").classes("text-sm font-semibold")
                        roles_opts = {None: "Todos los roles"}
                        roles_opts.update(_ROLES_EQUIPO)
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

                    btn_primary(
                        "Nuevo usuario",
                        on_click=_abrir_crear_usuario,
                        icon="person_add",
                        size="sm",
                    )

                tabla()

    app_layout(
        ctx,
        contenido,
        page_titulo="Equipo Docente",
        page_subtitulo="Coordinadores y profesores de tu institución",
        page_icono=Icons.TEACHERS,
    )


__all__ = ["gestion_usuarios_page"]
