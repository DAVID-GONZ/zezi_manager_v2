"""
layout.py — Layout principal con sidebar colapsable + topbar (Andes Minimal v2).

Sidebar colapsable:
  - Estado en _s = {"collapsed": False} (dict mutable, accesible en closures)
  - _toggle() alterna clase "collapsed" en sidebar y "sidebar-collapsed" en main
  - CSS en styles.css define la transición y el ancho en ambos estados
  - En estado collapsed: icono visible, label oculto (opacity:0; width:0)

Regla CSS:
  Ningún componente inyecta style="" con valores estáticos.
  Todo el CSS vive en styles.css. Solo se usan .classes("nombre-clase").

Ajustes NiceGUI 3.x:
  - Sidebar es position:fixed → main area requiere margin-left (clase .andes-main)
  - Iconos via ThemeManager.icono() en vez de ui.element().text()
  - Ítems de navegación: ui.element("a") con props href
  - Botón logout: with ui.button(...): ThemeManager.icono()

Uso en cada página autenticada:

    @ui.page("/mi-ruta")
    def mi_pagina():
        def contenido():
            ui.label("Mi contenido aquí")

        app_layout(
            titulo_pagina="Mi Página",
            usuario_nombre=ctx.nombre,
            usuario_rol=ctx.rol,
            ruta_activa="/mi-ruta",
            contenido=contenido,
        )
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from .theme import ThemeManager
from .tokens import Icons


# ── Definición de la navegación principal ──────────────────────────────────────
NAV_ITEMS: list[dict] = [
    {
        "label": "Dashboard",
        "icon":  Icons.DASHBOARD,
        "ruta":  "/inicio",
        "rol":   ["*"],
    },
    {
        "label": "Estudiantes",
        "icon":  Icons.STUDENTS,
        "ruta":  "/estudiantes",
        "rol":   ["admin", "director", "coordinador", "profesor"],
    },
    {
        "label": "Asistencia",
        "icon":  Icons.ATTENDANCE,
        "ruta":  "/asistencia",
        "rol":   ["profesor", "coordinador"],
    },
    {
        "label": "Calificaciones",
        "icon":  Icons.GRADES,
        "ruta":  "/evaluacion",
        "rol":   ["profesor", "coordinador"],
    },
    {
        "label": "Convivencia",
        "icon":  Icons.BEHAVIOR,
        "ruta":  "/convivencia",
        "rol":   ["coordinador", "director"],
    },
    {
        "label": "Informes",
        "icon":  Icons.REPORTS,
        "ruta":  "/informes",
        "rol":   ["director", "coordinador", "profesor"],
    },
    {
        "label": "Horarios",
        "icon":  Icons.SCHEDULE,
        "ruta":  "/horarios",
        "rol":   ["admin", "director"],
    },
    {
        "divider": True,
        "rol":     ["admin", "director"],
    },
    {
        "label": "Configuración",
        "icon":  Icons.CONFIG,
        "ruta":  "/admin/config",
        "rol":   ["admin", "director"],
    },
    {
        "label": "Usuarios",
        "icon":  Icons.TEACHERS,
        "ruta":  "/admin/usuarios",
        "rol":   ["admin"],
    },
    {
        "label": "Estadísticos",
        "icon":  "analytics",         
        "ruta":  "/academico/tablero",
        "rol":   ["profesor", "director", "coordinador"],
    },
]


def _usuario_puede_ver(item: dict, usuario_rol: str) -> bool:
    """Determina si el usuario con el rol dado puede ver un ítem de navegación."""
    roles = item.get("rol", [])
    return "*" in roles or usuario_rol in roles


# ── Layout principal ────────────────────────────────────────────────────────────
def app_layout(
    titulo_pagina: str,
    usuario_nombre: str,
    usuario_rol: str,
    ruta_activa: str,
    contenido: Callable[[], None],
    ctx=None,
    on_context_change=None,
) -> None:
    """
    Renderiza el layout completo de la aplicación (sidebar colapsable + topbar + contenido).

    Args:
        titulo_pagina:     Texto del topbar como título de la sección activa.
        usuario_nombre:    Nombre completo del usuario autenticado.
        usuario_rol:       Rol del usuario — controla visibilidad de ítems de nav.
        ruta_activa:       Ruta URL de la página actual — resalta el ítem del sidebar.
        contenido:         Callable sin argumentos que renderiza el cuerpo de la página.
        ctx:               SessionContext opcional — activa el context chip en el topbar.
        on_context_change: Callback llamado cuando el usuario cambia de contexto académico.
    """
    # Estado mutable del sidebar — dict para que las closures puedan mutar
    _s: dict = {"collapsed": False}

    # ── Sidebar (position:fixed en CSS) ───────────────────────────────────────
    sidebar_el = ui.element("nav").classes("andes-sidebar")
    with sidebar_el:

        # Cabecera: logo + botón toggle
        with ui.element("div").classes("sidebar-header"):
            with ui.element("div").classes("sidebar-logo-wrap"):
                ui.label("LumEd").classes("sidebar-logo-text")
                ui.label("Education Manager").classes("sidebar-sub-text")

            # Botón toggle — alterna collapsed
            toggle_btn = ui.element("div").classes("sidebar-toggle")
            with toggle_btn:
                ThemeManager.icono(Icons.MENU, size=18, color="var(--nav-sidebar-text)")

        # Ítems de navegación
        with ui.element("div").classes("sidebar-nav-scroll"):
            for item in NAV_ITEMS:

                # Divisor de sección
                if "divider" in item:
                    if _usuario_puede_ver(item, usuario_rol):
                        ui.element("div").classes("sidebar-nav-divider")
                    continue

                # Filtrar por rol
                if not _usuario_puede_ver(item, usuario_rol):
                    continue

                is_active = ruta_activa == item["ruta"]
                clase = "andes-sidebar-item" + (" active" if is_active else "")

                with ui.element("a").classes(clase).props(
                    f'href="{item["ruta"]}"'
                ):
                    ThemeManager.icono(item["icon"], size=20, clases="nav-icon")
                    ui.label(item["label"]).classes("nav-label")

        # Pie del sidebar — versión (oculto en collapsed)
        with ui.element("div").classes("sidebar-footer"):
            ui.label("v2.0").classes("sidebar-version")

    # ── Área principal (.andes-main maneja margin-left via CSS) ───────────────
    main_el = ui.element("div").classes("andes-main")
    with main_el:

        # Topbar (position:sticky en CSS)
        with ui.element("header").classes("andes-topbar"):

            ui.label(titulo_pagina).classes("topbar-title")

            # Context chip (roles académicos, no admin)
            if ctx is not None and usuario_rol != "admin":
                from src.interface.design.components.context_selector import context_chip
                context_chip(
                    ctx=ctx,
                    on_change=on_context_change,
                    mostrar_asignatura=(usuario_rol == "profesor"),
                )

            # Bloque de usuario + logout
            with ui.element("div").classes("topbar-user-block"):
                ThemeManager.icono(
                    Icons.PROFILE,
                    size=22,
                    color="var(--color-text-secondary)",
                )
                with ui.element("div").classes("topbar-user-info"):
                    ui.label(usuario_nombre).classes("topbar-user-name")
                    ui.label(usuario_rol.capitalize()).classes("topbar-user-role")

                with ui.button(
                    on_click=lambda: ui.navigate.to("/logout"),
                ).props("flat round dense").classes("topbar-logout-btn"):
                    ThemeManager.icono(Icons.LOGOUT, size=18)

        # Contenido de la página
        with ui.element("main").classes("andes-content"):
            contenido()

    # ── Toggle handler — definido DESPUÉS de tener refs a sidebar_el y main_el
    def _toggle() -> None:
        _s["collapsed"] = not _s["collapsed"]
        if _s["collapsed"]:
            sidebar_el.classes(add="collapsed")
            main_el.classes(add="sidebar-collapsed")
        else:
            sidebar_el.classes(remove="collapsed")
            main_el.classes(remove="sidebar-collapsed")

    toggle_btn.on("click", lambda _: _toggle())


__all__ = ["app_layout", "NAV_ITEMS"]
