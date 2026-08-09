"""
espera_configuracion.py — Página de espera de configuración inicial (mejora_09b).
==================================================================================
Ruta: /espera-configuracion  •  roles: AUTENTICADO

Se muestra a los usuarios (no directores) que intentan entrar a su tenant antes
de que el director complete el wizard de configuración inicial.

El botón "Reintentar" re-evalúa el flag en BD (a través de route_guard, o
navegando a /inicio que el guard ya protege). El director ve un botón adicional
"Ir a la configuración" que lo lleva al wizard.

Página SUELTA (sin app_layout/NAV) — misma estética que login.
"""
from __future__ import annotations

from nicegui import app, ui

from src.interface.design.components.buttons import btn_ghost, btn_primary
from src.interface.design.theme import ThemeManager


# page-delegate: ruta registrada en main.py vía registrar_pagina (mejora_09b)
def espera_configuracion_page() -> None:
    ui.add_body_html('<style>body{margin:0;padding:0;}</style>', shared=True)

    rol = app.storage.user.get("usuario_rol", "")

    with ui.element("div").classes("andes-login-bg w-full"):
        with ui.element("div").classes("wizard-espera-card"):

            # ── Ícono + título ────────────────────────────────────────────────
            with ui.element("div").classes("andes-login-logo"):
                with ui.element("div").classes("andes-login-icon-wrap"):
                    ThemeManager.icono("hourglass_empty", size=48, color="var(--color-primary)")

                ui.label("Institución en configuración").classes("wizard-espera-title")
                ui.label(
                    "El director de tu institución todavía no ha completado la "
                    "configuración inicial. Por favor, espera a que lo haga para "
                    "acceder a la plataforma."
                ).classes("wizard-espera-desc")

            # ── Botones de acción ─────────────────────────────────────────────
            with ui.element("div").classes("u-stack-sm u-mt-lg"):

                # Director: acceso directo al wizard
                if rol == "director":
                    btn_primary(
                        "Ir a la configuración",
                        on_click=lambda: ui.navigate.to("/configuracion-inicial"),
                    ).classes("w-full")

                # Reintentar: vuelve a /inicio; el guard re-evalúa el flag en vivo.
                btn_ghost(
                    "Reintentar",
                    on_click=lambda: ui.navigate.to("/inicio"),
                ).classes("w-full")

            # ── Pie ───────────────────────────────────────────────────────────
            ui.link("Cerrar sesión", "/logout").classes("andes-login-footer w-full")


__all__ = ["espera_configuracion_page"]
