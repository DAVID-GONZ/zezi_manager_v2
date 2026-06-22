"""
src/interface/pages/admin/usuarios.py
======================================
Página de administración de usuarios.
Ruta: /admin/usuarios
Acceso: admin, director

Permite:
 - Listar usuarios con filtros (rol, solo activos).
 - Crear usuario (admin y director, con roles acotados por RBAC).
 - Reactivar / Desactivar usuario (gated por puede_gestionar).
 - Restablecer contraseña (gated por puede_gestionar).
 - Cambiar rol (roles ofrecidos = roles_asignables del actor).

El RBAC real vive en el servicio; la vista solo consulta la política para
mostrar u ocultar controles (defensa en profundidad).
"""
from __future__ import annotations

import logging

from nicegui import ui

from container import Container
from src.interface.context.session_context import SessionContext
from src.interface.design.layout import app_layout
from src.interface.design.tokens import Icons
from src.interface.design.components.buttons import btn_icon, btn_primary
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
from src.services.usuario_service import NuevoUsuarioDTO, FiltroUsuariosDTO
from src.services.institucion_service import NuevaInstitucionDTO

logger = logging.getLogger("ADMIN.USUARIOS")

_ROLES_OPCIONES = {
    "admin":        "Administrador",
    "director":     "Director",
    "coordinador":  "Coordinador",
    "profesor":     "Profesor",
}


# page-delegate: ruta y guard de rol registrados en main.py (paso_35)
def usuarios_page() -> None:
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return

    svc = Container.usuario_service()
    es_admin = ctx.usuario_rol == "admin"
    puede_crear = ctx.usuario_rol in ("admin", "director")

    # ── Scope multi-tenant (paso_24 / frente C paso_28) ───────────────────────
    # - admin: puede filtrar por institución (opciones desde InstitucionService),
    #   "Todas" por defecto. Su sesión NO impone scope (contextvar None), así que
    #   el filtro del selector se pasa explícito.
    # - director: el servicio auto-scopea a SU institución vía el contextvar de
    #   sesión; la página ya no necesita forzar el institucion_id.
    instituciones_opts: dict = {None: "Todas las instituciones"}
    if es_admin:
        try:
            for i in Container.institucion_service().listar():
                instituciones_opts[i.id] = i.nombre
        except Exception as exc:
            logger.error("Error al cargar instituciones: %s", exc)
    # Roles asignables del actor según la política RBAC del servicio (paso_23):
    #   admin    → admin, director.
    #   director → coordinador, profesor.
    roles_asignables = svc.roles_asignables(ctx.usuario_rol)
    roles_disponibles_crear = {
        r: _ROLES_OPCIONES.get(r, r) for r in _ROLES_OPCIONES if r in roles_asignables
    }
    _rol_crear_default = "director" if es_admin else "profesor"

    logger.info("Usuarios admin: %s (%s)", ctx.usuario_nombre, ctx.usuario_rol)

    # ── Estado mutable ────────────────────────────────────────────────────────
    _s: dict = {
        "usuarios":          [],
        "filtro_rol":        None,
        "filtro_activos":    True,
        # admin: institución elegida en el selector (None = todas).
        # director: se ignora; el scope se fuerza a su institución.
        "filtro_institucion": None,
        # Catálogo de instituciones (solo admin). Lista de InstitucionResumenDTO.
        "instituciones":     [],
    }

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _cargar_estado() -> None:
        try:
            # admin: pasa el filtro del selector (None = todas). director: deja
            # institucion_id None y el servicio lo auto-scopea a su institución.
            filtro = FiltroUsuariosDTO(
                rol=_s["filtro_rol"] or None,
                solo_activos=_s["filtro_activos"],
                institucion_id=_s["filtro_institucion"] if es_admin else None,
            )
            _s["usuarios"] = Container.usuario_service().listar_resumenes(filtro)
        except Exception as exc:
            logger.error("Error al cargar usuarios: %s", exc)
            _s["usuarios"] = []

    def _cargar_instituciones() -> None:
        if not es_admin:
            _s["instituciones"] = []
            return
        try:
            _s["instituciones"] = Container.institucion_service().listar()
        except Exception as exc:
            logger.error("Error al cargar instituciones: %s", exc)
            _s["instituciones"] = []

    _cargar_estado()
    _cargar_instituciones()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _abrir_crear_usuario() -> None:
        if not puede_crear:
            toast_warning("No tienes permisos para crear usuarios")
            return

        def _crear(datos: dict) -> "bool | None":
            # El RBAC real lo aplica el servicio vía actor_rol. La vista solo
            # construye el DTO y propaga el rol del actor.
            rol_str = datos.get("rol", _rol_crear_default)
            # Normalización y validación (strip, longitudes, email, rol) las
            # realiza NuevoUsuarioDTO en sus field_validator.
            try:
                dto = NuevoUsuarioDTO(
                    usuario=datos.get("usuario", ""),
                    nombre_completo=datos.get("nombre_completo", ""),
                    rol=rol_str,
                    email=datos.get("email"),
                    password=datos.get("password") or None,
                )
                svc.crear_usuario(
                    dto, creado_por_id=ctx.usuario_id, actor_rol=ctx.usuario_rol
                )
                toast_success(f"Usuario '{dto.usuario}' creado")
                _cargar_estado()
                tabla.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al crear usuario: %s", exc)
                toast_error("Error al crear el usuario")
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
                 "opciones": roles_disponibles_crear,
                 "valor": _rol_crear_default},
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
            svc.desactivar(
                usuario_id, desactivado_por_id=ctx.usuario_id,
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
            titulo          = "Desactivar usuario",
            mensaje         = f"¿Desactivar la cuenta de '{nombre}'? No podrá iniciar sesión.",
            on_confirm      = lambda: _confirmar_desactivar(usuario_id, nombre),
            variante        = "danger",
            texto_confirmar = "Desactivar",
        )

    def _reactivar_usuario(usuario_id: int, nombre: str, rol_actual: str) -> None:
        if not svc.puede_gestionar(ctx.usuario_rol, rol_actual):
            toast_warning("No tienes permiso para reactivar a este usuario")
            return
        try:
            svc.reactivar(
                usuario_id, reactivado_por_id=ctx.usuario_id,
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

    def _resetear_password(usuario_id: int, nombre: str, username: str,
                           rol_actual: str) -> None:
        if not svc.puede_gestionar(ctx.usuario_rol, rol_actual):
            toast_warning("No tienes permiso para restablecer la contraseña de este usuario")
            return

        def _aplicar(datos: dict) -> "bool | None":
            try:
                nueva = datos.get("password") or ""
                svc.resetear_password(
                    usuario_id, nueva, actor_rol=ctx.usuario_rol,
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
            titulo    = f"Restablecer contraseña de '{nombre}'",
            campos    = [
                {"key": "password", "label": "Nueva contraseña", "tipo": "password",
                 "placeholder": f"dejar vacío = usa el username ({username})"},
            ],
            on_submit    = _aplicar,
            texto_submit = "Restablecer",
            max_width    = "max-w-sm",
        )

    def _cambiar_rol(usuario_id: int, nombre: str, rol_actual: str) -> None:
        if not svc.puede_gestionar(ctx.usuario_rol, rol_actual):
            toast_warning("No tienes permiso para cambiar el rol de este usuario")
            return
        if not roles_asignables:
            toast_warning("Tu rol no puede asignar roles")
            return

        opciones_rol = {
            r: _ROLES_OPCIONES.get(r, r) for r in _ROLES_OPCIONES if r in roles_asignables
        }
        valor_default = (
            rol_actual if rol_actual in opciones_rol else next(iter(opciones_rol))
        )

        def _aplicar(datos: dict) -> "bool | None":
            try:
                nuevo_rol = datos.get("rol", rol_actual)
                svc.cambiar_rol(
                    usuario_id, nuevo_rol, cambiado_por_id=ctx.usuario_id,
                    actor_rol=ctx.usuario_rol,
                )
                toast_success(f"Rol actualizado a '{_ROLES_OPCIONES.get(nuevo_rol, nuevo_rol)}'")
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
            titulo    = f"Cambiar rol de '{nombre}'",
            campos    = [
                {"key": "rol", "label": "Nuevo rol *", "tipo": "select",
                 "opciones": opciones_rol,
                 "valor": valor_default,
                 "requerido": True},
            ],
            on_submit    = _aplicar,
            texto_submit = "Cambiar rol",
            max_width    = "max-w-sm",
        )

    def _ver_como(
        usuario_id: int, nombre: str, rol: str,
        institucion_id: int | None = None,
    ) -> None:
        # Solo admin puede impersonar; no puede verse como sí mismo.
        if not es_admin:
            toast_warning("Solo el administrador puede usar 'Ver como'")
            return
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

    # ── Sección refreshable ───────────────────────────────────────────────────
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
            "admin":       "badge-error",
            "director":    "badge-purple",
            "coordinador": "badge-info",
            "profesor":    "badge-success",
        }

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex items-center gap-4 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Nombre completo").classes("flex-1")
                ui.label("Usuario").classes("w-32")
                if es_admin:
                    ui.label("Institución").classes("w-48")
                ui.label("Rol").classes("w-28")
                ui.label("Estado").classes("w-20")
                if puede_crear:
                    ui.label("Acciones").classes("w-56 text-right")

            for u in usuarios:
                rol_str = u.rol.value if hasattr(u.rol, "value") else str(u.rol)
                gestionable = svc.puede_gestionar(ctx.usuario_rol, rol_str)
                with ui.element("div").classes("flex items-center gap-4 p-2 border-b"):
                    ui.label(u.nombre_completo).classes("flex-1")
                    ui.label(u.usuario).classes("w-32 font-mono text-sm")
                    if es_admin:
                        ui.label(
                            instituciones_opts.get(u.institucion_id, "—")
                        ).classes("w-48 text-sm whitespace-nowrap overflow-hidden")
                    with ui.element("div").classes("w-28 flex items-center"):
                        status_badge(
                            _ROLES_OPCIONES.get(rol_str, rol_str),
                            _ROL_CLASES.get(rol_str, "badge-neutral").replace("badge-", ""),
                        )
                    with ui.element("div").classes("w-20 flex items-center"):
                        badge_estado_general(bool(u.activo))
                    if puede_crear:
                        with ui.row().classes("w-56 gap-1 justify-end no-wrap"):
                            if es_admin and u.id != ctx.usuario_id and u.activo:
                                btn_icon("visibility", on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str, inst=u.institucion_id: _ver_como(uid, nom, r, inst), tooltip="Ver como (solo lectura)")
                            if gestionable and u.activo:
                                btn_icon("manage_accounts", on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str: _cambiar_rol(uid, nom, r), tooltip="Cambiar rol")
                                btn_icon("key", on_click=lambda uid=u.id, nom=u.nombre_completo, un=u.usuario, r=rol_str: _resetear_password(uid, nom, un, r), tooltip="Restablecer contraseña", variante="secondary")
                                btn_icon("person_off", on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str: _desactivar_usuario(uid, nom, r), tooltip="Desactivar", variante="danger")
                            if gestionable and not u.activo:
                                btn_icon("restart_alt", on_click=lambda uid=u.id, nom=u.nombre_completo, r=rol_str: _reactivar_usuario(uid, nom, r), tooltip="Reactivar", variante="primary")
                                btn_icon("key", on_click=lambda uid=u.id, nom=u.nombre_completo, un=u.usuario, r=rol_str: _resetear_password(uid, nom, un, r), tooltip="Restablecer contraseña", variante="secondary")

    # ── Instituciones (solo admin) ─────────────────────────────────────────────
    @ui.refreshable
    def lista_instituciones() -> None:
        instituciones = _s["instituciones"]
        if not instituciones:
            empty_state(
                icono="business",
                titulo="Aún no hay instituciones registradas",
                descripcion="Crea la primera institución para gestionar la plataforma.",
            )
            return

        with ui.element("div").classes("w-full"):
            with ui.element("div").classes(
                "flex gap-4 p-2 font-semibold text-sm border-b"
            ):
                ui.label("Institución").classes("flex-1")
                ui.label("Estado").classes("w-24 text-right")

            for inst in instituciones:
                with ui.element("div").classes(
                    "flex items-center gap-4 p-2 border-b"
                ):
                    ui.label(inst.nombre).classes("flex-1")
                    with ui.row().classes("w-24 justify-end"):
                        badge_estado_general(inst.activa)

    def _abrir_crear_institucion() -> None:
        if not es_admin:
            toast_warning("Solo el administrador puede crear instituciones")
            return

        def _crear(datos: dict) -> "bool | None":
            try:
                dto = NuevaInstitucionDTO(
                    nombre=datos.get("nombre", ""),
                    nit=datos.get("nit") or None,
                    codigo=datos.get("codigo") or None,
                )
                Container.institucion_service().crear(dto)
                toast_success(f"Institución '{dto.nombre}' creada")
                _cargar_instituciones()
                lista_instituciones.refresh()
            except ValueError as exc:
                toast_warning(str(exc))
                return False
            except Exception as exc:
                logger.error("Error al crear institución: %s", exc)
                toast_error("Error al crear la institución")
                return False

        form_dialog(
            titulo    = "Nueva institución",
            campos    = [
                {"key": "nombre", "label": "Nombre *", "tipo": "text",
                 "requerido": True, "placeholder": "Colegio San José"},
                {"key": "nit",    "label": "NIT (opcional)", "tipo": "text",
                 "placeholder": "900123456-7"},
                {"key": "codigo", "label": "Código DANE (opcional)", "tipo": "text",
                 "placeholder": "111001000000"},
            ],
            on_submit    = _crear,
            texto_submit = "Crear",
            max_width    = "max-w-md",
        )

    # ── Contenido principal ───────────────────────────────────────────────────
    def contenido() -> None:
        with ui.element("div").classes("page-stack"):

            # ── Panel de instituciones (solo admin) ───────────────────────────
            if es_admin:
                with ui.element("div").classes("panel-card"):
                    with ui.row().classes(
                        "gap-4 items-center justify-between flex-wrap mb-4"
                    ):
                        ui.label("Instituciones").classes("text-base font-semibold")
                        btn_primary(
                            "Nueva institución",
                            on_click=_abrir_crear_institucion,
                            icon="add_business",
                            size="sm",
                        )
                    lista_instituciones()

            with ui.element("div").classes("panel-card"):

                # Barra de herramientas: filtros + acción "Nuevo usuario"
                with ui.row().classes(
                    "gap-4 items-center justify-between flex-wrap mb-4"
                ):
                    with ui.row().classes("gap-4 items-center flex-wrap"):
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
                        if es_admin:
                            ui.select(
                                instituciones_opts,
                                value=None,
                                label="Institución",
                                on_change=lambda e: (
                                    _s.__setitem__("filtro_institucion", e.value),
                                    _on_filtros_cambio(),
                                ),
                            ).classes("w-56")
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

                    if puede_crear:
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
        page_titulo      = "Gestión de Usuarios",
        page_subtitulo   = "Cuentas de usuario y roles del sistema",
        page_icono       = Icons.TEACHERS,
        mostrar_contexto = False,
    )


__all__ = ["usuarios_page"]
