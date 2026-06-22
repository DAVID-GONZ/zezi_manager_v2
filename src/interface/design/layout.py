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
from .components.buttons import btn_icon, btn_secondary

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
        "rol":   ["director", "coordinador", "profesor"],
        "children": [
            {"label": "Planilla de Notas", "icon": "table_chart",
             "ruta": "/evaluacion/planilla",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Asistencia",        "icon": "fact_check",
             "ruta": "/asistencia",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Observaciones",     "icon": "comment",
             "ruta": "/convivencia/observaciones",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Comportamiento",    "icon": "rule",
             "ruta": "/convivencia/comportamiento",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Seguimiento",       "icon": "assignment",
             "ruta": "/convivencia/notas",
             "rol":  ["director", "coordinador", "profesor"]},
        ],
    },
    {
        "label": "Académico",
        "icon":  "school",
        "rol":   ["director", "coordinador", "profesor"],
        "children": [
            {"label": "Estudiantes",   "icon": "person",
             "ruta": "/estudiantes",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Grupos",        "icon": "group",
             "ruta": "/admin/grupos",
             "rol":  ["director"]},
            {"label": "Asignaturas",   "icon": "book",
             "ruta": "/admin/asignaturas",
             "rol":  ["director"]},
            {"label": "Plan de estudios", "icon": "book",
             "ruta": "/admin/plan-estudios",
             "rol":  ["director", "coordinador"]},
            {"label": "Asignaciones",  "icon": "assignment_ind",
             "ruta": "/admin/asignaciones",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Horarios",      "icon": "calendar_today",
             "ruta": "/horarios",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Disponibilidad docente", "icon": "event_available",
             "ruta": "/admin/disponibilidad-docente",
             "rol":  ["director", "coordinador"]},
            {"label": "Salas",         "icon": "meeting_room",
             "ruta": "/admin/salas",
             "rol":  ["director"]},
        ],
    },
    {
        "label": "Evaluación",
        "icon":  "grading",
        "rol":   ["director", "coordinador", "profesor"],
        "children": [
            {"label": "Configuración SIE",      "icon": "tune",
             "ruta": "/evaluacion/configuracion",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Habilitaciones",         "icon": "assignment_return",
             "ruta": "/evaluacion/habilitaciones",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Planes de Mejoramiento", "icon": "trending_up",
             "ruta": "/evaluacion/planes",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Cierre de Periodo",      "icon": "lock",
             "ruta": "/evaluacion/cierre-periodo",
             "rol":  ["director", "coordinador"]},
            {"label": "Cierre de Año",          "icon": "lock_clock",
             "ruta": "/evaluacion/cierre-anio",
             "rol":  ["director", "coordinador"]},
        ],
    },
    {
        "label": "Informes",
        "icon":  "summarize",
        "rol":   ["director", "coordinador", "profesor"],
        "children": [
            {"label": "Tablero",                   "icon": "dashboard",
             "ruta": "/academico/tablero",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Boletín de Periodo",        "icon": "description",
             "ruta": "/informes/boletin-periodo",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Boletín Anual",             "icon": "description",
             "ruta": "/informes/boletin-anual",
             "rol":  ["director", "coordinador", "profesor"]},
            {"label": "Consolidado de Notas",      "icon": "bar_chart",
             "ruta": "/informes/consolidado-notas",
             "rol":  ["director", "coordinador"]},
            {"label": "Consolidado de Asistencia", "icon": "event_note",
             "ruta": "/informes/consolidado-asistencia",
             "rol":  ["director", "coordinador"]},
            {"label": "Estadísticos",              "icon": "analytics",
             "ruta": "/informes/estadisticos",
             "rol":  ["director", "coordinador", "profesor"]},
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
             "rol":  ["director"]},
            {"label": "Auditoría",                 "icon": "history",
             "ruta": "/admin/auditoria",
             "rol":  ["admin"]},
            {"label": "Diagnóstico",               "icon": "monitor_heart",
             "ruta": "/diagnostico",
             "rol":  ["admin"]},
        ],
    },
]


def _rol_permitido_en_ruta(ruta: str, usuario_rol: str) -> bool:
    """
    Decide visibilidad de UNA ruta consultando el registro central
    (`roles_de_ruta`) — la ÚNICA fuente de verdad de autorización (paso_35).

    - Sentinels PUBLICO / AUTENTICADO → visible para cualquier rol con sesión.
    - frozenset[Rol] → visible si el rol del usuario está dentro.
    - Ruta no registrada (None) → no visible (deny-by-default; evita drift).
    """
    from src.interface.auth import AUTENTICADO, PUBLICO, roles_de_ruta

    roles = roles_de_ruta(ruta)
    if roles is None:
        return False
    if roles is PUBLICO or roles is AUTENTICADO:
        return True
    return usuario_rol in {r.value for r in roles}


def _usuario_puede_ver(item: dict, usuario_rol: str) -> bool:
    """
    Determina si el usuario con el rol dado puede ver un ítem de navegación.

    Fuente única (paso_35): para ítems con `ruta` la visibilidad se deriva del
    registro central `roles_de_ruta`. Para grupos (con `children`) el grupo es
    visible si ALGÚN hijo lo es. Para ítems sin ruta ni hijos (p.ej. divider)
    se conserva la lista `"rol"` (no es una ruta autorizable).
    """
    if "ruta" in item:
        return _rol_permitido_en_ruta(item["ruta"], usuario_rol)
    if "children" in item:
        return any(_usuario_puede_ver(c, usuario_rol) for c in item["children"])
    # Sin ruta ni hijos: divisor u otro adorno. Usa su lista de rol declarativa.
    roles = item.get("rol", [])
    return "*" in roles or usuario_rol in roles


def _get_logo_institucional() -> str | None:
    """
    Obtiene la URL del logo institucional desde la BD.
    Devuelve None si no existe o si falla la consulta.
    """
    try:
        from container import Container
        from src.interface.context.session_context import SessionContext
        ctx = SessionContext.desde_storage()
        institucion_id = ctx.institucion_id if ctx else None
        config = Container.configuracion_service().get_activa(institucion_id)
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
    """Botón cíclico de tema: auto → light → dark → auto.
    El click handler se agrega vía addEventListener en el JS global (Vue.v-html
    sanitiza onclick, por eso no se usa inline handler).
    """
    btn = ui.element("button").classes("theme-toggle-btn")
    btn.props('tabindex="0" title="Cambiar tema: auto / claro / oscuro"')
    with btn:
        ui.html(
            '<span class="material-symbols-rounded theme-icon icon-auto">brightness_auto</span>'
            '<span class="material-symbols-rounded theme-icon icon-light">light_mode</span>'
            '<span class="material-symbols-rounded theme-icon icon-dark">dark_mode</span>'
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


def _salir_ver_como(ctx: "SessionContext") -> None:
    """Handler del botón Salir del banner de impersonación."""
    ctx.salir_ver_como()
    ui.navigate.to("/inicio")


def _impersonation_banner(ctx: "SessionContext | None") -> None:
    """
    Banner persistente mostrado mientras un admin impersona a otro usuario
    en modo solo lectura (paso_21). Incluye botón "Salir".
    """
    if not ctx or not getattr(ctx, "impersonando", False):
        return
    with ui.element("div").classes("impersonation-banner"):
        ThemeManager.icono(
            "visibility", size=18, clases="impersonation-banner-icon"
        )
        with ui.row().classes("impersonation-banner-text items-center gap-2"):
            ui.label("Estás viendo como")
            ui.label(ctx.usuario_nombre or "usuario").classes(
                "impersonation-banner-target"
            )
            ui.label("solo lectura").classes("impersonation-banner-tag")
        btn_secondary(
            "Salir",
            on_click=lambda: _salir_ver_como(ctx),
            icon="logout",
            size="sm",
        ).classes("impersonation-exit-btn")


def _topbar(
    ctx: "SessionContext | None",
    *,
    page_titulo: str = "",
    page_subtitulo: str = "",
    page_icono: str = "",
    page_acciones: "list[dict] | None" = None,
    logo_url: str | None = None,
    on_context_change=None,
    mostrar_contexto: bool = True,
    mostrar_grupo: bool = True,
    mostrar_asignatura: bool = True,
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
        if ctx is not None and mostrar_contexto:
            from src.interface.design.components.context_selector import context_chip
            # Dimensiones declaradas POR PÁGINA (no derivadas del rol).
            context_chip(
                ctx=ctx,
                on_change=on_context_change,
                mostrar_grupo=mostrar_grupo,
                mostrar_asignatura=mostrar_asignatura,
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
    Renderiza el rail icon-only de 60px con flyouts pre-renderizados.

    - Hover sobre un ítem con hijos → abre el flyout (transient).
    - Click → fija el flyout (persiste aunque el mouse se mueva).
    - JS puro para show/hide: sin roundtrip al servidor en hover.
    - Click fuera o ESC → cierra todos los flyouts.
    """
    flyout_groups: list[tuple[int, dict, str]] = []

    # ── Rail ────────────────────────────────────────────────────────────
    rail_el = ui.element("nav").classes("andes-rail").props("role=navigation")

    with rail_el:
        # Logo / monograma
        with ui.element("div").classes("rail-brand"):
            if logo_url:
                ui.html(f'<img src="{logo_url}" alt="Logo" class="rail-logo-img">')
            else:
                ui.html('<span class="rail-monogram">ZM</span>')

        for idx, item in enumerate(NAV_ITEMS):
            if "divider" in item:
                if _usuario_puede_ver(item, usuario_rol):
                    ui.element("div").classes("rail-divider")
                continue
            if not _usuario_puede_ver(item, usuario_rol):
                continue

            tiene_hijos = "children" in item
            es_activo   = _calcular_activo(item, ruta_activa)
            flyout_id   = f"flyout-g{idx}"

            clase = "rail-item"
            if es_activo:
                clase += " is-active"
            if tiene_hijos:
                clase += " has-children"

            item_el = ui.element("div").classes(clase)
            with item_el:
                ThemeManager.icono(item["icon"], size=22, clases="rail-icon")

            if tiene_hijos:
                # JS maneja hover y click — no Python handler para grupos
                item_el.props(
                    f'data-flyout="{flyout_id}" data-label="{item["label"]}" tabindex="0"'
                )
                flyout_groups.append((idx, item, flyout_id))
            else:
                # Hoja: Python navega, tooltip CSS en hover
                item_el.props(f'data-tooltip="{item["label"]}" tabindex="0"')
                item_el.on("click", lambda e, r=item["ruta"]: ui.navigate.to(r))

    # ── Flyouts pre-renderizados (position:fixed, fuera del rail) ────────
    for _idx, item, flyout_id in flyout_groups:
        flyout_el = ui.element("div").classes("rail-flyout-container hidden")
        flyout_el.props(f'id="{flyout_id}"')
        with flyout_el:
            ui.label(item["label"]).classes("flyout-header")
            for child in item["children"]:
                if not _usuario_puede_ver(child, usuario_rol):
                    continue
                is_active   = ruta_activa == child.get("ruta")
                clase_child = "flyout-item" + (" is-active" if is_active else "")
                it = ui.element("div").classes(clase_child)
                with it:
                    ThemeManager.icono(child["icon"], size=18, clases="flyout-icon")
                    ui.label(child["label"]).classes("flyout-label")
                ruta_child = child["ruta"]
                it.on("click", lambda e, r=ruta_child: ui.navigate.to(r))

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
    mostrar_contexto: bool = True,
    mostrar_grupo: bool = True,
    mostrar_asignatura: bool = True,
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
        mostrar_contexto:  Si False, oculta el chip de contexto (selector
                           año/periodo/grupo) en el topbar. Default True →
                           ninguna otra página cambia.
        mostrar_grupo:     Si False, el selector no muestra el paso Grupo
                           (página de agregados institucionales: solo periodo/año).
                           Default True. Asignatura implica grupo.
        mostrar_asignatura: Si False, el selector no muestra el paso Asignatura
                           (página que solo usa periodo+grupo). Default True.
                           Lo declara cada PÁGINA según su uso real de contexto.
    """
    _ctx = ctx_or_none
    _contenido = contenido_arg
    _usuario_rol = _ctx.usuario_rol if _ctx else ""
    _ruta_activa = _get_ruta_activa()

    logo_url = _get_logo_institucional()

    # JS global: flyout navigation (hover/pin) + theme init
    ui.add_body_html("""
<script>
(function() {
  /* ── Flyout navigation: hover transient, click pin ── */
  if (!window.__andesNavListeners) {
    window.__andesNavListeners = true;
    var pinned = null;
    var hoverTimer = null;

    function showFlyout(fid, railItem) {
      var flyout = document.getElementById(fid);
      if (!flyout) return;
      var rect = railItem.getBoundingClientRect();
      flyout.style.top = Math.max(rect.top - 8, 70) + 'px';
      document.querySelectorAll('.rail-flyout-container').forEach(function(f) {
        if (f.id !== fid) f.classList.add('hidden');
      });
      flyout.classList.remove('hidden');
      document.querySelectorAll('.rail-item[data-flyout]').forEach(function(ri) {
        ri.classList.toggle('is-open', ri.getAttribute('data-flyout') === fid);
      });
    }

    function hideFlyout(fid) {
      if (pinned === fid) return;
      var flyout = document.getElementById(fid);
      if (flyout) flyout.classList.add('hidden');
      document.querySelectorAll('.rail-item[data-flyout="' + fid + '"]').forEach(function(ri) {
        ri.classList.remove('is-open');
      });
    }

    function hideAll() {
      pinned = null;
      document.querySelectorAll('.rail-flyout-container').forEach(function(f) {
        f.classList.add('hidden');
      });
      document.querySelectorAll('.rail-item[data-flyout]').forEach(function(ri) {
        ri.classList.remove('is-open');
      });
    }

    function setupRailItems() {
      document.querySelectorAll('.rail-item[data-flyout]').forEach(function(item) {
        if (item._andesSetup) return;
        item._andesSetup = true;
        var fid = item.getAttribute('data-flyout');
        item.addEventListener('mouseenter', function() {
          clearTimeout(hoverTimer);
          showFlyout(fid, item);
        });
        item.addEventListener('mouseleave', function() {
          if (pinned === fid) return;
          hoverTimer = setTimeout(function() { hideFlyout(fid); }, 200);
        });
        item.addEventListener('click', function(e) {
          e.stopPropagation();
          if (pinned === fid) { pinned = null; hideFlyout(fid); }
          else { showFlyout(fid, item); pinned = fid; }
        });
      });
      document.querySelectorAll('.rail-flyout-container').forEach(function(flyout) {
        if (flyout._andesSetup) return;
        flyout._andesSetup = true;
        flyout.addEventListener('mouseenter', function() { clearTimeout(hoverTimer); });
        flyout.addEventListener('mouseleave', function() {
          if (pinned === flyout.id) return;
          hoverTimer = setTimeout(function() { hideFlyout(flyout.id); }, 200);
        });
      });
    }

    document.addEventListener('click', function(e) {
      var rail = document.querySelector('.andes-rail');
      var inFlyout = false;
      document.querySelectorAll('.rail-flyout-container').forEach(function(f) {
        if (f.contains(e.target)) inFlyout = true;
      });
      if (!rail || inFlyout || rail.contains(e.target)) return;
      hideAll();
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') hideAll();
    });

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', setupRailItems);
    } else {
      setupRailItems();
      setTimeout(setupRailItems, 150);
    }
  }

  /* ── Theme init ── */
  if (!window.__andesThemeInit) {
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
    /* Attach click handler and sync initial data-mode */
    var setupThemeBtn = function() {
      var btn = document.querySelector('.theme-toggle-btn');
      if (!btn) { setTimeout(setupThemeBtn, 50); return; }
      if (!btn._themeSetup) {
        btn._themeSetup = true;
        btn.addEventListener('click', function() {
          var m = this.getAttribute('data-mode') || 'auto';
          var n = m === 'auto' ? 'light' : (m === 'light' ? 'dark' : 'auto');
          window.__andesSetTheme(n);
        });
      }
      btn.setAttribute('data-mode', saved);
    };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', setupThemeBtn);
    } else {
      setupThemeBtn();
      setTimeout(setupThemeBtn, 150);
    }
  }
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
        _impersonation_banner(_ctx)
        _topbar(
            _ctx,
            page_titulo=page_titulo,
            page_subtitulo=page_subtitulo,
            page_icono=page_icono,
            page_acciones=page_acciones,
            logo_url=logo_url,
            on_context_change=on_context_change,
            mostrar_contexto=mostrar_contexto,
            mostrar_grupo=mostrar_grupo,
            mostrar_asignatura=mostrar_asignatura,
        )

        # Contenido de la página
        with ui.element("main").classes("andes-content"):
            if _contenido:
                _contenido()


__all__ = ["app_layout", "NAV_ITEMS"]
