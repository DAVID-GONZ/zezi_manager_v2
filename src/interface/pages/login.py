"""
login.py — Página de inicio de sesión de ZECI Manager v2.0
"""
from __future__ import annotations

import logging

from nicegui import app, ui

from container import Container
from src.interface.design.components.buttons import btn_primary
from src.interface.design.theme import ThemeManager

logger = logging.getLogger("LOGIN")

# page-delegate: ruta registrada en main.py vía registrar_pagina (PUBLICO)
def login_page() -> None:
    ui.add_body_html('<style>body{margin:0;padding:0;}</style>', shared=True)

    with ui.element("div").classes("andes-login-bg w-full"):
    
        with ui.element("div").classes("andes-login-card") as login_card_el:
            
            # ── Encabezado ──────────────────────────────────────────────────
            with ui.element("div").classes("andes-login-logo"):
                with ui.element("div").classes("andes-login-icon-wrap"):
                    ThemeManager.icono("school", size=40, color="var(--color-primary)")
                ui.label("Gestor Docente").classes("andes-login-logo-title")
                ui.label("Sistema de Gestión Educativa").classes("andes-login-logo-subtitle")

            # ── Formulario ───────────────────────────────────────────────────
            with ui.column().classes("w-full gap-4"):
                usuario_input = (
                    ui.input(label="Usuario", placeholder="usuario")
                    .classes("w-full andes-input")
                    .props("outlined") 
                )

                password_input = (
                    ui.input(label="Contraseña", placeholder="Contraseña", password=True)
                    .classes("w-full andes-input")
                    .props("outlined")
                )

            # ── Toggle de contraseña con ícono del design system ─────────────
            _pwd_visible = [False]

            def _pwd_icon_html(visible: bool) -> str:
                icono = "visibility" if visible else "visibility_off"
                fvs = "font-variation-settings:'FILL' 0,'wght' 300,'GRAD' 0,'opsz' 20;"
                style = (
                    fvs
                    + "font-size:20px;line-height:1;vertical-align:middle;"
                    + "user-select:none;color:var(--color-text-secondary);"
                    + "cursor:pointer;transition:color 0.15s;"
                )
                return f'<span class="material-symbols-rounded" style="{style}">{icono}</span>'

            with password_input.add_slot("append"):
                _pwd_toggle_el = ui.html(_pwd_icon_html(False))

            def _toggle_pwd() -> None:
                _pwd_visible[0] = not _pwd_visible[0]
                password_input.props("type=text" if _pwd_visible[0] else "type=password")
                _pwd_toggle_el.content = _pwd_icon_html(_pwd_visible[0])

            _pwd_toggle_el.on("click", _toggle_pwd)

            # Contenedor para el error
            error_container = ui.row().classes("alert alert--error form-row-center u-mt-md login-alert-banner hidden")
            with error_container:
                ThemeManager.icono("error", size=20, color="inherit")
                error_label = ui.label("").classes("login-alert-text")

            # ── Lógica de autenticación ──────────────────────────────────────
            def intentar_login() -> None:
                error_container.classes(add="hidden", remove="andes-login-alert-in andes-login-error-shake")
                error_label.set_text("")
                usuario_input.props(remove="error")
                password_input.props(remove="error")

                login_btn.disable()
                login_btn.props("loading")
                usuario_input.disable()
                password_input.disable()
                login_card_el.classes(add="andes-login-loading")

                def on_finish():
                    login_btn.enable()
                    login_btn.props(remove="loading")
                    usuario_input.enable()
                    password_input.enable()
                    login_card_el.classes(remove="andes-login-loading")

                nombre_usuario = usuario_input.value.strip() if usuario_input.value else ""
                contrasena     = password_input.value if password_input.value else ""

                if not nombre_usuario or not contrasena:
                    error_label.set_text("Completa usuario y contraseña.")
                    error_container.classes(remove="hidden", add="andes-login-alert-in andes-login-error-shake")
                    if not nombre_usuario:
                        usuario_input.props("error")
                    if not contrasena:
                        password_input.props("error")
                    on_finish()
                    return

                # A1 — throttle/lockout: si el username está bloqueado por exceso
                # de fallos, abortar sin tocar el servicio de auth.
                from src.services import login_throttle
                bloqueado, segundos = login_throttle.estado_bloqueo(nombre_usuario)
                if bloqueado:
                    error_label.set_text(
                        f"Demasiados intentos. Espera {segundos} s e inténtalo de nuevo."
                    )
                    error_container.classes(remove="hidden", add="andes-login-alert-in andes-login-error-shake")
                    usuario_input.props("error")
                    on_finish()
                    return

                try:
                    svc_auth = Container.auth_service()
                    user_db = svc_auth.autenticar_usuario(
                        nombre_usuario, contrasena
                    )

                    rol_str = (
                        user_db.rol.value
                        if hasattr(user_db.rol, "value")
                        else str(user_db.rol)
                    )

                    # A1 — credenciales correctas: limpiar el contador de fallos.
                    login_throttle.registrar_exito(nombre_usuario)

                    app.storage.user["autenticado"]    = True
                    app.storage.user["usuario_id"]     = user_db.id
                    app.storage.user["usuario_nombre"] = user_db.nombre_completo
                    app.storage.user["usuario_rol"]    = rol_str
                    # A2 — cambio forzado: el guard fuerza /cambiar-password si
                    # el flag está activo. Lo lee desde la entidad autenticada.
                    app.storage.user["debe_cambiar_password"] = bool(
                        getattr(user_db, "debe_cambiar_password", False)
                    )

                    from src.interface.context.session_context import SessionContext
                    ctx = SessionContext(
                        usuario_id     = user_db.id,
                        usuario_nombre = user_db.nombre_completo,
                        usuario_rol    = rol_str,
                        # Multi-tenant (paso_24): institución del usuario.
                        institucion_id = getattr(user_db, "institucion_id", None),
                    )

                    ctx = Container.inicializar_contexto(ctx)

                    # mejora_09b — sembrar flag de configuración inicial del tenant.
                    # admin → True (nunca se le aplica el gate; su inst_id suele ser None).
                    # resto → valor real del tenant, con fail-open a True ante cualquier error.
                    _inst_id_login = getattr(user_db, "institucion_id", None)
                    if rol_str == "admin":
                        _config_completa = True
                    else:
                        try:
                            if _inst_id_login is None:
                                _config_completa = True
                            else:
                                _inst_obj = Container.institucion_service().get(_inst_id_login)
                                _config_completa = bool(_inst_obj.configuracion_inicial_completa)
                        except Exception:
                            _config_completa = True  # fail-open: no encerrar al usuario
                    ctx.institucion_config_completa = _config_completa
                    app.storage.user["institucion_config_completa"] = _config_completa

                    ctx.guardar()

                    try:
                        from src.services.auditoria_service import (
                            EventoSesion,
                            TipoEventoSesion,
                        )
                        Container.auditoria_service().registrar_evento(
                            EventoSesion(
                                usuario     = user_db.usuario,
                                usuario_id  = user_db.id,
                                tipo_evento = TipoEventoSesion.LOGIN_EXITOSO,
                            )
                        )
                    except Exception as audit_exc:
                        logger.warning("No se pudo registrar evento de login: %s", audit_exc)

                    logger.info(
                        "Login exitoso: usuario_id=%s rol=%s año=%s periodo=%s",
                        user_db.id, rol_str, ctx.anio_nombre, ctx.periodo_nombre,
                    )
                    ui.navigate.to("/inicio")

                except ValueError as exc:
                    codigo = str(exc)
                    if codigo == "cuenta_inactiva":
                        # Credenciales válidas pero cuenta desactivada: no es un
                        # intento de fuerza bruta, no cuenta para el throttle.
                        error_label.set_text("Tu cuenta está desactivada.")
                    else:
                        # A1 — credenciales inválidas: contar el fallo (puede
                        # disparar el bloqueo) y auditar el evento ya existente.
                        login_throttle.registrar_fallo(nombre_usuario)
                        try:
                            from src.services.auditoria_service import (
                                EventoSesion,
                                TipoEventoSesion,
                            )
                            Container.auditoria_service().registrar_evento(
                                EventoSesion(
                                    usuario     = nombre_usuario,
                                    tipo_evento = TipoEventoSesion.LOGIN_FALLIDO,
                                )
                            )
                        except Exception as audit_exc:
                            logger.warning(
                                "No se pudo registrar login fallido: %s", audit_exc
                            )
                        usuario_input.props("error")
                        password_input.props("error")
                        error_label.set_text("Usuario o contraseña incorrectos.")
                    error_container.classes(remove="hidden", add="andes-login-alert-in andes-login-error-shake")
                    on_finish()

                except Exception:
                    logger.exception("Error inesperado en login")
                    error_label.set_text("Error del sistema. Intenta de nuevo.")
                    error_container.classes(remove="hidden", add="andes-login-alert-in andes-login-error-shake")
                    on_finish()

            password_input.on("keydown.enter", lambda _: intentar_login())
            usuario_input.on("keydown", lambda _: usuario_input.props(remove="error"))
            password_input.on("keydown", lambda _: password_input.props(remove="error"))

            # Botón instanciado mediante la fábrica
            login_btn = btn_primary("Iniciar sesión", on_click=intentar_login, size="lg").classes("w-full u-mt-lg")

            # ── Pie ──────────────────────────────────────────────────────────
            ui.label("© 2026 by LDGV").classes("andes-login-footer w-full")


__all__ = ["login_page"]