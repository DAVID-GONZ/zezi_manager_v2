# Tasks — paso_10i: Saneamiento del Design System

> Estado: **spec_ready** — esperando aprobación de David para iniciar implementación.

---

## T1 — Añadir clases CSS en `styles.css`

**Artefacto:** `src/interface/design/styles.css` (modificado)

Añadir al final del archivo las clases listadas en `design.md §"Clases CSS nuevas para components"` y `design.md §"Botones nuevos"`:
- `.btn-ghost`, `.btn-ghost:hover`
- `.btn-icon`, `.btn-icon:hover`
- `.btn-icon-sm`, `.btn-icon-sm:hover`
- `.stat-card`, `.stat-card-header`, `.stat-card-label`, `.stat-card-value`, `.stat-card-sub`, `.stat-icon-circle`
- `.perf-root`, `.perf-header`, `.perf-label`, `.perf-value`, `.perf-nivel`, `.perf-bar-track`, `.perf-bar-fill`
- `.page-header-row`, `.page-header-title`, `.page-header-sub`
- `.data-table-search`, `.data-table-root`, `.data-table-clickable`
- `.base-form-card`, `.base-form-title`, `.base-form-sep`, `.base-form-footer`
- `.confirm-dialog-card`, `.confirm-dialog-head`, `.confirm-dialog-body`, `.confirm-dialog-foot`
- `.confirm-card-inner`, `.confirm-card-body`, `.confirm-card-actions`

**Verificación:**
```python
python -c "
import pathlib
css = pathlib.Path('src/interface/design/styles.css').read_text(encoding='utf-8')
clases = ['.btn-ghost','.btn-icon','.btn-icon-sm','.stat-card','.perf-bar-track',
          '.page-header-row','.data-table-search','.base-form-card',
          '.confirm-dialog-card','.confirm-card-body']
for c in clases:
    assert c in css, f'Falta: {c}'
print('T1 OK — todas las clases presentes')
"
```

---

## T2 — Completar y exportar `buttons.py`

**Artefacto:** `src/interface/design/components/buttons.py` (reemplazado)

Reemplazar el contenido actual con la implementación completa definida en `design.md §"Diseño de buttons.py"`:

```python
"""
buttons.py — Fábrica centralizada de botones del Design System Andes Minimal v2.

Regla: TODA creación de botón en src/interface/ pasa por estas funciones.
       Prohibido: ui.button().props("flat"), ui.button(color="primary"), etc.

Por qué color=None es obligatorio:
  Quasar (el framework CSS de NiceGUI) inyecta clases .bg-primary, .text-white, etc.
  cuando se pasa color="primary". Esas clases sobreescriben los estilos de .btn-primary
  definidos en styles.css. color=None bloquea esa inyección.
"""
from __future__ import annotations

from typing import Callable, Literal

from nicegui import ui


def _build(
    text: str,
    on_click: Callable | None,
    variant: str,
    icon: str | None,
    size: str | None,
    disabled: bool,
) -> ui.button:
    btn = ui.button(text, on_click=on_click, color=None, icon=icon)
    clases = f"btn btn-{variant}"
    if size == "sm":
        clases += " btn-sm"
    elif size == "lg":
        clases += " btn-lg"
    btn.classes(clases)
    if disabled:
        btn.props("disable")
    return btn


def btn_primary(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button:
    """Acción principal — fondo sólido primario."""
    return _build(text, on_click, "primary", icon, size, disabled)


def btn_secondary(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button:
    """Acción secundaria — borde primario, fondo transparente."""
    return _build(text, on_click, "secondary", icon, size, disabled)


def btn_danger(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button:
    """Acción destructiva — fondo rojo."""
    return _build(text, on_click, "danger", icon, size, disabled)


def btn_ghost(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button:
    """Acción terciaria / cancelar — plano, sin borde."""
    return _build(text, on_click, "ghost", icon, size, disabled)


def btn_icon(
    icono: str,
    on_click: Callable | None = None,
    *,
    tooltip: str = "",
    variante: Literal["primary", "secondary", "danger", "ghost"] = "ghost",
    size: Literal["sm", "md"] = "md",
) -> ui.button:
    """
    Botón solo-icono circular.
    Reemplaza: ui.button(icon=X).props("flat round dense")
    """
    size_cls = "btn-icon-sm" if size == "sm" else "btn-icon"
    btn = ui.button(icon=icono, on_click=on_click, color=None)
    btn.classes(f"btn {size_cls} btn-{variante}")
    if tooltip:
        btn.tooltip(tooltip)
    return btn


__all__ = ["btn_primary", "btn_secondary", "btn_danger", "btn_ghost", "btn_icon"]
```

**Añadir a `components/__init__.py`** (después de las exportaciones existentes):
```python
from .buttons import btn_primary, btn_secondary, btn_danger, btn_ghost, btn_icon
```
Y actualizar `__all__` con los cinco nombres.

**Verificación:**
```python
python -c "
from src.interface.design.components import btn_primary, btn_secondary, btn_danger, btn_ghost, btn_icon
print('T2 OK — btn_* importables desde components')
"
```

---

## T3 — Sanear los 7 archivos de components

**Artefacto:** 7 archivos en `src/interface/design/components/` (reemplazados)

Para cada archivo, aplicar la tabla de conversión `style=""` → `.classes("clase")` definida en `design.md §"Clases CSS nuevas para components"`. Los únicos `style=""` que sobreviven son valores genuinamente dinámicos:

| Archivo | style= dinámico permitido | style= estático a eliminar |
|---------|--------------------------|---------------------------|
| `stat_card.py` | `f"background:{icono_bg}"` (el icono_bg es la variable CSS `--color-{variante}-light`) | Todo lo demás |
| `performance_indicator.py` | `f"height:{altura}px"` (track), `f"width:{pct:.1f}%; background:{barra_color}"` (fill) | Todo lo demás |
| `page_header.py` | Ninguno | Todo |
| `data_table.py` | Ninguno | Todo |
| `base_form.py` | `f"grid-template-columns:repeat({columnas},1fr); gap:var(--space-md);"` (solo las columnas dinámicas) | Todo lo demás |
| `confirm_dialog.py` | Ninguno | Todo (incluyendo el bug `margin-bottom:var(--color-divider)`) |
| `confirmation_card.py` | `f"background:{bg_color}; border-left:4px solid {icono_color};"` | `padding:var(--space-md); width:100%;` — mover a clase `.andes-card` |

Además, en `stat_card.py` reemplazar el dict `_BG_MAP` de hex hardcodeados por referencias a variables CSS:
```python
# ANTES (hex hardcodeado)
"success": "#E8F5E9",

# DESPUÉS (variable CSS — coincide con tokens.py y styles.css)
"success": "var(--color-success-light)",
```

Y en `confirm_dialog.py`, `confirmation_card.py`, `page_header.py`, `base_form.py`:
reemplazar `ui.button(...).classes("btn-primary")` etc. con `btn_primary(...)`, `btn_secondary(...)`, `btn_danger(...)`.

**Verificación:**
```python
python -c "
import pathlib, re, sys
archivos = [
    'src/interface/design/components/stat_card.py',
    'src/interface/design/components/performance_indicator.py',
    'src/interface/design/components/page_header.py',
    'src/interface/design/components/data_table.py',
    'src/interface/design/components/base_form.py',
    'src/interface/design/components/confirm_dialog.py',
    'src/interface/design/components/confirmation_card.py',
]
errores = []
for fp in archivos:
    src = pathlib.Path(fp).read_text(encoding='utf-8')
    # Detectar style= con valores estáticos (no contiene { ni f-string variables)
    matches = re.findall(r'\.style\([\"\']((?:[^{}\"\'\\\\])+)[\"\']', src)
    for m in matches:
        errores.append(f'{fp}: style con valor potencialmente estático: {m[:60]}')
if errores:
    for e in errores: print('WARN:', e)
else:
    print('T3 OK — sin style= estáticos detectados en components')
"
```

---

## T4a — Inyectar `btn_*()` en páginas admin

**Artefacto:** 6 archivos en `src/interface/pages/admin/` (modificados)

Archivos: `grupos.py`, `asignaturas.py`, `asignaciones.py`, `usuarios.py`, `configuracion_sie.py`, `configuracion_institucion.py`

Aplicar la tabla de conversión de `design.md §"Tabla de conversión"`.

Cada archivo debe añadir al bloque de imports:
```python
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_danger, btn_ghost, btn_icon
```

Solo importar los `btn_*` que realmente se usen en ese archivo.

**Verificación:**
```python
python -c "
import ast, pathlib
pages = list(pathlib.Path('src/interface/pages/admin').glob('*.py'))
for p in pages:
    if p.name == '__init__.py': continue
    src = p.read_text(encoding='utf-8')
    tree = ast.parse(src)
    raw_btns = [n for n in ast.walk(tree)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == 'button'
                and isinstance(n.func.value, ast.Attribute)
                and n.func.value.attr == 'ui']
    if raw_btns:
        print(f'PENDIENTE {p.name}: {len(raw_btns)} ui.button() sin migrar')
    else:
        print(f'OK {p.name}')
"
```

---

## T4b — Inyectar `btn_*()` en páginas academico

**Artefacto:** `registro_asistencia.py`, `estudiantes.py`, `horarios.py` (modificados)

Igual que T4a pero en `src/interface/pages/academico/`.

`registro_asistencia.py` ya usa `abrir_selector` del design system;
asegurarse de que sus `ui.button().props("flat dense no-caps")` también migran.

**Verificación:** igual que T4a pero path `src/interface/pages/academico`.

---

## T4c — Inyectar `btn_*()` en páginas evaluacion

**Artefacto:** 6 archivos en `src/interface/pages/evaluacion/` (modificados)

Igual que T4a. `planilla_notas.py` tiene el mayor número de botones (9 `ui.button()`
incluyendo botones `size=xs` → `btn_icon(..., size="sm")`).

**Verificación:** igual que T4a pero path `src/interface/pages/evaluacion`.

---

## T4d — Inyectar `btn_*()` en login, layout y context_selector

**Artefacto:** `src/interface/pages/login.py`, `src/interface/design/layout.py`, `src/interface/design/components/context_selector.py` (modificados)

- `login.py`: 3 botones con `.props("outlined dense")` y `.props("unelevated")` → `btn_secondary`, `btn_primary`
- `layout.py`: botón logout con context manager → `btn_icon(Icons.LOGOUT, on_click=..., tooltip="Cerrar sesión")`
- `context_selector.py`: botón cierre del dialog → `btn_icon("close", on_click=dialog.close)`, botones "Cancelar" y "Aplicar contexto" → `btn_ghost` y `btn_primary`

**Verificación:**
```python
python -c "
import pathlib, re
for fp in ['src/interface/pages/login.py',
           'src/interface/design/layout.py',
           'src/interface/design/components/context_selector.py']:
    src = pathlib.Path(fp).read_text(encoding='utf-8')
    raw = len(re.findall(r'ui\.button\(', src))
    # login.py y context_selector.py pueden tener 0 ui.button() si migran 100%
    # layout.py también debería llegar a 0
    print(f'{fp}: {raw} ui.button() restantes')
"
```

---

## T5 — Verificación final

```python
# 1. Tests completos
# PowerShell:
$env:PYTHONIOENCODING="utf-8"
python -m pytest tests/ -q --tb=short

# 2. Import check completo
python -c "
from src.interface.design.components import (
    btn_primary, btn_secondary, btn_danger, btn_ghost, btn_icon,
    status_badge, confirm_dialog, page_header, stat_card, data_table,
    context_chip, performance_indicator, base_form,
)
print('Import OK — todos los components exportados correctamente')
"

# 3. Sin ui.button crudo en pages (debe devolver 0 archivos con ui.button no migrado)
python -c "
import pathlib, re
pages = list(pathlib.Path('src/interface/pages').rglob('*.py'))
for p in pages:
    if p.name == '__init__.py': continue
    src = p.read_text(encoding='utf-8')
    count = len(re.findall(r'ui\.button\(', src))
    if count > 0:
        print(f'PENDIENTE {p.name}: {count} ui.button() sin migrar')
print('T5 OK si no hubo líneas PENDIENTE')
"
```

---

## Orden de ejecución recomendado

```
T1 → T2 → T3 → T4a + T4b + T4c + T4d (paralelo) → T5
```

T4a/b/c/d son independientes entre sí y pueden ejecutarse en paralelo.

---

## Resultado esperado

Tras este paso:
- 0 archivos en `src/interface/design/components/` con `style=""` estático
- 0 páginas con `ui.button().props("flat*")` sin migrar
- `btn_primary/secondary/danger/ghost/icon` disponibles y usados en toda la interfaz
- 607+ tests pasando
- `progress/impl_paso_10i.md` con checklist de tareas completadas
