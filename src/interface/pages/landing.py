"""
src/interface/pages/landing.py
==============================
Landing pública de marketing — cara comercial del producto (portal_36).
No usa app_layout; es standalone de marketing.

GATE DE DEPLOY: no publicar a producción sin:
  - seguridad_web_01_tls_proxy (proxy HTTPS)
  - seguridad_web_02_secretos_config (secretos fuera del código)
completados. En desarrollo local no hay restricción.
"""

from __future__ import annotations

from nicegui import ui

from src.domain.modulos import modulos_con_pagina
from src.interface.design.components.buttons import btn_primary, btn_secondary
from src.interface.design.theme import ThemeManager


# page-delegate: ruta registrada en main.py vía registrar_pagina (PUBLICO)
def landing_page() -> None:
    with ui.element("div").classes("mkt-page"):
        # ── Top-bar ──────────────────────────────────────────────────────────
        with ui.element("nav").classes("mkt-topbar"):
            with ui.element("div").classes("mkt-logo-wrap"):
                ThemeManager.icono("school", size=28, color="var(--color-primary)")
                ui.label("Gestor Docente").classes("mkt-logo-name")
            with ui.element("div").classes("mkt-nav"):
                # Solo se enlazan anclas que existen en esta página. `#precios`,
                # `#demo` y `#contacto` apuntaban a secciones inexistentes: se
                # eliminan en vez de dejar enlaces muertos. Inventar esas
                # secciones sería contenido de marketing no aprobado; cuando se
                # aprueben, se añaden aquí junto con su `<section id="…">`.
                ui.link("Características", "#caracteristicas").classes("mkt-nav-link")
            with ui.element("div").classes("mkt-topbar-actions"):
                btn_secondary("Iniciar sesión", lambda: ui.navigate.to("/login"))
                btn_primary("Regístrate", lambda: ui.navigate.to("/login"))

        # ── Hero ─────────────────────────────────────────────────────────────
        with ui.element("section").classes("mkt-hero"):
            with ui.element("div").classes("mkt-hero-content"):
                ui.label("Gestión educativa para instituciones modernas").classes("mkt-hero-title")
                ui.label(
                    "Controla asistencia, evaluaciones y convivencia en un solo lugar. "
                    "Diseñado para docentes, coordinadores y directivos."
                ).classes("mkt-hero-sub")
                btn_primary(
                    "Comenzar gratis",
                    lambda: ui.navigate.to("/login"),
                    size="lg",
                )

        # ── Características ───────────────────────────────────────────────────
        with ui.element("section").classes("mkt-feature-section"):
            el = ui.element("div")
            el.props('id="caracteristicas"')
            with el:
                ui.label("Características").classes("mkt-section-title")
                with ui.element("div").classes("mkt-feature-grid"):
                    for d in modulos_con_pagina():
                        anchor_id = f"caracteristicas-{d.id.value}"
                        card = ui.element("div").classes("mkt-feature-card")
                        card.props(f'id="{anchor_id}"')
                        with card:
                            with ui.element("div").classes("mkt-feature-icon"):
                                ThemeManager.icono(d.icono, size=28, color="var(--color-primary)")
                            ui.label(d.label).classes("mkt-feature-title")
                            ui.label(d.descripcion).classes("mkt-feature-desc")

        # ── Footer ────────────────────────────────────────────────────────────
        with ui.element("footer").classes("mkt-footer"):
            # Los enlaces de "Términos de uso" y "Política de privacidad"
            # apuntaban a "#" y el de "Contacto" a una sección inexistente:
            # se eliminan hasta que existan las páginas que los respalden.
            # Al reponerlos, envolverlos de nuevo en `.mkt-footer-links`
            # y usar `.mkt-footer-link` (ambas siguen en CLASS_CONTRACT.md).
            ui.label("© 2026 Gestor Docente. Todos los derechos reservados.").classes(
                "mkt-footer-copy"
            )


__all__ = ["landing_page"]
