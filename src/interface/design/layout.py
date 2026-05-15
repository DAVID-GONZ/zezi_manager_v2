"""
layout.py — Layout principal con sidebar + topbar del design system Andes Minimal.

Ajustes NiceGUI 3.x:
  - Iconos via ThemeManager.icono() (ui.html) en vez de ui.element().text()
    que no existe como método chainable en NiceGUI 3.x.
  - Ítems de navegación: ui.element("a") con props href; icono como ThemeManager.icono().
  - Botón de logout: with ui.button(...): ThemeManager.icono() — no ui.button(icon=nombre)
    porque el parámetro icon= espera nombres Quasar, no Material Symbols Rounded.
  - Icono de perfil: ThemeManager.icono() directo, sin envoltura de botón.

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
    Renderiza el layout completo de la aplicación (sidebar + topbar + contenido).

    Args:
        titulo_pagina:  Texto que aparece en el topbar como título de la sección activa.
        usuario_nombre: Nombre completo del usuario autenticado.
        usuario_rol:    Rol del usuario autenticado (ej: "admin", "profesor", "director").
                        Controla qué ítems de navegación son visibles.
        ruta_activa:    Ruta URL de la página actual (ej: "/inicio", "/asistencia").
                        Resalta el ítem correspondiente en el sidebar.
        contenido:      Callable sin argumentos que renderiza el cuerpo de la página.

    Ejemplo:
        @ui.page("/inicio")
        def inicio():
            def _render():
                ui.label("Bienvenido al dashboard")

            app_layout(
                titulo_pagina="Dashboard",
                usuario_nombre="Ana García",
                usuario_rol="coordinador",
                ruta_activa="/inicio",
                contenido=_render,
            )
    """
    with ui.element("div").style(
        "display:flex;"
        "min-height:100vh;"
        "background:var(--color-bg);"
    ):
        # ── Sidebar ──────────────────────────────────────────────────────────
        with ui.element("nav").classes("andes-sidebar"):

            # Logo / nombre de la app
            with ui.element("div").style(
                "padding:20px 16px 16px;"
                "border-bottom:1px solid rgba(255,255,255,0.1);"
            ):
                ui.label("Gestor Docente").style(
                    "color:#FFFFFF;"
                    "font-weight:600;"
                    "font-size:var(--font-size-body);"
                    "display:block;"
                )
                ui.label("Sistema Educativo").style(
                    "color:var(--color-sidebar-text);"
                    "font-size:var(--font-size-small);"
                    "margin-top:2px;"
                    "display:block;"
                )

            # Ítems de navegación
            with ui.element("div").style("padding:8px 0;flex:1;overflow-y:auto;"):
                for item in NAV_ITEMS:

                    # Divisor de sección
                    if "divider" in item:
                        if _usuario_puede_ver(item, usuario_rol):
                            ui.separator().style(
                                "margin:8px 16px;"
                                "background:rgba(255,255,255,0.1);"
                                "border:none;"
                                "height:1px;"
                            )
                        continue

                    # Filtrar por rol
                    if not _usuario_puede_ver(item, usuario_rol):
                        continue

                    is_active = ruta_activa == item["ruta"]
                    clase = "andes-sidebar-item" + (" active" if is_active else "")

                    # Ítem de navegación como enlace <a>
                    with ui.element("a").classes(clase).props(
                        f'href="{item["ruta"]}"'
                    ):
                        # Icono — ThemeManager.icono() en vez de .text()
                        ThemeManager.icono(
                            item["icon"],
                            size=20,
                            clases="nav-icon",
                        )
                        ui.label(item["label"]).style(
                            "font-size:var(--font-size-small);"
                            "white-space:nowrap;"
                            "overflow:hidden;"
                            "text-overflow:ellipsis;"
                        )

        # ── Área principal ────────────────────────────────────────────────────
        with ui.element("div").style(
            "flex:1;"
            "display:flex;"
            "flex-direction:column;"
            "min-width:0;"            # evita overflow en flex
        ):
            # Topbar
            with ui.element("header").classes("andes-topbar"):

                # Título de la página activa
                ui.label(titulo_pagina).style(
                    "color:var(--color-text-primary);"
                    "font-weight:600;"
                    "font-size:var(--font-size-body);"
                    "flex:1;"
                )

                # Context chip (roles académicos, no admin)
                if ctx is not None and usuario_rol != "admin":
                    from src.interface.design.components.context_selector import context_chip
                    mostrar_asignatura = usuario_rol == "profesor"
                    context_chip(
                        ctx=ctx,
                        on_change=on_context_change,
                        mostrar_asignatura=mostrar_asignatura,
                    )

                # Bloque de usuario + logout
                with ui.row().classes("items-center gap-2").style("flex-shrink:0;"):

                    # Icono de perfil
                    ThemeManager.icono(
                        Icons.PROFILE,
                        size=24,
                        color="var(--color-text-secondary)",
                    )

                    # Nombre y rol del usuario
                    with ui.column().classes("gap-0").style("line-height:1.2;"):
                        ui.label(usuario_nombre).style(
                            "font-size:var(--font-size-small);"
                            "font-weight:500;"
                            "color:var(--color-text-primary);"
                        )
                        ui.label(usuario_rol.capitalize()).style(
                            "font-size:11px;"
                            "color:var(--color-text-secondary);"
                        )

                    # Botón de logout con icono Material Symbol
                    with ui.button(
                        on_click=lambda: ui.navigate.to("/logout"),
                    ).props("flat round dense").style(
                        "color:var(--color-text-secondary);"
                        "min-width:36px;"
                        "min-height:36px;"
                    ):
                        ThemeManager.icono(Icons.LOGOUT, size=20)

            # Contenido de la página
            with ui.element("main").classes("andes-content"):
                contenido()


__all__ = ["app_layout", "NAV_ITEMS"]
