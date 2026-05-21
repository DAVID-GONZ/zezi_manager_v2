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
  - Botón logout: btn_icon(Icons.LOGOUT, ...)

Uso nuevo (preferido):
    @ui.page("/mi-ruta")
    def mi_pagina():
        ctx = SessionContext.desde_storage()
        def contenido():
            ui.label("Mi contenido")

        app_layout(
            ctx,
            contenido,
            page_titulo="Mi Página",
            page_subtitulo="Descripción de la página",
            page_icono="home",
        )

Uso legacy (compatible):
    app_layout(
        titulo_pagina="Mi Página",
        usuario_nombre=ctx.usuario_nombre,
        usuario_rol=ctx.usuario_rol,
        ruta_activa="/mi-ruta",
        contenido=contenido,
        ctx=ctx,
    )
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from nicegui import ui

from .theme import ThemeManager
from .tokens import Icons
from .components.buttons import btn_icon

if TYPE_CHECKING:
    from src.interface.context.session_context import SessionContext


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


def _get_logo_institucional() -> str | None:
    """
    Obtiene la URL del logo institucional desde la BD.
    Devuelve None si no existe o si falla la consulta.
    """
    try:
        from container import Container
        config = Container.configuracion_service().get_activa()
        if config and hasattr(config, "logo_url") and config.logo_url:
            return config.logo_url
    except Exception:
        pass
    return None


def _get_ruta_activa() -> str:
    """Intenta obtener la ruta activa desde el contexto de NiceGUI."""
    try:
        from nicegui import context as ng_context
        return ng_context.client.request.url.path
    except Exception:
        return ""


def _btn_topbar_accion(accion: dict) -> None:
    """Botón de acción en el topbar (fondo oscuro). Usa clase topbar-action-btn."""
    label    = accion.get("label", "")
    on_click = accion.get("on_click", lambda: None)
    icono    = accion.get("icono", None)
    variante = accion.get("variante", "primary")

    clase_var = "topbar-action-danger" if variante == "danger" else (
        "topbar-action-secondary" if variante == "secondary" else "topbar-action-primary"
    )

    if icono:
        icon_html = (
            f'<span class="material-symbols-rounded" '
            f'style="font-size:16px;vertical-align:middle;margin-right:4px;">'
            f'{icono}</span>'
        )
        content = f'{icon_html}{label}'
        btn = ui.button(on_click=on_click).classes(
            f"topbar-action-btn {clase_var}"
        ).props("flat")
        btn= content
    else:
        ui.button(label, on_click=on_click).classes(
            f"topbar-action-btn {clase_var}"
        ).props("flat")


def _user_block_topbar(ctx: "SessionContext | None") -> None:
    """Bloque de usuario en el topbar."""
    if not ctx:
        return
    with ui.row().classes("topbar-user-block items-center gap-2"):
        ThemeManager.icono(Icons.PROFILE, size=20, color="rgba(255,255,255,0.9)")
        with ui.column().classes("gap-0 topbar-user-info"):
            ui.label(ctx.usuario_nombre or "Usuario").classes("topbar-user-name")
            ui.label(ctx.usuario_rol or "").classes("topbar-user-role")
        btn_icon(
            Icons.LOGOUT,
            on_click=lambda: ui.navigate.to("/logout"),
            tooltip="Cerrar sesión",
        ).classes("topbar-logout-btn")


def _topbar(
    ctx: "SessionContext | None",
    *,
    page_titulo: str = "",
    page_subtitulo: str = "",
    page_icono: str = "",
    page_acciones: "list[dict] | None" = None,
    logo_url: str | None = None,
    toggle_callback=None,
) -> None:
    """Renderiza el topbar de la aplicación."""
    usuario_rol = ctx.usuario_rol if ctx else ""

    with ui.row().classes("andes-topbar items-center gap-0"):
        
        # ── Brand / toggle area ──────────────────────────────────────────────
        with ui.element("div").classes("topbar-brand"):
            if toggle_callback:
                toggle_btn_inner = ui.element("div").classes("topbar-toggle-btn") 
                with toggle_btn_inner:
                    ThemeManager.icono(Icons.MENU, size=20, color="rgba(255,255,255,0.85)")
                toggle_btn_inner.on("click", lambda _: toggle_callback())
            else:
                ThemeManager.icono(Icons.MENU, size=20, color="rgba(255,255,255,0.85)")

        # ── Page info ────────────────────────────────────────────────────────
        if page_titulo:
            with ui.row().classes("topbar-page-info items-center gap-2"):
                if page_icono:
                    ThemeManager.icono(
                        page_icono,
                        size=20,
                        color="rgba(255,255,255,0.85)",
                    )
                with ui.column().classes("gap-0"):
                    ui.label(page_titulo).classes("topbar-page-title")
                    if page_subtitulo:
                        ui.label(page_subtitulo).classes("topbar-page-sub")
        else:
            ui.element("div").classes("flex-1")

        # ── Context chip (centro/derecha) ────────────────────────────────────
        if ctx is not None and usuario_rol != "admin":
            from src.interface.design.components.context_selector import context_chip
            context_chip(
                ctx=ctx,
                on_change=None,
                mostrar_asignatura=(usuario_rol == "profesor"),
            )

        # ── Acciones de página ───────────────────────────────────────────────
        if page_acciones:
            with ui.row().classes("topbar-actions gap-2"):
                for accion in page_acciones:
                    _btn_topbar_accion(accion)

        # ── Logo institucional ───────────────────────────────────────────────
        if logo_url:
            with ui.element("div").classes("topbar-logo-inst"):
                ui.html(
                    f'<img src="{logo_url}" alt="Logo institución" '
                    f'class="topbar-logo-img" />'
                )

        # ── User block ───────────────────────────────────────────────────────
        _user_block_topbar(ctx)


def _topbar_legacy(
    titulo_pagina: str,
    usuario_nombre: str,
    usuario_rol: str,
    ctx=None,
    on_context_change=None,
    toggle_callback=None,
) -> None:
    """Topbar legacy para llamadas antiguas a app_layout."""

    with ui.element("header").classes("andes-topbar"):

        # Toggle sidebar
        if toggle_callback:
            toggle_btn_inner = ui.element("div").classes("topbar-brand")
            with toggle_btn_inner:
                ThemeManager.icono(Icons.MENU, size=20, color="rgba(255,255,255,0.85)")
            toggle_btn_inner.on("click", lambda _: toggle_callback())

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
                color="rgba(255,255,255,0.9)",
            )
            with ui.element("div").classes("topbar-user-info"):
                ui.label(usuario_nombre).classes("topbar-user-name")
                ui.label(usuario_rol.capitalize()).classes("topbar-user-role")

            btn_icon(
                Icons.LOGOUT,
                on_click=lambda: ui.navigate.to("/logout"),
                tooltip="Cerrar sesión",
            ).classes("topbar-logout-btn")

def _sidebar(
    usuario_rol: str,
    ruta_activa: str,
    *,
    logo_url: str | None = None,
) -> tuple:
    # Estado mutable del sidebar
    _s: dict = {"collapsed": True}

    sidebar_el = ui.element("nav").classes("andes-sidebar collapsed")

    with sidebar_el:
        # Cabecera: logo (sin el botón toggle)
        with ui.element("div").classes("sidebar-header"):
            with ui.element("div").classes("sidebar-logo-wrap"):
                if logo_url:
                    ui.html(
                        f'<img src="{logo_url}" alt="Logo" class="sidebar-logo-img" />'
                    )
                else:
                    ui.label("LumEd").classes("sidebar-logo-text")
                    ui.label("Education Manager").classes("sidebar-sub-text")
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
                        def _toggle_nav(
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

                        parent_el.on("click", _toggle_nav)

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

    return sidebar_el, _s


# ── Layout principal ────────────────────────────────────────────────────────────
def app_layout(
    ctx_or_none=None,
    contenido_arg: "Callable[[], None] | None" = None,
    *,
    page_titulo: str = "",
    page_subtitulo: str = "",
    page_icono: str = "",
    page_acciones: "list[dict] | None" = None,
    # ── Deprecated legacy kwargs (backward compat) ──────────────────────
    titulo_pagina: str = "",
    usuario_nombre: str = "",
    usuario_rol: str = "",
    ruta_activa: str = "",
    contenido: "Callable[[], None] | None" = None,
    ctx=None,
    on_context_change=None,
) -> None:
    """
    Layout principal de la aplicación Andes Minimal v2.

    Uso nuevo (preferido):
        app_layout(ctx, contenido_fn, page_titulo="...", page_icono="...", ...)

    Uso legacy (compatible con código existente):
        app_layout(titulo_pagina="...", usuario_nombre=..., usuario_rol=...,
                   ruta_activa=..., contenido=fn, ctx=ctx)

    Args (nuevo):
        ctx_or_none:     SessionContext del usuario autenticado.
        contenido_arg:   Callable que renderiza el cuerpo de la página.
        page_titulo:     Título mostrado en el topbar.
        page_subtitulo:  Subtítulo descriptivo opcional.
        page_icono:      Material Symbol para el topbar.
        page_acciones:   Lista de dicts de acciones para botones en el topbar.
    """
    from src.interface.context.session_context import SessionContext

    # ── Detectar modo de llamada ─────────────────────────────────────────────
    _new_mode = isinstance(ctx_or_none, SessionContext)

    if _new_mode:
        # Nueva llamada: app_layout(ctx, contenido, page_titulo=...)
        _ctx: "SessionContext | None" = ctx_or_none
        _contenido = contenido_arg
        _usuario_rol = _ctx.usuario_rol if _ctx else ""
        _usuario_nombre = _ctx.usuario_nombre if _ctx else ""
        _ruta_activa = _get_ruta_activa()
    else:
        # Llamada legacy: app_layout(titulo_pagina=..., usuario_nombre=..., ...)
        _ctx = ctx
        _contenido = contenido or contenido_arg
        _usuario_rol = usuario_rol
        _usuario_nombre = usuario_nombre
        _ruta_activa = ruta_activa

    logo_url = _get_logo_institucional()

    # ── Sidebar ──────────────────────────────────────────────────────────────
    sidebar_el, _s = _sidebar( 
        _usuario_rol,
        _ruta_activa,
        logo_url=logo_url,
    )

    # ── Área principal ───────────────────────────────────────────────────────
    main_el = ui.element("div").classes("andes-main")

    with main_el:
        def _toggle_sidebar() -> None:
            _s["collapsed"] = not _s["collapsed"]
                
            if _s["collapsed"]:
                sidebar_el.classes("collapsed")
            else:
                sidebar_el.classes(remove="collapsed") 
                           
        if _new_mode:
            _topbar(
                _ctx,
                page_titulo=page_titulo,
                page_subtitulo=page_subtitulo,
                toggle_callback=_toggle_sidebar,
            )
        else:
            _topbar_legacy(
                titulo_pagina=titulo_pagina,
                usuario_nombre=_usuario_nombre,
                usuario_rol=_usuario_rol,
                ctx=_ctx,
                toggle_callback=_toggle_sidebar,
            )

        # Contenido de la página
        with ui.element("main").classes("andes-content"):
            if _contenido:
                _contenido()


__all__ = ["app_layout", "NAV_ITEMS"]
