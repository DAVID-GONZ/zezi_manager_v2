"""
login.py — Página de inicio de sesión de ZECI Manager v2.0

Sin layout de app (no hay sidebar ni topbar): pantalla completa centrada.
Valida credenciales usando AuthenticationService + repositorio de usuario.

Ajustes NiceGUI 3.x:
  - Icono "school" via ThemeManager.icono() en vez de ui.element().text()
  - Mensajes de error actualizados con label.set_text() para forzar refresh
  - ui.input() en modo password: password=True + password_toggle_button=True

Encapsulamiento:
  - La vista NO accede a svc_usuario._repo ni a ningún repositorio directamente.
  - Toda la lógica de autenticación (lookup, verificación, estado de cuenta)
    vive en IAuthenticationService.autenticar_usuario().
  - login.py solo gestiona el formulario, los mensajes de error y la sesión.
"""
from __future__ import annotations

import logging

from nicegui import app, ui

from container import Container
from src.interface.design.theme import ThemeManager

logger = logging.getLogger("LOGIN")


def login_page() -> None:
    """
    Página de login — sin layout de app (no hay sidebar).
    Valida credenciales con AuthenticationService + UsuarioRepository.

    Flujo de autenticación:
        1. Buscar usuario por nombre de usuario en la BD.
        2. Verificar el hash de contraseña con BcryptAuthService.
        3. Comprobar que la cuenta está activa.
        4. Guardar sesión en app.storage.user y redirigir a /inicio.
    """
    # Fondo usando la clase del design system
    ui.add_body_html('<style>body{margin:0;padding:0;}</style>', shared=True)

    with ui.element("div").classes("andes-login-bg w-full"):
        with ui.card().classes("andes-login-card"):
            # ── Encabezado ──────────────────────────────────────────────────
            with ui.column().classes("andes-login-logo items-center w-full"):
                ThemeManager.icono("school", size=56, color="var(--color-primary)")
                ui.label("Gestor Docente").classes("andes-login-logo-title")
                ui.label("Sistema de Gestión Educativa").classes("andes-login-logo-subtitle")

            # ── Formulario ───────────────────────────────────────────────────
            usuario_input = (
                ui.input(label="Usuario", placeholder="nombre.apellido")
                .classes("w-full andes-input")
                .props("outlined dense")
            )

            password_input = (
                ui.input(label="Contraseña", password=True, password_toggle_button=True)
                .classes("w-full andes-input")
                .props("outlined dense")
                .style("margin-top:var(--space-md);")
            )

            # Contenedor para el error
            error_container = ui.row().classes("andes-alert andes-alert-error w-full items-center hidden").style("margin-top:var(--space-md); padding: var(--space-sm);")
            with error_container:
                ThemeManager.icono("error", size=20, color="inherit")
                error_label = ui.label("").style("font-size:var(--font-size-small); font-weight: 500;")

            # ── Lógica de autenticación ──────────────────────────────────────
            def intentar_login() -> None:
                error_container.classes(add="hidden")
                error_label.set_text("")
                
                login_btn.disable()
                login_btn.props("loading")

                def on_finish():
                    login_btn.enable()
                    login_btn.props(remove="loading")

                nombre_usuario = usuario_input.value.strip()
                contrasena     = password_input.value

                # Validación de campos vacíos
                if not nombre_usuario or not contrasena:
                    error_label.set_text("Completa usuario y contraseña.")
                    error_container.classes(remove="hidden")
                    on_finish()
                    return

                try:
                    svc_auth = Container.auth_service()

                    user_db = svc_auth.autenticar_usuario(nombre_usuario, contrasena)

                    # Guardar sesión en NiceGUI storage (server-side por cookie)
                    app.storage.user["usuario_id"]     = user_db.id
                    app.storage.user["usuario_nombre"] = user_db.nombre_completo
                    app.storage.user["usuario_rol"]    = (
                        user_db.rol.value if hasattr(user_db.rol, "value") else str(user_db.rol)
                    )
                    app.storage.user["autenticado"] = True

                    logger.info("Login exitoso: usuario_id=%s rol=%s", user_db.id, app.storage.user["usuario_rol"])
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

            # Enter en el campo password también dispara el login
            password_input.on("keydown.enter", lambda _: intentar_login())

            login_btn = ui.button("Iniciar sesión", on_click=intentar_login).classes(
                "btn-primary w-full"
            ).props("unelevated").style("margin-top:var(--space-lg); height: 44px; font-size: 15px; font-weight: 600; border-radius: var(--radius-md);")

            # ── Pie ──────────────────────────────────────────────────────────
            ui.label("© 2026 Gestor Docente").style(
                "color:var(--color-text-disabled);"
                "font-size:12px;"
                "text-align:center;"
                "margin-top:var(--space-xl);"
                "width:100%;"
                "letter-spacing: 0.5px;"
            )


__all__ = ["login_page"]
