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
  - Botón logout: btn_icon(Icons.LOGOUT, ...).classes("topbar-logout-btn")

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
from .components.buttons import btn_icon


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
        "rol":   ["profesor", "coordinador", "director"],
        "children": [
            {"label": "Planilla de Notas",   "icon": "table_chart",       "ruta": "/evaluacion/planilla",        "rol": ["profesor", "coordinador"]},
            {"label": "Config. Evaluación",  "icon": "tune",              "ruta": "/evaluacion/configuracion",   "rol": ["profesor", "coordinador"]},
            {"label": "Habilitaciones",      "icon": "assignment_return", "ruta": "/evaluacion/habilitaciones",  "rol": ["profesor", "coordinador"]},
            {"label": "Planes de Mejora",    "icon": "trending_up",       "ruta": "/evaluacion/planes",          "rol": ["profesor", "coordinador"]},
            {"label": "Cierre de Periodo",   "icon": "lock",              "ruta": "/evaluacion/cierre-periodo",  "rol": ["coordinador", "director"]},
            {"label": "Cierre de Año",       "icon": "lock_clock",        "ruta": "/evaluacion/cierre-anio",     "rol": ["director"]},
        ],
    },
    {
        "label":   "Convivencia",
        "icon":    Icons.BEHAVIOR,
        "rol":     ["coordinador", "director"],
        "pending": True,
        "children": [
            {"label": "Observaciones",  "icon": "comment",    "ruta": "/convivencia/observaciones",  "rol": ["coordinador", "director"], "pending": True},
            {"label": "Comportamiento", "icon": "rule",       "ruta": "/convivencia/comportamiento", "rol": ["coordinador", "director"], "pending": True},
            {"label": "Seguimiento",    "icon": "fact_check", "ruta": "/convivencia/seguimiento",    "rol": ["coordinador", "director"], "pending": True},
        ],
    },
    {
        "label":   "Informes",
        "icon":    Icons.REPORTS,
        "rol":     ["director", "coordinador", "profesor"],
        "pending": True,
        "children": [
            {"label": "Boletín Periodo",     "icon": "description", "ruta": "/informes/boletin-periodo",       "rol": ["director", "coordinador", "profesor"], "pending": True},
            {"label": "Boletín Anual",       "icon": "description", "ruta": "/informes/boletin-anual",         "rol": ["director", "coordinador", "profesor"], "pending": True},
            {"label": "Consol. Notas",       "icon": "bar_chart",   "ruta": "/informes/consolidado-notas",     "rol": ["director", "coordinador"],            "pending": True},
            {"label": "Consol. Asistencia",  "icon": "event_note",  "ruta": "/informes/consolidado-asistencia","rol": ["director", "coordinador"],            "pending": True},
            {"label": "Estadísticos",        "icon": "analytics",   "ruta": "/informes/estadisticos",          "rol": ["director", "coordinador", "profesor"], "pending": True},
        ],
    },
    {
        "label": "Horarios",
        "icon":  Icons.SCHEDULE,
        "ruta":  "/horarios",
        "rol":   ["admin", "director", "coordinador"],
    },
    {
        "label": "Estadísticos",
        "icon":  "analytics",
        "ruta":  "/academico/tablero",
        "rol":   ["profesor", "director", "coordinador"],
    },
    {
        "divider": True,
        "rol":     ["admin", "director"],
    },
    {
        "label": "Administración",
        "icon":  Icons.CONFIG,
        "rol":   ["admin", "director"],
        "children": [
            {"label": "Grupos",              "icon": Icons.GROUPS,     "ruta": "/admin/grupos",                    "rol": ["admin", "director"]},
            {"label": "Asignaturas",         "icon": "book",           "ruta": "/admin/asignaturas",               "rol": ["admin", "director"]},
            {"label": "Asignaciones",        "icon": "assignment_ind", "ruta": "/admin/asignaciones",              "rol": ["admin", "director"]},
            {"label": "Config. SIE",         "icon": "settings",       "ruta": "/admin/configuracion",             "rol": ["admin", "director"]},
            {"label": "Info. Institucional", "icon": "business",       "ruta": "/admin/configuracion-institucion", "rol": ["admin", "director"]},
            {"label": "Usuarios",            "icon": Icons.TEACHERS,   "ruta": "/admin/usuarios",                  "rol": ["admin"]},
        ],
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
            # Pre-calcular qué grupos están abiertos (el que contiene ruta_activa)
            _nav_open: dict = {
                item["label"]: any(
                    c.get("ruta") == ruta_activa for c in item.get("children", [])
                )
                for item in NAV_ITEMS
                if "children" in item
            }

            for item in NAV_ITEMS:
                # Divisor de sección
                if "divider" in item:
                    if _usuario_puede_ver(item, usuario_rol):
                        ui.element("div").classes("sidebar-nav-divider")
                    continue

                # Filtrar por rol
                if not _usuario_puede_ver(item, usuario_rol):
                    continue

                if "children" in item:
                    # ── Grupo colapsable ─────────────────────────────────────
                    visible_children = [
                        c for c in item["children"]
                        if _usuario_puede_ver(c, usuario_rol)
                    ]
                    if not visible_children:
                        continue

                    is_open    = _nav_open.get(item["label"], False)
                    is_pending = item.get("pending", False)
                    parent_clase = "sidebar-nav-parent" + (
                        " open"    if is_open    else ""
                    ) + (
                        " pending" if is_pending else ""
                    )

                    parent_el = ui.element("div").classes(parent_clase)
                    with parent_el:
                        ThemeManager.icono(item["icon"], size=20, clases="nav-icon")
                        ui.label(item["label"]).classes("nav-label")
                        ThemeManager.icono(
                            "expand_more", size=14, clases="nav-expand-icon"
                        )

                    children_el = ui.element("div").classes(
                        "sidebar-nav-children" + ("" if is_open else " hidden")
                    )
                    with children_el:
                        for child in visible_children:
                            is_active_child = ruta_activa == child.get("ruta", "")
                            is_child_pending = child.get("pending", False)
                            child_clase = "sidebar-nav-sub-item" + (
                                " active"  if is_active_child  else ""
                            ) + (
                                " pending" if is_child_pending  else ""
                            )
                            if is_child_pending:
                                with ui.element("div").classes(child_clase):
                                    ThemeManager.icono(
                                        child.get("icon", "circle"), size=16, clases="nav-icon"
                                    )
                                    ui.label(child["label"]).classes("nav-label")
                            else:
                                with ui.element("a").classes(child_clase).props(
                                    f'href="{child["ruta"]}"'
                                ):
                                    ThemeManager.icono(
                                        child.get("icon", "circle"), size=16, clases="nav-icon"
                                    )
                                    ui.label(child["label"]).classes("nav-label")

                    if not is_pending:
                        def _toggle(
                            label=item["label"],
                            p_el=parent_el,
                            c_el=children_el,
                        ):
                            _nav_open[label] = not _nav_open.get(label, False)
                            if _nav_open[label]:
                                p_el.classes(add="open")
                                c_el.classes(remove="hidden")
                            else:
                                p_el.classes(remove="open")
                                c_el.classes(add="hidden")

                        parent_el.on("click", _toggle)

                else:
                    # ── Ítem simple ──────────────────────────────────────────
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

                btn_icon(
                    Icons.LOGOUT,
                    on_click=lambda: ui.navigate.to("/logout"),
                    tooltip="Cerrar sesión",
                ).classes("topbar-logout-btn")

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
