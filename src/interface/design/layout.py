"""
layout.py — Layout principal con rail icon-only 60px + flyout flotante (paso_12d).

Rail navigation:
  - Rail de 60px fijo (siempre visible, no colapsable).
  - Flyout flotante para grupos con sub-ítems (click para abrir).
  - Tooltip nativo CSS via data-tooltip al hover.
  - Cierre de flyout con click fuera o ESC (JS global inyectado una vez).

Regla CSS:
  Ningún componente inyecta style="" con valores estáticos.
  Todo el CSS vive en styles/. Solo se usan .classes("nombre-clase").

Ajustes NiceGUI 3.x:
  - Rail es position:fixed → main area requiere margin-left: var(--rail-width)
  - Iconos via ThemeManager.icono() en vez de ui.element().text()
  - Navegación: ui.navigate.to() en handlers de click
  - Botón logout: btn_icon(Icons.LOGOUT, ...)

Uso:
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
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from nicegui import ui

from .theme import ThemeManager
from .tokens import Icons
from .components.buttons import btn_icon

if TYPE_CHECKING:
    from src.interface.context.session_context import SessionContext


# ── Definición de la navegación principal — "Aula primero" (paso_12e) ──────────
NAV_ITEMS: list[dict] = [
    {
        "label": "Inicio",
        "icon":  "home",
        "ruta":  "/inicio",
        "rol":   ["*"],
    },
    {
        "label": "Aula",
        "icon":  "co_present",
        "rol":   ["admin", "director", "coordinador", "profesor"],
        "children": [
            {"label": "Planilla de Notas", "icon": "table_chart",
             "ruta": "/evaluacion/planilla",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Asistencia",        "icon": "fact_check",
             "ruta": "/asistencia",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Observaciones",     "icon": "comment",
             "ruta": "/convivencia/observaciones",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Comportamiento",    "icon": "rule",
             "ruta": "/convivencia/comportamiento",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Seguimiento",       "icon": "assignment",
             "ruta": "/convivencia/notas",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
        ],
    },
    {
        "label": "Académico",
        "icon":  "school",
        "rol":   ["admin", "director", "coordinador", "profesor"],
        "children": [
            {"label": "Estudiantes",   "icon": "person",
             "ruta": "/estudiantes",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Grupos",        "icon": "group",
             "ruta": "/admin/grupos",
             "rol":  ["admin", "director"]},
            {"label": "Asignaturas",   "icon": "book",
             "ruta": "/admin/asignaturas",
             "rol":  ["admin", "director"]},
            {"label": "Asignaciones",  "icon": "assignment_ind",
             "ruta": "/admin/asignaciones",
             "rol":  ["admin", "director"]},
            {"label": "Horarios",      "icon": "calendar_today",
             "ruta": "/horarios",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
        ],
    },
    {
        "label": "Evaluación",
        "icon":  "grading",
        "rol":   ["admin", "director", "coordinador", "profesor"],
        "children": [
            {"label": "Configuración SIE",      "icon": "tune",
             "ruta": "/evaluacion/configuracion",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Habilitaciones",         "icon": "assignment_return",
             "ruta": "/evaluacion/habilitaciones",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Planes de Mejoramiento", "icon": "trending_up",
             "ruta": "/evaluacion/planes",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Cierre de Periodo",      "icon": "lock",
             "ruta": "/evaluacion/cierre-periodo",
             "rol":  ["admin", "director", "coordinador"]},
            {"label": "Cierre de Año",          "icon": "lock_clock",
             "ruta": "/evaluacion/cierre-anio",
             "rol":  ["admin", "director", "coordinador"]},
        ],
    },
    {
        "label": "Informes",
        "icon":  "summarize",
        "rol":   ["admin", "director", "coordinador", "profesor"],
        "children": [
            {"label": "Tablero",                   "icon": "dashboard",
             "ruta": "/academico/tablero",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Boletín de Periodo",        "icon": "description",
             "ruta": "/informes/boletin-periodo",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Boletín Anual",             "icon": "description",
             "ruta": "/informes/boletin-anual",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
            {"label": "Consolidado de Notas",      "icon": "bar_chart",
             "ruta": "/informes/consolidado-notas",
             "rol":  ["admin", "director", "coordinador"]},
            {"label": "Consolidado de Asistencia", "icon": "event_note",
             "ruta": "/informes/consolidado-asistencia",
             "rol":  ["admin", "director", "coordinador"]},
            {"label": "Estadísticos",              "icon": "analytics",
             "ruta": "/informes/estadisticos",
             "rol":  ["admin", "director", "coordinador", "profesor"]},
        ],
    },
    {
        "divider": True,
        "rol":     ["admin", "director"],
    },
    {
        "label": "Administración",
        "icon":  "settings",
        "rol":   ["admin", "director"],
        "children": [
            {"label": "Usuarios",                  "icon": "badge",
             "ruta": "/admin/usuarios",
             "rol":  ["admin", "director"]},
            {"label": "Información Institucional", "icon": "business",
             "ruta": "/admin/configuracion-institucion",
             "rol":  ["admin", "director"]},
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
        with btn:
            ui.html(content)
    else:
        ui.button(label, on_click=on_click).classes(
            f"topbar-action-btn {clase_var}"
        ).props("flat")


def _theme_toggle_btn() -> None:
    """Botón cíclico de tema: auto → light → dark → auto."""
    btn = ui.element("button").classes("theme-toggle-btn").props(
        'data-mode="auto" title="Cambiar tema: auto / claro / oscuro" tabindex="0"'
    )
    with btn:
        ThemeManager.icono("brightness_auto", size=20, clases="theme-icon icon-auto")
        ThemeManager.icono("light_mode", size=20, clases="theme-icon icon-light")
        ThemeManager.icono("dark_mode", size=20, clases="theme-icon icon-dark")
    btn.on(
        "click",
        lambda _: ui.run_javascript(
            "var m=document.documentElement.getAttribute('data-theme')||'auto';"
            "var next=m==='auto'?'light':(m==='light'?'dark':'auto');"
            "window.__andesSetTheme(next);"
        ),
    )


def _user_block_topbar(ctx: "SessionContext | None") -> None:
    """Bloque de usuario en el topbar."""
    if not ctx:
        return
    with ui.row().classes("topbar-user-block items-center gap-2"):
        ThemeManager.icono(Icons.PROFILE, size=20)  # T1: color css-controlled (no inline)
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
    on_context_change=None,
) -> None:
    """Renderiza el topbar claro de la aplicación (surface bg, sin toggle — paso_13a)."""
    usuario_rol = ctx.usuario_rol if ctx else ""

    with ui.row().classes("andes-topbar items-center gap-0"):

        # ── Brand (decorativo — sin toggle desde paso_12d) ──────────────────
        ui.element("div").classes("topbar-brand")

        # ── Page info ────────────────────────────────────────────────────────
        if page_titulo:
            with ui.row().classes("topbar-page-info items-center gap-2"):
                if page_icono:
                    ThemeManager.icono(
                        page_icono,
                        size=20,
                    )  # T1: color css-controlled (no inline)
                with ui.column().classes("gap-0"):
                    ui.label(page_titulo).classes("topbar-page-title")
                    if page_subtitulo:
                        ui.label(page_subtitulo).classes("topbar-page-sub")
        else:
            ui.element("div").classes("flex-1")

        # ── Context chip (centro/derecha) ────────────────────────────────────
        if ctx is not None:
            from src.interface.design.components.context_selector import context_chip
            context_chip(
                ctx=ctx,
                on_change=on_context_change,
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

        # ── Theme toggle ─────────────────────────────────────────────────────
        if ctx is not None:
            _theme_toggle_btn()

        # ── User block ───────────────────────────────────────────────────────
        _user_block_topbar(ctx)


def _calcular_activo(item: dict, ruta_activa: str) -> bool:
    """Devuelve True si el item (o alguno de sus hijos) coincide con la ruta activa."""
    if "ruta" in item:
        return item["ruta"] == ruta_activa
    if "children" in item:
        return any(c.get("ruta") == ruta_activa for c in item["children"])
    return False


def _rail(
    usuario_rol: str,
    ruta_activa: str,
    *,
    logo_url: str | None = None,
) -> ui.element:
    """
    Renderiza el rail icon-only de 60px con flyouts contextuales.

    - Cada icono es un rail-item de 44×44px centrado en el rail.
    - Items sin hijos navegan directamente al hacer click.
    - Items con hijos abren un flyout flotante a la derecha.
    - El flyout se cierra con click fuera o ESC (JS global en app_layout).
    """

    # ── Estado del flyout (mutable en closures) ──────────────────────────
    _flyout_state: dict = {"open_item_id": None}
    # Holder de un elemento — permite mutar la referencia dentro de closures
    _fh: list = []  # _fh[0] = flyout_container (se asigna al final)

    def _cerrar_flyout() -> None:
        if _fh:
            _fh[0].classes(add="hidden")
        _flyout_state["open_item_id"] = None

    def _abrir_flyout(item: dict, event) -> None:
        container = _fh[0]
        container.clear()
        with container:
            ui.label(item["label"]).classes("flyout-header")
            for child in item["children"]:
                if not _usuario_puede_ver(child, usuario_rol):
                    continue
                is_active = ruta_activa == child.get("ruta")
                clase = "flyout-item" + (" is-active" if is_active else "")
                it = ui.element("div").classes(clase)
                with it:
                    ThemeManager.icono(child["icon"], size=18, clases="flyout-icon")
                    ui.label(child["label"]).classes("flyout-label")
                ruta_child = child["ruta"]
                it.on(
                    "click",
                    lambda e, r=ruta_child: (ui.navigate.to(r), _cerrar_flyout()),
                )
        # Posicionar el flyout cerca del icono clicado
        try:
            page_y = int(event.args.get("pageY", 80)) if isinstance(event.args, dict) else 80
        except Exception:
            page_y = 80
        container.style(f"top: {max(page_y - 20, 70)}px")
        container.classes(remove="hidden")
        _flyout_state["open_item_id"] = id(item)

    def _toggle_flyout(item: dict, event) -> None:
        if _flyout_state["open_item_id"] == id(item):
            _cerrar_flyout()
            return
        _abrir_flyout(item, event)

    # ── Render del rail ──────────────────────────────────────────────────
    rail_el = ui.element("nav").classes("andes-rail").props("role=navigation")

    with rail_el:
        # Logo / monograma institucional
        with ui.element("div").classes("rail-brand"):
            if logo_url:
                ui.html(f'<img src="{logo_url}" alt="Logo" class="rail-logo-img">')
            else:
                ui.html('<span class="rail-monogram">ZM</span>')

        # Ítems de navegación
        for item in NAV_ITEMS:
            if "divider" in item:
                if _usuario_puede_ver(item, usuario_rol):
                    ui.element("div").classes("rail-divider")
                continue

            if not _usuario_puede_ver(item, usuario_rol):
                continue

            tiene_hijos = "children" in item
            es_activo = _calcular_activo(item, ruta_activa)

            clase = "rail-item"
            if es_activo:
                clase += " is-active"
            if tiene_hijos:
                clase += " has-children"

            item_el = ui.element("div").classes(clase)
            with item_el:
                ThemeManager.icono(item["icon"], size=22, clases="rail-icon")
            item_el.props(f'data-tooltip="{item["label"]}" tabindex="0"')  # T5: keyboard a11y

            if tiene_hijos:
                item_el.on("click", lambda e, it=item: _toggle_flyout(it, e))
            else:
                item_el.on("click", lambda e, r=item["ruta"]: ui.navigate.to(r))

    # Flyout container — fuera del rail, usa position:fixed
    flyout_el = ui.element("div").classes("rail-flyout-container hidden")
    _fh.append(flyout_el)

    return rail_el


# ── Layout principal ────────────────────────────────────────────────────────────
def app_layout(
    ctx_or_none=None,
    contenido_arg: "Callable[[], None] | None" = None,
    *,
    page_titulo: str = "",
    page_subtitulo: str = "",
    page_icono: str = "",
    page_acciones: "list[dict] | None" = None,
    on_context_change=None,
) -> None:
    """
    Layout principal de la aplicación — Rail icon-only 60px (paso_12d).

    Uso:
        app_layout(ctx, contenido_fn, page_titulo="...", page_icono="...", ...)

    Args:
        ctx_or_none:       SessionContext del usuario autenticado.
        contenido_arg:     Callable que renderiza el cuerpo de la página.
        page_titulo:       Título mostrado en el topbar.
        page_subtitulo:    Subtítulo descriptivo opcional.
        page_icono:        Material Symbol para el topbar.
        page_acciones:     Lista de dicts de acciones para botones en el topbar.
        on_context_change: Callback al cambiar contexto desde el chip.
    """
    _ctx = ctx_or_none
    _contenido = contenido_arg
    _usuario_rol = _ctx.usuario_rol if _ctx else ""
    _ruta_activa = _get_ruta_activa()

    logo_url = _get_logo_institucional()

    # JS global: cerrar flyout con click-fuera o ESC (inyectado una vez por carga)
    ui.add_body_html("""
<script>
(function() {
  if (window.__andesTooltipListeners) return;
  window.__andesTooltipListeners = true;
  document.addEventListener('click', function(e) {
    var flyout = document.querySelector('.rail-flyout-container');
    var rail   = document.querySelector('.andes-rail');
    if (!flyout || !rail) return;
    if (flyout.contains(e.target) || rail.contains(e.target)) return;
    flyout.classList.add('hidden');
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      var flyout = document.querySelector('.rail-flyout-container');
      if (flyout) flyout.classList.add('hidden');
    }
  });
})();
</script>
""")

    ui.add_body_html("""
<script>
(function() {
  if (window.__andesThemeInit) return;
  window.__andesThemeInit = true;

  var saved = localStorage.getItem('andes-theme') || 'auto';
  if (saved !== 'auto') {
    document.documentElement.setAttribute('data-theme', saved);
  }

  window.__andesSetTheme = function(mode) {
    localStorage.setItem('andes-theme', mode);
    if (mode === 'auto') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', mode);
    }
    var btn = document.querySelector('.theme-toggle-btn');
    if (btn) btn.setAttribute('data-mode', mode);
  };

  var setButtonMode = function() {
    var btn = document.querySelector('.theme-toggle-btn');
    if (btn) {
      btn.setAttribute('data-mode', saved);
    } else {
      window.setTimeout(setButtonMode, 50);
    }
  };
  setButtonMode();
})();
</script>
""")

    # ── Rail ────────────────────────────────────────────────────────────────
    _rail(
        _usuario_rol,
        _ruta_activa,
        logo_url=logo_url,
    )

    # ── Área principal ───────────────────────────────────────────────────────
    main_el = ui.element("div").classes("andes-main")

    with main_el:
        _topbar(
            _ctx,
            page_titulo=page_titulo,
            page_subtitulo=page_subtitulo,
            page_icono=page_icono,
            page_acciones=page_acciones,
            logo_url=logo_url,
            on_context_change=on_context_change,
        )

        # Contenido de la página
        with ui.element("main").classes("andes-content"):
            if _contenido:
                _contenido()


__all__ = ["app_layout", "NAV_ITEMS"]
