# Design — paso_10i: Saneamiento del Design System

---

## Archivos a crear / modificar

| Archivo | Operación | Responsabilidad |
|---------|-----------|-----------------|
| `src/interface/design/styles.css` | MODIFICAR | Añadir clases CSS faltantes para components y nuevas variantes de botón |
| `src/interface/design/components/buttons.py` | REEMPLAZAR | Ampliar con `btn_ghost` y `btn_icon`; aplicar convenciones de tipo |
| `src/interface/design/components/__init__.py` | MODIFICAR | Exportar los cinco `btn_*` |
| `src/interface/design/components/stat_card.py` | REEMPLAZAR | Eliminar `style=""` estáticos; usar clases CSS |
| `src/interface/design/components/performance_indicator.py` | REEMPLAZAR | Eliminar `style=""` estáticos; solo conservar dinámicos |
| `src/interface/design/components/page_header.py` | REEMPLAZAR | Eliminar `style=""` estáticos; usar `btn_*()` |
| `src/interface/design/components/data_table.py` | REEMPLAZAR | Eliminar `style=""` estáticos |
| `src/interface/design/components/base_form.py` | REEMPLAZAR | Eliminar `style=""` estáticos; usar `btn_*()` |
| `src/interface/design/components/confirm_dialog.py` | REEMPLAZAR | Eliminar `style=""` estáticos; usar `btn_*()` |
| `src/interface/design/components/confirmation_card.py` | REEMPLAZAR | Eliminar `style=""` estáticos dinámicos separados de estáticos; usar `btn_*()` |
| `src/interface/pages/admin/*.py` (6 archivos) | MODIFICAR | Reemplazar `ui.button().props("flat*")` con `btn_*()`|
| `src/interface/pages/academico/*.py` (3 archivos) | MODIFICAR | Ídem |
| `src/interface/pages/evaluacion/*.py` (6 archivos) | MODIFICAR | Ídem |
| `src/interface/pages/login.py` | MODIFICAR | Ídem |
| `src/interface/design/layout.py` | MODIFICAR | Reemplazar `ui.button` del logout con `btn_icon()` |
| `src/interface/design/components/context_selector.py` | MODIFICAR | Reemplazar `ui.button` de cierre con `btn_icon()` |

---

## Diseño de `buttons.py` — API completa

```python
# Firma canónica de cada función pública

def btn_primary(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button: ...

def btn_secondary(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button: ...

def btn_danger(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button: ...

def btn_ghost(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button: ...

def btn_icon(
    icono: str,
    on_click: Callable | None = None,
    *,
    tooltip: str = "",
    variante: Literal["primary", "secondary", "danger", "ghost"] = "ghost",
    size: Literal["sm", "md"] = "md",
) -> ui.button: ...
```

### Regla de construcción interna

```python
def _build(
    text: str | None,
    on_click,
    variant: str,
    icon: str | None,
    size: str | None,
    disabled: bool,
) -> ui.button:
    btn = ui.button(text or "", on_click=on_click, color=None, icon=icon)
    clases = f"btn btn-{variant}"
    if size == "sm":
        clases += " btn-sm"
    elif size == "lg":
        clases += " btn-lg"
    btn.classes(clases)
    if disabled:
        btn.props("disable")
    return btn
```

`color=None` es la clave: bloquea que Quasar inyecte `.bg-primary`, `.text-white`, etc.
Sin esto, Quasar sobreescribe los colores definidos en `.btn-primary`.

### btn_icon — construcción

```python
def btn_icon(icono, on_click=None, *, tooltip="", variante="ghost", size="md"):
    size_cls = "btn-icon-sm" if size == "sm" else "btn-icon"
    btn = ui.button(icon=icono, on_click=on_click, color=None)
    btn.classes(f"btn {size_cls} btn-{variante}")
    if tooltip:
        btn.tooltip(tooltip)
    return btn
```

---

## Nuevas clases CSS en styles.css

### Botones nuevos

```css
/* btn-ghost: plano, sin borde, color primario en hover */
.btn-ghost {
  background: transparent;
  color: var(--color-text-secondary);
  border-color: transparent;
}
.btn-ghost:hover {
  background: var(--color-surface-alt);
  color: var(--color-text-primary);
}

/* btn-icon: botón circular solo-icono */
.btn-icon {
  width: 36px;
  height: 36px;
  min-width: 36px;
  padding: 0;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-color: transparent;
  background: transparent;
  color: var(--color-text-secondary);
}
.btn-icon:hover {
  background: var(--color-surface-alt);
  color: var(--color-text-primary);
}
.btn-icon-sm {
  width: 28px;
  height: 28px;
  min-width: 28px;
  padding: 0;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-color: transparent;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 14px;
}
.btn-icon-sm:hover {
  background: var(--color-surface-alt);
  color: var(--color-text-primary);
}
```

### Clases CSS nuevas para components (reemplazan style="")

```css
/* stat_card */
.stat-card          { min-width: 200px; flex: 1; padding: var(--space-lg); }
.stat-card-header   { width: 100%; margin-bottom: var(--space-md); }
.stat-card-label    { color: var(--color-text-secondary); font-size: var(--font-size-small);
                      font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.stat-card-value    { color: var(--color-text-primary); line-height: 1.1; margin-top: 2px; }
.stat-card-sub      { color: var(--color-text-secondary); font-size: var(--font-size-small); margin-top: 4px; }
.stat-icon-circle   { border-radius: 50%; width: 48px; height: 48px; flex-shrink: 0;
                      display: flex; align-items: center; justify-content: center; }
/* variantes de icono: background dinámico se sigue pasando via style= porque depende de variante */

/* performance_indicator */
.perf-root          { width: 100%; }
.perf-header        { width: 100%; margin-bottom: 4px; }
.perf-label         { color: var(--color-text-secondary); font-size: var(--font-size-small); font-weight: 500; }
.perf-value         { color: var(--color-text-primary); font-size: var(--font-size-small); font-weight: 600; }
.perf-nivel         { font-size: var(--font-size-small); font-weight: 500; }
/* color de .perf-nivel es dinámico → style= aceptado */
.perf-bar-track     { width: 100%; background: var(--color-bg); border-radius: 999px;
                      overflow: hidden; border: 1px solid var(--color-divider); }
.perf-bar-fill      { height: 100%; border-radius: 999px; transition: width 0.4s ease; }
/* height del track y width+background del fill son dinámicos → style= aceptados */

/* page_header */
.page-header-row    { width: 100%; margin-bottom: var(--space-lg);
                      padding-bottom: var(--space-md); border-bottom: 1px solid var(--color-divider); }
.page-header-title  { color: var(--color-text-primary); line-height: 1.2; }
.page-header-sub    { color: var(--color-text-secondary); font-size: var(--font-size-small); margin-top: 2px; }

/* data_table */
.data-table-search  { max-width: 280px; }
.data-table-root    { width: 100%; }
.data-table-clickable { cursor: pointer; }

/* base_form */
.base-form-card     { width: 100%; padding: var(--space-lg); background: var(--color-surface); }
.base-form-title    { color: var(--color-text-primary); margin-bottom: var(--space-md); }
.base-form-sep      { margin: var(--space-md) 0; background: var(--color-divider); }
.base-form-footer   { width: 100%; }
/* col_style: grid-template-columns es dinámico (columnas=1|2) → style= aceptado para esa propiedad */

/* confirm_dialog */
.confirm-dialog-card  { min-width: 380px; max-width: 480px; }
.confirm-dialog-head  { margin-bottom: var(--space-md); }
.confirm-dialog-body  { color: var(--color-text-secondary); font-size: var(--font-size-body);
                        line-height: 1.6; margin-bottom: var(--space-lg); }
.confirm-dialog-foot  { margin-top: var(--space-md); }

/* confirmation_card */
.confirm-card-inner   { flex: 1; }
.confirm-card-title   { /* color es dinámico (variante) → style= aceptado */ }
.confirm-card-body    { color: var(--color-text-primary); font-size: var(--font-size-body); line-height: 1.5; }
.confirm-card-actions { margin-top: var(--space-sm); }
/* background y border-left del card raíz son dinámicos → style= aceptado */
/* padding y width del card raíz → mover a clase .andes-card ya tiene padding */
```

---

## Tabla de conversión: props Quasar → btn_*()

| Patrón actual en páginas | Función de reemplazo | Notas |
|--------------------------|---------------------|-------|
| `ui.button("X").props("flat")` | `btn_ghost("X", ...)` | Botón plano terciario |
| `ui.button("X").props("flat dense no-caps")` | `btn_ghost("X", ...)` | Ídem, quitar props |
| `ui.button("X").props("outlined")` | `btn_secondary("X", ...)` | Borde + fondo vacío |
| `ui.button("X").props("outlined dense")` | `btn_secondary("X", ...)` | Ídem |
| `ui.button("X").props("outline color=primary")` | `btn_secondary("X", ...)` | Ídem |
| `ui.button("X").props("unelevated")` | `btn_primary("X", ...)` | Sólido sin sombra |
| `ui.button(icon="X").props("flat round dense")` | `btn_icon("X", ...)` | Solo-icono circular |
| `ui.button(icon="X").props("flat round dense size=xs")` | `btn_icon("X", ..., size="sm")` | Ídem pequeño |
| `ui.button("X", color="primary")` | `btn_primary("X", ...)` | Color nativo → btn_primary |
| `ui.button("X", color="negative")` | `btn_danger("X", ...)` | Color nativo → btn_danger |

### Casos especiales con context manager (botones con contenido hijo)

```python
# ANTES — patrón en layout.py para logout
with ui.button(on_click=lambda: ui.navigate.to("/logout")).props("flat round dense"):
    ThemeManager.icono(Icons.LOGOUT, size=18)

# DESPUÉS — btn_icon se encarga del layout
btn_icon(Icons.LOGOUT, on_click=lambda: ui.navigate.to("/logout"), tooltip="Cerrar sesión")
```

```python
# ANTES — patrón en context_selector.py para cerrar dialog
ui.button(icon="close", on_click=dialog.close).props("flat round dense")

# DESPUÉS
btn_icon("close", on_click=dialog.close, tooltip="Cerrar")
```

---

## Alternativa descartada: Quasar theming global

Se evaluó modificar la configuración de Quasar para que sus props nativos (flat, outlined)
produzcan el look del design system. Se descartó porque:

1. NiceGUI no expone la API de Quasar theming de forma estable (varía entre versiones)
2. Requeriría inyectar JS de configuración de Quasar fuera del ciclo de NiceGUI
3. No daría trazabilidad: un revisor no podría saber qué variante visual tiene un botón
   leyendo solo el código Python; necesitaría leer la config Quasar global

La fábrica `btn_*()` es explícita, legible y verificable con `grep`.

---

## Dependencias entre tareas

```
T1 (CSS en styles.css)
  ↓
T2 (buttons.py completo + __init__.py)
  ↓
T3 (components usan clases CSS + btn_*())
  ↓
T4 (pages usan btn_*())
```

T4 puede ejecutarse en paralelo por módulo (admin, academico, evaluacion, login, layout).
