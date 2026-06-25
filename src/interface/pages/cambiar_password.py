"""
cambiar_password.py — Cambio forzado de contraseña (A2 — seguridad_01).
=======================================================================
Página suelta (patrón de login.py) que el route_guard fuerza cuando la sesión
tiene `debe_cambiar_password` activo: cuentas creadas/reseteadas con contraseña
temporal deben re-elegir su clave en el primer acceso.

Regla de capas:
  Esta página NO importa src.domain.models.*; pasa primitivos al servicio
  (Container.usuario_service().cambiar_password). Usa solo NiceGUI, Container
  y el design system.

Flujo:
  1. El usuario introduce su contraseña actual (la temporal) y la nueva (x2).
  2. Validaciones de UI (no vacías, coinciden, longitud mínima).
  3. usuario_service().cambiar_password(...) verifica la actual y persiste la
     nueva; el servicio limpia debe_cambiar_password en la BD.
  4. Se limpia el flag en app.storage.user y se navega a /inicio.
"""
from __future__ import annotations

import logging

from nicegui import app, ui

from container import Container
from src.interface.design.theme import ThemeManager
from src.interface.design.components.buttons import btn_primary

logger = logging.getLogger("CAMBIAR_PASSWORD")

_LONGITUD_MINIMA = 8


# page-delegate: ruta registrada en main.py vía registrar_pagina (T6)
def cambiar_password_page() -> None:
    ui.add_body_html('<style>body{margin:0;padding:0;}</style>', shared=True)

    with ui.element("div").classes("andes-login-bg w-full"):
        with ui.element("div").classes("andes-login-card"):

            # ── Encabezado ──────────────────────────────────────────────────
            with ui.element("div").classes("andes-login-logo"):
                with ui.element("div").classes("andes-login-icon-wrap"):
                    ThemeManager.icono("lock_reset", size=40, color="var(--color-primary)")
                ui.label("Cambia tu contraseña").classes("andes-login-logo-title")
                ui.label(
                    "Por seguridad, debes elegir una nueva contraseña para continuar."
                ).classes("andes-login-logo-subtitle")

            # ── Formulario ───────────────────────────────────────────────────
            with ui.column().classes("w-full gap-4"):
                actual_input = (
                    ui.input(label="Contraseña actual", password=True,
                             password_toggle_button=True)
                    .classes("w-full andes-input")
                    .props("outlined")
                )
                nueva_input = (
                    ui.input(label="Nueva contraseña", password=True,
                             password_toggle_button=True)
                    .classes("w-full andes-input")
                    .props("outlined")
                )
                confirmar_input = (
                    ui.input(label="Confirmar nueva contraseña", password=True,
                             password_toggle_button=True)
                    .classes("w-full andes-input")
                    .props("outlined")
                )

            # ── Banner de error ──────────────────────────────────────────────
            error_container = ui.row().classes(
                "andes-alert andes-alert-error w-full items-center hidden "
                "no-wrap gap-2 u-mt-md login-alert-banner"
            )
            with error_container:
                ThemeManager.icono("error", size=20, color="inherit")
                error_label = ui.label("").classes("login-alert-text")

            def _mostrar_error(mensaje: str) -> None:
                error_label.set_text(mensaje)
                error_container.classes(remove="hidden")

            # ── Lógica de cambio ─────────────────────────────────────────────
            def intentar_cambio() -> None:
                error_container.classes(add="hidden")
                error_label.set_text("")

                cambiar_btn.disable()
                cambiar_btn.props("loading")

                def on_finish() -> None:
                    cambiar_btn.enable()
                    cambiar_btn.props(remove="loading")

                actual    = actual_input.value or ""
                nueva     = nueva_input.value or ""
                confirmar = confirmar_input.value or ""

                if not actual or not nueva or not confirmar:
                    _mostrar_error("Completa todos los campos.")
                    on_finish()
                    return
                if nueva != confirmar:
                    _mostrar_error("La nueva contraseña y su confirmación no coinciden.")
                    on_finish()
                    return
                if len(nueva) < _LONGITUD_MINIMA:
                    _mostrar_error(
                        f"La nueva contraseña debe tener al menos {_LONGITUD_MINIMA} caracteres."
                    )
                    on_finish()
                    return
                if nueva == actual:
                    _mostrar_error("La nueva contraseña debe ser distinta de la actual.")
                    on_finish()
                    return

                usuario_id = app.storage.user.get("usuario_id")
                if not usuario_id:
                    ui.navigate.to("/login")
                    return

                try:
                    Container.usuario_service().cambiar_password(
                        usuario_id, actual, nueva
                    )
                    # El servicio ya limpió el flag en la BD; limpiarlo también en
                    # la sesión para que el guard deje de forzar esta página.
                    app.storage.user["debe_cambiar_password"] = False
                    logger.info("Cambio de contraseña forzado completado: usuario_id=%s", usuario_id)
                    ui.navigate.to("/inicio")
                except ValueError as exc:
                    codigo = str(exc)
                    if "no es correcta" in codigo:
                        _mostrar_error("La contraseña actual no es correcta.")
                    else:
                        _mostrar_error("No se pudo cambiar la contraseña. Revisa los datos.")
                    on_finish()
                except Exception:
                    logger.exception("Error inesperado al cambiar contraseña")
                    _mostrar_error("Error del sistema. Intenta de nuevo.")
                    on_finish()

            confirmar_input.on("keydown.enter", lambda _: intentar_cambio())

            cambiar_btn = btn_primary(
                "Guardar y continuar", on_click=intentar_cambio, size="lg"
            ).classes("w-full u-mt-lg")

            # ── Pie: salir si no quiere continuar ────────────────────────────
            ui.link("Cerrar sesión", "/logout").classes("andes-login-footer w-full")


__all__ = ["cambiar_password_page"]
