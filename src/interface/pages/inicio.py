"""
src/interface/pages/inicio.py
==============================
Portal autenticado — hub de módulos por rol (portal_38).
Mini-dashboards con sub-secciones Recientes/Alertas/Hitos.
Usa app_layout (rail + topbar). La landing pública (/) vive en landing.py.
"""

from __future__ import annotations

import contextlib
import logging

from nicegui import ui

from src.domain.modulos import Modulo, modulos_con_pagina
from src.domain.portal_provider import SubItem
from src.interface.context.session_context import SessionContext
from src.interface.design.components.buttons import btn_secondary
from src.interface.design.components.greeting_hero import greeting_hero
from src.interface.design.layout import app_layout
from src.interface.design.theme import ThemeManager

logger = logging.getLogger("INICIO")


_COLOR_POR_MODULO: dict[str, tuple[str, str]] = {
    "asistencia": ("var(--module-asistencia-bg)", "var(--module-asistencia)"),
    "evaluacion": ("var(--module-evaluacion-bg)", "var(--module-evaluacion)"),
    "academico": ("var(--module-academico-bg)", "var(--module-academico)"),
    "convivencia": ("var(--module-convivencia-bg)", "var(--module-convivencia)"),
    "informes": ("var(--module-informes-bg)", "var(--module-informes)"),
}

_ORDEN_POR_ROL: dict[str, tuple[Modulo, ...]] = {
    "profesor": (
        Modulo.ASISTENCIA,
        Modulo.EVALUACION,
        Modulo.CONVIVENCIA,
        Modulo.INFORMES,
        Modulo.ACADEMICO,
    ),
    "director": (
        Modulo.INFORMES,
        Modulo.EVALUACION,
        Modulo.ACADEMICO,
        Modulo.ASISTENCIA,
        Modulo.CONVIVENCIA,
    ),
    "coordinador": (
        Modulo.CONVIVENCIA,
        Modulo.ACADEMICO,
        Modulo.ASISTENCIA,
        Modulo.EVALUACION,
        Modulo.INFORMES,
    ),
}

_ADMIN_CARDS: list[dict[str, str]] = [
    {
        "label": "Auditoría",
        "desc": "Eventos y cambios del sistema",
        "icono": "history",
        "ruta": "/admin/auditoria",
        "bg": "var(--color-primary-lighter)",
        "color": "var(--color-primary)",
    },
    {
        "label": "Usuarios",
        "desc": "Cuentas y roles del sistema",
        "icono": "group",
        "ruta": "/admin/usuarios",
        "bg": "var(--color-success-light)",
        "color": "var(--color-success)",
    },
    {
        "label": "Instituciones",
        "desc": "Catálogo de instituciones",
        "icono": "apartment",
        "ruta": "/admin/instituciones",
        "bg": "var(--color-info-light)",
        "color": "var(--color-info)",
    },
    {
        "label": "Diagnóstico",
        "desc": "Estado técnico del sistema",
        "icono": "monitoring",
        "ruta": "/diagnostico",
        "bg": "var(--color-warning-light)",
        "color": "var(--color-warning)",
    },
]


def _activable(el, on_activate) -> None:
    """Hace alcanzable por teclado un `div` que actúa como control clicable.

    Un `ui.element("div").on("click", ...)` no recibe foco ni responde a teclado,
    así que el `*:focus-visible` global de `reset.css` nunca dispara y el ítem es
    inalcanzable sin ratón. Se le da el contrato mínimo de un control:

      - `role="button"` — anuncia que activarlo ejecuta una acción.
      - `tabindex="0"`  — entra en el orden natural de tabulación.
      - Enter y Espacio — activación por teclado, como un botón nativo
        (`.prevent` en Espacio evita el scroll de página por defecto).

    `on_activate` es el mismo callable que se usaría en el `on("click", ...)`.
    """
    el.props('role="button" tabindex="0"')
    el.on("click", on_activate)
    el.on("keydown.enter", on_activate)
    el.on("keydown.space.prevent", on_activate)


def _modulos_filtrados(rol: str) -> list:
    from src.interface.design.layout import _modulo_visible, _rol_permitido_en_ruta

    disponibles = {d.id: d for d in modulos_con_pagina()}
    orden = _ORDEN_POR_ROL.get(rol, ())
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


def _render_module_card(d, ctx, provider) -> None:
    """Tarjeta de módulo con cabecera y sub-secciones condicionales (portal_38)."""
    bg, ic = _COLOR_POR_MODULO.get(
        d.id.value,
        ("var(--color-surface-alt)", "var(--color-text-secondary)"),
    )

    # Sub-secciones — fail-open
    recientes: list[SubItem] = []
    alertas: list[SubItem] = []
    hitos: list[SubItem] = []
    if provider is not None:
        with contextlib.suppress(Exception):
            recientes = provider.recientes(ctx)
        with contextlib.suppress(Exception):
            alertas = provider.alertas(ctx)
        with contextlib.suppress(Exception):
            hitos = provider.hitos(ctx)

    with (
        ui.element("div")
        .classes("portal-module-card")
        .style(  # DYNAMIC
            f"--card-accent:{ic}; --card-accent-bg:{bg}"
        )
    ):
        # ── Cabecera ──────────────────────────────────────────────────
        with ui.element("div").classes("portal-card-header"):
            with ui.element("div").classes("portal-card-icon"):
                ThemeManager.icono(d.icono, size=22, color=ic)
            ui.label(d.label).classes("portal-card-title")
            btn_secondary(
                "Ver módulo",
                on_click=lambda r=d.ruta_principal: ui.navigate.to(r),
                size="sm",
            )

        # ── Sub-secciones ─────────────────────────────────────────────
        if recientes:
            with ui.element("div").classes("portal-subcard portal-subcard--recientes"):
                ui.label("Recientes").classes("portal-card-section-title")
                for item in recientes:
                    it = ui.element("div").classes("portal-subcard-item")
                    _activable(it, lambda r=item.ruta_destino: ui.navigate.to(r))
                    with it:
                        ui.label(item.label).classes("portal-subcard-label")
                        ui.label(item.detalle).classes("portal-subcard-detalle")

        if alertas:
            with ui.element("div").classes("portal-subcard portal-subcard--alertas"):
                ui.label("Alertas").classes("portal-card-section-title")
                for item in alertas:
                    it = ui.element("div").classes(
                        "portal-subcard-item portal-subcard-item--warning"
                    )
                    _activable(it, lambda r=item.ruta_destino: ui.navigate.to(r))
                    with it:
                        ThemeManager.icono("warning", size=14, color="var(--color-warning)")
                        ui.label(item.label).classes("portal-subcard-label")

        if hitos:
            with ui.element("div").classes("portal-subcard portal-subcard--hitos"):
                ui.label("Hitos").classes("portal-card-section-title")
                for item in hitos:
                    it = ui.element("div").classes("portal-subcard-item")
                    _activable(it, lambda r=item.ruta_destino: ui.navigate.to(r))
                    with it:
                        ui.label(item.label).classes("portal-subcard-label")
                        ui.label(item.detalle).classes("portal-subcard-detalle")


def _render_module_card_admin(c: dict) -> None:
    """Tarjeta de administración (sin sub-secciones)."""
    with (
        ui.element("div")
        .classes("portal-module-card")
        .style(  # DYNAMIC
            f"--card-accent:{c['color']}; --card-accent-bg:{c['bg']}"
        )
    ):
        with ui.element("div").classes("portal-card-header"):
            with ui.element("div").classes("portal-card-icon"):
                ThemeManager.icono(c["icono"], size=22, color=c["color"])
            ui.label(c["label"]).classes("portal-card-title")
            btn_secondary(
                "Ver módulo",
                on_click=lambda r=c["ruta"]: ui.navigate.to(r),
                size="sm",
            )


# page-delegate: ruta registrada en main.py vía registrar_pagina (AUTENTICADO)
def inicio_page() -> None:
    from container import Container
    from src.services.portal_resumen_service import ResumenGlobalDTO

    ctx = SessionContext.desde_storage()
    rol = ctx.usuario_rol if ctx else None
    nombre = ctx.usuario_nombre if ctx else ""
    logger.info("Hub: %s (%s)", nombre or "anónimo", rol or "?")

    # Resumen global — fail-open
    resumen: ResumenGlobalDTO
    try:
        svc = Container.portal_resumen_service()
        resumen = (
            svc.resumen_global(ctx) if ctx else ResumenGlobalDTO(lineas=[], total_notificaciones=0)
        )
    except Exception:
        resumen = ResumenGlobalDTO(lineas=[], total_notificaciones=0)

    def contenido() -> None:
        nombre_corto = nombre.split()[0] if nombre else "Usuario"
        greeting_hero(
            nombre=nombre_corto,
            rol=rol or "",
            mensaje="Bienvenido al portal de gestión docente.",
            nombre_completo=nombre or None,
        )

        # Resumen global navegable
        if resumen.lineas:
            with ui.element("div").classes("portal-resumen"):
                for linea in resumen.lineas:
                    fila = ui.element("div").classes(
                        f"portal-resumen-linea portal-resumen-linea--{linea.severidad}"
                    )
                    _activable(fila, lambda r=linea.ruta_destino: ui.navigate.to(r))
                    with fila:
                        ThemeManager.icono("info", size=16, color="var(--color-warning)")
                        ui.label(linea.texto).classes("portal-resumen-texto")

        # Tarjetas de módulo
        with ui.element("div").classes("module-hub-grid"):
            if rol == "admin":
                for c in _ADMIN_CARDS:
                    _render_module_card_admin(c)
            elif rol:
                for d in _modulos_filtrados(rol):
                    provider = Container.portal_provider(d.id.value)
                    _render_module_card(d, ctx, provider)

    app_layout(ctx, contenido, notif_count=resumen.total_notificaciones)


__all__ = ["inicio_page"]
