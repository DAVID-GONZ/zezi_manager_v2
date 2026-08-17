"""
src/interface/pages/inicio.py
==============================
Hub publico de modulos — landing page del sistema.
Ruta PUBLICA: muestra las tarjetas de modulo a todos.
Click en tarjeta: si hay sesion activa y autorizacion, navega;
si no, redirige a /login.
"""
from __future__ import annotations

import logging

from nicegui import app, ui

from src.interface.design.theme import ThemeManager
from src.domain.modulos import Modulo, modulos_con_pagina

logger = logging.getLogger("INICIO")


_COLOR_POR_MODULO: dict[str, tuple[str, str]] = {
    "asistencia":  ("var(--color-success-light)", "var(--color-success)"),
    "evaluacion":  ("var(--color-primary-lighter)", "var(--color-primary)"),
    "academico":   ("var(--color-info-light)", "var(--color-info)"),
    "convivencia": ("var(--color-warning-light)", "var(--color-warning)"),
    "informes":    ("var(--color-primary-lighter)", "var(--color-primary)"),
}

_ORDEN_POR_ROL: dict[str, tuple[Modulo, ...]] = {
    "profesor":    (Modulo.ASISTENCIA, Modulo.EVALUACION, Modulo.CONVIVENCIA, Modulo.INFORMES, Modulo.ACADEMICO),
    "director":    (Modulo.INFORMES, Modulo.EVALUACION, Modulo.ACADEMICO, Modulo.ASISTENCIA, Modulo.CONVIVENCIA),
    "coordinador": (Modulo.CONVIVENCIA, Modulo.ACADEMICO, Modulo.ASISTENCIA, Modulo.EVALUACION, Modulo.INFORMES),
}

_ORDEN_PUBLICO: tuple[Modulo, ...] = (
    Modulo.ASISTENCIA, Modulo.EVALUACION, Modulo.CONVIVENCIA,
    Modulo.ACADEMICO, Modulo.INFORMES,
)

_ADMIN_CARDS: list[dict[str, str]] = [
    {"label": "Auditoría",     "desc": "Eventos y cambios del sistema", "icono": "history",    "ruta": "/admin/auditoria",    "bg": "var(--color-primary-lighter)", "color": "var(--color-primary)"},
    {"label": "Usuarios",      "desc": "Cuentas y roles del sistema",   "icono": "group",      "ruta": "/admin/usuarios",     "bg": "var(--color-success-light)",   "color": "var(--color-success)"},
    {"label": "Instituciones", "desc": "Catálogo de instituciones",     "icono": "apartment",  "ruta": "/admin/instituciones", "bg": "var(--color-info-light)",      "color": "var(--color-info)"},
    {"label": "Diagnóstico",   "desc": "Estado técnico del sistema",    "icono": "monitoring", "ruta": "/diagnostico",         "bg": "var(--color-warning-light)",   "color": "var(--color-warning)"},
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _on_card_click(ruta: str) -> None:
    """Navega al modulo si hay sesion; si no, al login."""
    if app.storage.user.get("autenticado"):
        ui.navigate.to(ruta)
    else:
        ui.navigate.to("/login")


def _modulos_filtrados(rol: str) -> list:
    """Modulos visibles para un rol autenticado, en orden de prioridad."""
    from src.interface.design.layout import _modulo_visible, _rol_permitido_en_ruta

    disponibles = {d.id: d for d in modulos_con_pagina()}
    orden = _ORDEN_POR_ROL.get(rol, _ORDEN_PUBLICO)

    result = []
    for m in orden:
        d = disponibles.get(m)
        if d is None:
            continue
        if not _rol_permitido_en_ruta(d.ruta_principal, rol):
            continue
        if not _modulo_visible({"ruta": d.ruta_principal}):
            continue
        result.append(d)

    ids_ya = {d.id for d in result}
    for d in modulos_con_pagina():
        if d.id in ids_ya:
            continue
        if not _rol_permitido_en_ruta(d.ruta_principal, rol):
            continue
        if not _modulo_visible({"ruta": d.ruta_principal}):
            continue
        result.append(d)

    return result


def _render_card(label: str, desc: str, icono: str, ruta: str,
                 bg: str, icon_color: str) -> None:
    with ui.element("div").classes("module-card").on(
        "click", lambda r=ruta: _on_card_click(r)
    ):
        with ui.element("div").classes("module-card-icon").style(  # DYNAMIC
            f"background:{bg}"
        ):
            ThemeManager.icono(icono, size=24, color=icon_color)
        with ui.element("div").classes("action-text-col"):
            ui.label(label).classes("action-label")
            ui.label(desc).classes("action-desc")


# ── Pagina principal ─────────────────────────────────────────────────────────

def inicio_page() -> None:
    autenticado = bool(app.storage.user.get("autenticado"))
    rol = app.storage.user.get("usuario_rol") if autenticado else None
    nombre = app.storage.user.get("usuario_nombre", "") if autenticado else ""

    logger.info("Hub: %s (%s)", nombre or "anónimo", rol or "público")

    with ui.element("div").classes("hub-landing"):
        # ── Branding con animacion ──
        with ui.element("div").classes("hub-branding greeting-hero-animated"):
            with ui.element("div").classes("andes-login-icon-wrap greeting-name"):
                ThemeManager.icono("school", size=40, color="var(--color-primary)")
            ui.label("Gestor Docente").classes("hub-title greeting-desc")
            ui.label("Sistema de Gestión Educativa").classes("hub-subtitle greeting-meta")

        # ── Indicador de sesion ──
        if autenticado and nombre:
            nombre_corto = nombre.split()[0]
            with ui.element("div").classes("hub-session"):
                ThemeManager.icono("person", size=16, color="var(--color-text-secondary)")
                ui.label(nombre_corto).classes("hub-session-name")
                ui.link("Cerrar sesión", "/logout").classes("hub-session-logout")

        # ── Tarjetas de modulo ──
        with ui.element("div").classes("module-hub-grid"):
            if rol == "admin":
                for c in _ADMIN_CARDS:
                    _render_card(c["label"], c["desc"], c["icono"],
                                 c["ruta"], c["bg"], c["color"])
            elif autenticado and rol:
                for d in _modulos_filtrados(rol):
                    bg, ic = _COLOR_POR_MODULO.get(
                        d.id.value,
                        ("var(--color-surface-alt)", "var(--color-text-secondary)"),
                    )
                    _render_card(d.label, d.descripcion, d.icono,
                                 d.ruta_principal, bg, ic)
            else:
                disponibles = {d.id: d for d in modulos_con_pagina()}
                for m in _ORDEN_PUBLICO:
                    d = disponibles.get(m)
                    if d is None:
                        continue
                    bg, ic = _COLOR_POR_MODULO.get(
                        d.id.value,
                        ("var(--color-surface-alt)", "var(--color-text-secondary)"),
                    )
                    _render_card(d.label, d.descripcion, d.icono,
                                 d.ruta_principal, bg, ic)

        # ── Pie: enlace a login si no hay sesion ──
        if not autenticado:
            with ui.element("div").classes("hub-footer"):
                ui.link("Iniciar sesión", "/login").classes("hub-login-link")


__all__ = ["inicio_page"]
