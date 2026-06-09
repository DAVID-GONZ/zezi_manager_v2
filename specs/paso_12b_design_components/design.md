# Diseño — paso_12b_design_components

## Dependencias

Bloqueado por paso 12a (`styles/` debe existir como carpeta).

## 1. `empty_state.py`

### Estructura visual

```
┌─────────────────────────────────────────┐
│                                         │
│              ┌───────┐                  │
│              │  📂   │   ← icono 64px   │
│              └───────┘                  │
│                                         │
│         Título en h3                    │
│         Descripción en cuerpo gris      │
│                                         │
│         [ + Crear grupo ]               │
│                                         │
└─────────────────────────────────────────┘
```

Centrado horizontal y verticalmente en el contenedor padre. Ocupa al menos 320 px
de alto.

### Implementación

```python
# empty_state.py
from __future__ import annotations
from typing import Callable
from nicegui import ui

from ..theme import ThemeManager
from .buttons import btn_primary, btn_ghost

_VARIANTE_ICONO_COLOR = {
    "default": "var(--color-text-secondary)",
    "search":  "var(--color-text-secondary)",
    "error":   "var(--color-error)",
}

def empty_state(
    *,
    icono: str = "inbox",
    titulo: str,
    descripcion: str = "",
    cta_label: str | None = None,
    cta_on_click: Callable | None = None,
    cta_icono: str | None = None,
    variante: str = "default",
) -> None:
    color_icono = _VARIANTE_ICONO_COLOR.get(variante, _VARIANTE_ICONO_COLOR["default"])
    with ui.column().classes(f"empty-state empty-state--{variante}"):
        with ui.element("div").classes("empty-state__icon-wrap"):
            ThemeManager.icono(icono, size=48, color=color_icono)
        ui.label(titulo).classes("empty-state__title")
        if descripcion:
            ui.label(descripcion).classes("empty-state__description")
        if cta_label and cta_on_click:
            btn = btn_primary if variante != "error" else btn_ghost
            btn(cta_label, on_click=cta_on_click, icono=cta_icono)
```

### CSS — `styles/components/empty_state.css`

```css
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 320px;
  padding: var(--space-xl) var(--space-lg);
  gap: var(--space-md);
}

.empty-state__icon-wrap {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background: var(--color-secondary-light);
  margin-bottom: var(--space-sm);
}

.empty-state--error .empty-state__icon-wrap {
  background: var(--color-error-light);
}

.empty-state__title {
  font-size: var(--font-size-h3);
  font-weight: 600;
  color: var(--color-text-primary);
  max-width: 360px;
}

.empty-state__description {
  font-size: var(--font-size-body);
  color: var(--color-text-secondary);
  max-width: 420px;
  line-height: 1.5;
}
```

## 2. `skeleton_loader.py`

### Implementación

```python
from nicegui import ui

def skeleton_table(rows: int = 8, cols: int = 5) -> None:
    """Placeholder para una tabla mientras carga."""
    with ui.column().classes("skeleton-table"):
        # Header
        with ui.row().classes("skeleton-row skeleton-row--header"):
            for _ in range(cols):
                ui.element("div").classes("skeleton-bar skeleton-bar--header")
        # Body
        for _ in range(rows):
            with ui.row().classes("skeleton-row"):
                for _ in range(cols):
                    ui.element("div").classes("skeleton-bar")

def skeleton_cards(count: int = 4) -> None:
    with ui.row().classes("skeleton-cards"):
        for _ in range(count):
            with ui.column().classes("skeleton-card"):
                ui.element("div").classes("skeleton-bar skeleton-bar--lg")
                ui.element("div").classes("skeleton-bar skeleton-bar--sm")
                ui.element("div").classes("skeleton-bar skeleton-bar--xs")

def skeleton_form(fields: int = 6) -> None:
    with ui.column().classes("skeleton-form"):
        for _ in range(fields):
            with ui.column().classes("skeleton-form-field"):
                ui.element("div").classes("skeleton-bar skeleton-bar--label")
                ui.element("div").classes("skeleton-bar skeleton-bar--input")
```

### CSS — `styles/components/skeleton_loader.css`

```css
@keyframes shimmer {
  0%   { background-position: -800px 0; }
  100% { background-position:  800px 0; }
}

.skeleton-bar {
  height: 14px;
  border-radius: var(--radius-sm);
  background: linear-gradient(
    90deg,
    var(--color-secondary-light) 0%,
    var(--color-border) 50%,
    var(--color-secondary-light) 100%
  );
  background-size: 800px 100%;
  animation: shimmer 1.4s linear infinite;
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-bar { animation: none; }
}

.skeleton-bar--header { height: 20px; }
.skeleton-bar--lg     { height: 24px; width: 70%; }
.skeleton-bar--sm     { height: 14px; width: 50%; }
.skeleton-bar--xs     { height: 12px; width: 30%; }
.skeleton-bar--label  { height: 10px; width: 30%; }
.skeleton-bar--input  { height: 38px; width: 100%; border-radius: var(--radius-md); }

.skeleton-table { gap: 6px; padding: var(--space-md); }
.skeleton-row { display: flex; gap: 12px; }
.skeleton-row > .skeleton-bar { flex: 1; }

.skeleton-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-md);
}

.skeleton-card {
  padding: var(--space-md);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  gap: var(--space-sm);
}

.skeleton-form { gap: var(--space-md); }
.skeleton-form-field { gap: 6px; }
```

## 3. `toast.py`

### Implementación

```python
from __future__ import annotations
from typing import Callable
from nicegui import ui

_TIPO_CONFIG = {
    "info":    {"color": "info",     "icon": "info"},
    "success": {"color": "positive", "icon": "check_circle"},
    "warning": {"color": "warning",  "icon": "warning"},
    "error":   {"color": "negative", "icon": "error"},
}

def toast(
    mensaje: str,
    *,
    tipo: str = "info",
    duracion_ms: int = 4000,
    accion: dict | None = None,
    titulo: str | None = None,
) -> None:
    cfg = _TIPO_CONFIG.get(tipo, _TIPO_CONFIG["info"])
    # Mensaje combinado si hay título
    contenido = f"{titulo}\n{mensaje}" if titulo else mensaje

    kwargs = {
        "type": cfg["color"],
        "position": "bottom-right",
        "timeout": duracion_ms,
        "icon": cfg["icon"],
        "classes": f"andes-toast andes-toast--{tipo}",
    }
    # NiceGUI permite "actions" como lista de dicts
    if accion:
        kwargs["actions"] = [
            {"label": accion["label"], "handler": accion["on_click"], "color": "white"}
        ]
    if duracion_ms == 0:
        kwargs["close_button"] = "Cerrar"

    ui.notify(contenido, **kwargs)

def toast_info(mensaje: str, **kw):    toast(mensaje, tipo="info", **kw)
def toast_success(mensaje: str, **kw): toast(mensaje, tipo="success", **kw)
def toast_warning(mensaje: str, **kw): toast(mensaje, tipo="warning", **kw)
def toast_error(mensaje: str, **kw):   toast(mensaje, tipo="error", **kw)
```

### CSS — `styles/components/toast.css`

Pequeño, sobre todo overrides al `q-notification` que NiceGUI genera:

```css
.andes-toast {
  border-radius: var(--radius-md) !important;
  font-family: var(--font-family) !important;
  font-size: var(--font-size-body) !important;
  box-shadow: var(--shadow-lg) !important;
  border-left: 4px solid currentColor;
  padding: 12px 16px !important;
}

.andes-toast--info    { color: var(--color-info)    !important; }
.andes-toast--success { color: var(--color-success) !important; }
.andes-toast--warning { color: var(--color-warning) !important; }
.andes-toast--error   { color: var(--color-error)   !important; }
```

## 4. Registro

`src/interface/design/components/__init__.py` añade:

```python
from .empty_state import empty_state
from .skeleton_loader import skeleton_table, skeleton_cards, skeleton_form
from .toast import toast, toast_info, toast_success, toast_warning, toast_error

__all__ += [
    "empty_state",
    "skeleton_table",
    "skeleton_cards",
    "skeleton_form",
    "toast",
    "toast_info",
    "toast_success",
    "toast_warning",
    "toast_error",
]
```

`theme.py` (campo `CSS_LOAD_ORDER` definido en 12a) añade tres archivos:

```python
CSS_LOAD_ORDER = [
    ...,
    "components/empty_state.css",
    "components/skeleton_loader.css",
    "components/toast.css",
    ...,
]
```

## 5. Alternativa descartada

**Crear un componente `LoadingState(estado: Enum)` que unifique empty + loading +
error.** Descartada: empuja demasiada lógica al componente. Es más limpio que el
caller decida: si está cargando llama a `skeleton_*`; si terminó y no hay datos,
llama a `empty_state`. Sigue separation of concerns y permite skeletons
distintos por contexto.

## 6. Orden de tareas

1. T1: empty_state.py + CSS.
2. T2: skeleton_loader.py + CSS.
3. T3: toast.py + CSS.
4. T4: actualizar __init__.py.
5. T5: actualizar CSS_LOAD_ORDER en theme.py.
6. T6: tests unitarios.
7. T7: verificación final.
