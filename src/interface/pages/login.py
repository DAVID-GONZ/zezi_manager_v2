"""
login.py — Página de inicio de sesión de ZECI Manager v2.0
"""
from __future__ import annotations

import logging

from nicegui import app, ui

from container import Container
from src.interface.design.theme import ThemeManager
from src.interface.design.components.buttons import btn_primary

logger = logging.getLogger("LOGIN")


# page-delegate: ruta registrada en main.py vía registrar_pagina (paso_35)
def login_page() -> None:
    # Fondo usando la clase del design system
    ui.add_body_html('<style>body{margin:0;padding:0;}</style>', shared=True)

    with ui.element("div").classes("andes-login-bg w-full"):
        # Reemplazo de ui.card() por ui.element("div") para control CSS absoluto
        with ui.element("div").classes("andes-login-card"):
            
            # ── Encabezado ──────────────────────────────────────────────────
            with ui.element("div").classes("andes-login-logo"):
                with ui.element("div").classes("andes-login-icon-wrap"):
                    ThemeManager.icono("school", size=40, color="var(--color-primary)")
                ui.label("Gestor Docente").classes("andes-login-logo-title")
                ui.label("Sistema de Gestión Educativa").classes("andes-login-logo-subtitle")

            # ── Formulario ───────────────────────────────────────────────────
            with ui.column().classes("w-full gap-4"):
                usuario_input = (
                    ui.input(label="Usuario", placeholder="nombre.apellido")
                    .classes("w-full andes-input")
                    .props("outlined") # Eliminado 'dense' para dar mayor altura
                )

                password_input = (
                    ui.input(label="Contraseña", password=True, password_toggle_button=True)
                    .classes("w-full andes-input")
                    .props("outlined")
                )

            # Contenedor para el error
            error_container = ui.row().classes("andes-alert andes-alert-error w-full items-center hidden no-wrap gap-2 u-mt-md login-alert-banner")
            with error_container:
                ThemeManager.icono("error", size=20, color="inherit")
                error_label = ui.label("").classes("login-alert-text")

            # ── Lógica de autenticación ──────────────────────────────────────
            def intentar_login() -> None:
                error_container.classes(add="hidden")
                error_label.set_text("")
                
                login_btn.disable()
                login_btn.props("loading")

                def on_finish():
                    login_btn.enable()
                    login_btn.props(remove="loading")

                nombre_usuario = usuario_input.value.strip() if usuario_input.value else ""
                contrasena     = password_input.value if password_input.value else ""

                if not nombre_usuario or not contrasena:
                    error_label.set_text("Completa usuario y contraseña.")
                    error_container.classes(remove="hidden")
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

                    app.storage.user["autenticado"]    = True
                    app.storage.user["usuario_id"]     = user_db.id
                    app.storage.user["usuario_nombre"] = user_db.nombre_completo
                    app.storage.user["usuario_rol"]    = rol_str

                    from src.interface.context.session_context import SessionContext
                    ctx = SessionContext(
                        usuario_id     = user_db.id,
                        usuario_nombre = user_db.nombre_completo,
                        usuario_rol    = rol_str,
                        # Multi-tenant (paso_24): institución del usuario.
                        institucion_id = getattr(user_db, "institucion_id", None),
                    )

                    ctx = Container.inicializar_contexto(ctx)
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
                        error_label.set_text("Tu cuenta está desactivada.")
                    else:
                        error_label.set_text("Usuario o contraseña incorrectos.")
                    error_container.classes(remove="hidden")
                    on_finish()

                except Exception:
                    logger.exception("Error inesperado en login")
                    error_label.set_text("Error del sistema. Intenta de nuevo.")
                    error_container.classes(remove="hidden")
                    on_finish()

            password_input.on("keydown.enter", lambda _: intentar_login())

            # Botón instanciado mediante la fábrica
            login_btn = btn_primary("Iniciar sesión", on_click=intentar_login, size="lg").classes("w-full u-mt-lg")

            # ── Pie ──────────────────────────────────────────────────────────
            ui.label("© 2026 Gestor Docente").classes("andes-login-footer w-full")


__all__ = ["login_page"]