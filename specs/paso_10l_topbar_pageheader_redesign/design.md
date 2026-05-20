# Diseño técnico — paso_10l_topbar_pageheader_redesign

## Arquitectura de referencia

```
src/interface/design/layout.py
  ← MODIFICAR: app_layout() + _topbar() + _sidebar()

src/interface/design/styles.css
  ← MODIFICAR: .andes-topbar, .topbar-* (nuevas y modificadas)
  ← AÑADIR: .topbar-page-info, .topbar-page-title, .topbar-page-sub,
             .topbar-brand, .topbar-logo-inst, .topbar-actions,
             .context-chip (override dark), .sidebar-logo-img

src/interface/design/theme.py
  ← AÑADIR: ThemeManager.render_logo()

src/interface/design/components/page_header.py
  ← MODIFICAR: solo deprecation notice en docstring

src/domain/models/[configuracion_institucion].py
  ← VERIFICAR/AÑADIR: campo logo_url

src/interface/pages/admin/[6 archivos].py
src/interface/pages/academico/[estudiantes, horarios].py
  ← MODIFICAR: mover page_header → parámetros de app_layout()
```

---

## §1 — Nueva firma de `app_layout()`

```python
# src/interface/design/layout.py

def app_layout(
    ctx: SessionContext | None,
    contenido: Callable,
    *,
    page_titulo: str = "",
    page_subtitulo: str = "",
    page_icono: str = "",
    page_acciones: list[dict] | None = None,
) -> None:
    """
    Layout principal de la aplicación Andes Minimal.

    Args:
        ctx:             Contexto de sesión del usuario actual.
        contenido:       Función callable que renderiza el contenido de la página.
        page_titulo:     Título de la página para el topbar integrado.
        page_subtitulo:  Subtítulo descriptivo opcional.
        page_icono:      Material Symbol para el topbar (ej: Icons.GROUPS).
        page_acciones:   Lista de dicts de acciones para botones en el topbar:
                         [{"label": str, "on_click": Callable, "icono": str|None,
                           "variante": "primary"|"secondary"|"danger"}]
    """
    logo_url = _get_logo_institucional()  # helper que lee from DB, ver §3

    with ui.row().classes("andes-app-layout"):
        _sidebar(ctx, logo_url=logo_url)
        with ui.column().classes("andes-main"):
            _topbar(
                ctx,
                page_titulo=page_titulo,
                page_subtitulo=page_subtitulo,
                page_icono=page_icono,
                page_acciones=page_acciones,
                logo_url=logo_url,
            )
            with ui.column().classes("andes-content"):
                contenido()
```

---

## §2 — Nueva `_topbar()` interna

```python
def _topbar(
    ctx: SessionContext | None,
    *,
    page_titulo: str = "",
    page_subtitulo: str = "",
    page_icono: str = "",
    page_acciones: list[dict] | None = None,
    logo_url: str | None = None,
) -> None:
    usuario_rol = ctx.usuario_rol if ctx else ""

    with ui.row().classes("andes-topbar items-center gap-0"):

        # ── Brand / toggle area ──────────────────────────────────────────────
        with ui.element("div").classes("topbar-brand"):
            btn_icon(
                Icons.MENU,
                on_click=_toggle_sidebar,
                tooltip="Menú",
                variante="ghost",
            )  # rediseñar color en CSS para fondo oscuro

        # ── Page info ────────────────────────────────────────────────────────
        if page_titulo:
            with ui.row().classes("topbar-page-info items-center gap-2 flex-1"):
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
            # Sin titulo: spacer para empujar items derechos
            ui.element("div").classes("flex-1")

        # ── Context chip (centro/derecha) ────────────────────────────────────
        if ctx is not None and usuario_rol != "admin":
            context_chip(
                ctx=ctx,
                on_change=_on_context_change,
                mostrar_asignatura=(usuario_rol == "profesor"),
            )

        # ── Acciones de página ───────────────────────────────────────────────
        if page_acciones:
            with ui.row().classes("topbar-actions gap-2"):
                for accion in page_acciones:
                    # Usar btn_ghost con clase override para fondo oscuro
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
```

### Helper `_btn_topbar_accion(accion: dict)`

```python
def _btn_topbar_accion(accion: dict) -> None:
    """Botón de acción en el topbar (fondo oscuro). Usa clase topbar-action-btn."""
    label    = accion.get("label", "")
    on_click = accion.get("on_click", lambda: None)
    icono    = accion.get("icono", None)
    variante = accion.get("variante", "primary")

    icon_html = ""
    if icono:
        icon_html = (
            f'<span class="material-symbols-rounded" '
            f'style="font-size:16px;vertical-align:middle;margin-right:4px;">'
            f'{icono}</span>'
        )

    clase_var = "topbar-action-danger" if variante == "danger" else (
        "topbar-action-secondary" if variante == "secondary" else "topbar-action-primary"
    )

    ui.button(
        on_click=on_click,
    ).classes(f"topbar-action-btn {clase_var}").props("flat").set_content(
        f'{icon_html}{label}'
    )
```

> **Nota para el implementer:** si `btn_primary/secondary/ghost` del design system
> tienen mecanismos de override de color, usarlos. Si no, crear `_btn_topbar_accion()`
> como helper privado en layout.py. El objetivo es tener botones visibles sobre
> el fondo oscuro del topbar.

### Helper `_user_block_topbar(ctx)`

```python
def _user_block_topbar(ctx: SessionContext | None) -> None:
    if not ctx:
        return
    with ui.row().classes("topbar-user-block items-center gap-2"):
        ThemeManager.icono(Icons.PROFILE, size=20, color="rgba(255,255,255,0.9)")
        with ui.column().classes("gap-0 topbar-user-info"):
            ui.label(ctx.usuario_nombre or "Usuario").classes("topbar-user-name")
            ui.label(ctx.usuario_rol or "").classes("topbar-user-role")
        btn_icon(
            Icons.LOGOUT,
            on_click=_logout,
            tooltip="Cerrar sesión",
            variante="ghost",
        )  # CSS override para fondo oscuro
```

---

## §3 — `_get_logo_institucional()` helper

```python
def _get_logo_institucional() -> str | None:
    """
    Obtiene la URL del logo institucional desde la BD.
    Devuelve None si no existe o si falla la consulta.
    """
    try:
        config = Container.infraestructura_service().get_configuracion_institucion()
        if config and hasattr(config, "logo_url") and config.logo_url:
            return config.logo_url
    except Exception:
        pass
    return None
```

---

## §4 — `_sidebar()` con logo condicional

```python
def _sidebar(ctx: SessionContext | None, *, logo_url: str | None = None) -> None:
    with ui.element("div").classes("andes-sidebar") as sidebar:
        with ui.element("div").classes("sidebar-header"):
            with ui.element("div").classes("sidebar-logo-wrap"):
                if logo_url:
                    ui.html(
                        f'<img src="{logo_url}" alt="Logo" class="sidebar-logo-img" />'
                    )
                else:
                    ui.label("LumEd").classes("sidebar-logo-text")
                    ui.label("Education Manager").classes("sidebar-sub-text")
        # ... resto del sidebar sin cambios
```

---

## §5 — CSS: `.andes-topbar` rediseñado

### Modificaciones a clases existentes

```css
/* ── TOPBAR REDESIGN ───────────────────────────────────────────────────────── */

.andes-topbar {
  height: var(--topbar-height);          /* aumentar a 72px en variables */
  min-height: var(--topbar-height);
  background: linear-gradient(135deg,
      rgba(25, 48, 122, 0.97)  0%,
      rgba(59, 92, 204, 0.93)  60%,
      rgba(78, 117, 255, 0.88) 100%);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 4px 24px rgba(59, 92, 204, 0.25);
  display: flex;
  align-items: center;
  padding: 0 var(--content-padding);
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 100;
}

/* Actualizar variable en :root */
/* --topbar-height: 72px;  (antes 58px) */
```

### Nuevas clases del topbar

```css
/* Brand (toggle button area) */
.topbar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-right: 12px;
  border-right: 1px solid rgba(255, 255, 255, 0.12);
  margin-right: 4px;
}

/* Page info (título + subtítulo) */
.topbar-page-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.topbar-page-title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
  letter-spacing: -0.01em;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topbar-page-sub {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.2;
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* User block */
.topbar-user-block {
  flex-shrink: 0;
}

.topbar-user-info {
  /* sin cambios en estructura, solo colores */
}

.topbar-user-name {
  font-size: var(--font-size-body);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.2;
  white-space: nowrap;
}

.topbar-user-role {
  font-size: var(--font-size-label);
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.2;
  white-space: nowrap;
  text-transform: capitalize;
}

/* Logo institucional en topbar */
.topbar-logo-inst {
  display: flex;
  align-items: center;
  padding: 0 8px;
  border-left: 1px solid rgba(255, 255, 255, 0.12);
  margin-left: 4px;
}

.topbar-logo-img {
  max-height: 36px;
  max-width: 120px;
  object-fit: contain;
  border-radius: var(--radius-sm);
  opacity: 0.9;
}

/* Botones en el topbar (fondo oscuro) */
.topbar-action-btn {
  height: 32px;
  padding: 0 12px;
  border-radius: var(--radius-md);
  font-size: var(--font-size-small);
  font-weight: 500;
  border: 1px solid rgba(255, 255, 255, 0.2);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: background 0.15s;
}
.topbar-action-primary {
  background: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.95);
}
.topbar-action-primary:hover {
  background: rgba(255, 255, 255, 0.25);
}
.topbar-action-secondary {
  background: transparent;
  color: rgba(255, 255, 255, 0.75);
}
.topbar-action-secondary:hover {
  background: rgba(255, 255, 255, 0.10);
}
.topbar-action-danger {
  background: rgba(220, 38, 38, 0.25);
  border-color: rgba(220, 38, 38, 0.4);
  color: rgba(255, 180, 180, 0.95);
}
.topbar-action-danger:hover {
  background: rgba(220, 38, 38, 0.4);
}

/* Botones icon-only del topbar (toggle, logout) */
.andes-topbar .q-btn[flat] {
  color: rgba(255, 255, 255, 0.75);
}
.andes-topbar .q-btn[flat]:hover {
  background: rgba(255, 255, 255, 0.10);
  color: rgba(255, 255, 255, 0.95);
}

/* Actions row */
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
```

### Context chip — override para fondo oscuro

```css
/* context_selector.py chip en topbar oscuro */
.andes-topbar .context-chip,
.andes-topbar [class*="context-chip"] {
  background: rgba(255, 255, 255, 0.12) !important;
  border: 1px solid rgba(255, 255, 255, 0.20) !important;
  color: rgba(255, 255, 255, 0.90) !important;
}
.andes-topbar .context-chip:hover,
.andes-topbar [class*="context-chip"]:hover {
  background: rgba(255, 255, 255, 0.20) !important;
}
```

> **Nota:** Las clases exactas del context_chip se deben verificar en
> `src/interface/design/components/context_selector.py`. Ajustar el selector
> CSS según las clases reales.

### Sidebar logo

```css
.sidebar-logo-img {
  max-width: 120px;
  max-height: 40px;
  object-fit: contain;
  border-radius: var(--radius-sm);
  opacity: 0.9;
}
```

---

## §6 — `ThemeManager.render_logo()` en `theme.py`

```python
@classmethod
def render_logo(
    cls,
    logo_url: str,
    max_height: int = 36,
    max_width: int = 120,
    clases: str = "",
) -> ui.html:
    """
    Renderiza la imagen del logo institucional.

    Args:
        logo_url:   URL o ruta estática de la imagen.
        max_height: Alto máximo en px.
        max_width:  Ancho máximo en px.
        clases:     Clases CSS adicionales para el <img>.
    """
    estilo = (
        f"max-height:{max_height}px;"
        f"max-width:{max_width}px;"
        f"object-fit:contain;"
        f"border-radius:var(--radius-sm);"
    )
    clase_final = f"logo-institucional {clases}".strip()
    return ui.html(
        f'<img src="{logo_url}" alt="Logo institución" '
        f'class="{clase_final}" style="{estilo}" />'
    )
```

---

## §7 — Modelo `ConfiguracionInstitucion`

El implementer debe leer `src/domain/models/` y encontrar el modelo de configuración
institucional. Si NO tiene `logo_url: str | None = None`, añadirlo:

```python
# Dentro del modelo (Pydantic v2)
logo_url: str | None = None
```

Si el modelo tiene validaciones de URL, no forzar — `logo_url` puede ser también
una ruta relativa a un directorio de assets estáticos.

Para el almacenamiento: si ya hay un servicio de actualización de la config
(`actualizar_configuracion_institucion()`), el campo `logo_url` se edita desde
`admin/configuracion_institucion.py` como un campo de texto (URL o ruta).
**Este paso NO incluye la UI de carga/edición del logo** — solo el campo en el modelo
y la lectura en el layout.

---

## §8 — Migración de páginas (8 archivos)

### Patrón de migración

```python
# ──── ANTES ────────────────────────────────────────────────────────────────
def grupos_page():
    ...
    def contenido():
        page_header(
            titulo    = "Gestión de Grupos",
            subtitulo = "Crea y administra los grupos académicos de la institución",
            icono     = Icons.GROUPS,
        )
        with ui.element("div").classes("panel-card"):
            ...
    app_layout(ctx, contenido)

# ──── DESPUÉS ──────────────────────────────────────────────────────────────
def grupos_page():
    ...
    def contenido():
        with ui.element("div").classes("panel-card"):
            ...
    app_layout(
        ctx,
        contenido,
        page_titulo    = "Gestión de Grupos",
        page_subtitulo = "Crea y administra los grupos académicos de la institución",
        page_icono     = Icons.GROUPS,
    )
```

**Para páginas con `page_acciones`:**

`academico/estudiantes.py` — los botones "Matricular" y "Carga CSV":
```python
app_layout(
    ctx,
    contenido,
    page_titulo    = "Gestión de Estudiantes",
    page_subtitulo = "Matrícula, estado y PIAR de estudiantes",
    page_icono     = Icons.STUDENTS,
    page_acciones  = [
        {"label": "Matricular",  "on_click": _abrir_dialog_matricula,
         "icono": "person_add",  "variante": "primary"},
        {"label": "Carga CSV",   "on_click": _abrir_dialog_csv,
         "icono": "upload_file", "variante": "secondary"},
    ],
)
```

`admin/usuarios.py` — el botón "Nuevo usuario" (condicional en es_admin):
```python
acciones = []
if es_admin:
    acciones = [{"label": "Nuevo usuario", "on_click": _abrir_crear_usuario,
                 "icono": "person_add", "variante": "primary"}]

app_layout(
    ctx,
    contenido,
    page_titulo    = "Gestión de Usuarios",
    page_subtitulo = "Cuentas de usuario y roles del sistema",
    page_icono     = Icons.TEACHERS,
    page_acciones  = acciones or None,
)
```

### Tabla completa de migración

| Página | `page_titulo` | `page_subtitulo` | `page_icono` | `page_acciones` |
|---|---|---|---|---|
| `admin/grupos.py` | "Gestión de Grupos" | "Crea y administra los grupos académicos de la institución" | `Icons.GROUPS` | `None` |
| `admin/asignaturas.py` | "Gestión de Asignaturas" | "Áreas de conocimiento y asignaturas del currículo" | `Icons.SUBJECTS` | `None` |
| `admin/asignaciones.py` | "Asignaciones Docentes" | "Asignación de docentes a grupos y asignaturas por periodo" | `"assignment_ind"` | `None` |
| `admin/usuarios.py` | "Gestión de Usuarios" | "Cuentas de usuario y roles del sistema" | `Icons.TEACHERS` | condicional |
| `admin/configuracion_sie.py` | "Configuración del SIE" | "Periodos académicos y configuración del año escolar" | `"settings"` | `None` |
| `admin/configuracion_institucion.py` | "Información Institucional" | "Datos básicos y generales de la institución educativa" | `"business"` | `None` |
| `academico/estudiantes.py` | "Gestión de Estudiantes" | "Matrícula, estado y PIAR de estudiantes" | `Icons.STUDENTS` | ver arriba |
| `academico/horarios.py` | "Horarios" | "Grilla semanal de bloques de clase por grupo" | `Icons.SCHEDULE` | `None` |

**Imports a eliminar de cada página migrada:**
```python
# ELIMINAR:
from src.interface.design.components import page_header
```

---

## §9 — Verificación de context_selector

Antes de declarar done, verificar en el browser que:
1. El context chip aparece en el topbar con estilo visible (texto/borde blancos)
2. Clic en el chip abre el selector (dialog) normalmente
3. El cambio de contexto actualiza las páginas sin error
4. El chip no se muestra para rol "admin" (comportamiento mantenido)

---

## §10 — Orden de implementación

```
T1  →  :root: actualizar --topbar-height a 72px
T2  →  styles.css: nuevo CSS del topbar (§5)
T3  →  domain: verificar/añadir logo_url en ConfiguracionInstitucion
T4  →  theme.py: añadir render_logo()
T5  →  layout.py: _get_logo_institucional() + nueva firma app_layout() +
                   nueva _topbar() + _sidebar() con logo
T6  →  8 páginas: migrar page_header → params de app_layout (§8)
T7  →  page_header.py: deprecation notice
T8  →  python init.py + pytest + verificación visual context_chip
```

---

## §11 — Notas de compatibilidad

### NiceGUI `btn_icon` en fondo oscuro
El `btn_icon()` del design system usa `variante="ghost"` internamente, que tiene
un color de texto oscuro por defecto. Para el topbar, el CSS override
`.andes-topbar .q-btn[flat]` debería funcionar. Si no, pasar `color="rgba(255,255,255,0.75)"`
como parámetro al `btn_icon()` si el componente lo acepta, o usar `ThemeManager.icono()`
directo en el topbar para el botón de toggle.

### `_toggle_sidebar`
La función `_toggle_sidebar` ya existe en el layout actual para colapsar el sidebar.
Solo asegurarse de que sigue siendo llamada desde el nuevo topbar.

### Variable `--topbar-height`
Al cambiar de 58px a 72px, verificar que `.andes-main` y `.andes-content` no tienen
`margin-top` o `padding-top` hardcodeados. El topbar es sticky, por lo que el contenido
fluye naturalmente debajo de él sin offsets adicionales.
