# Requirements — paso_10i: Saneamiento del Design System

> Notación EARS. Fuente de verdad: `docs/conventions.md §6`, `src/interface/design/styles.css`, `src/interface/design/components/`.

---

## Contexto del problema

### Violación A — CSS estático en `style=""` dentro de components

`conventions.md §6` establece:
> Todo el CSS vive en styles.css. Solo se usan `.classes("nombre-clase")`.
> `style=""` solo es válido para valores **calculados dinámicamente en Python**.

**Todos** los archivos en `src/interface/design/components/` (excepto `context_selector.py`)
violan esta regla con `style=""` que contiene valores estáticos (colores de tokens,
espaciados, bordes, tipografía).

Ejemplos concretos:

| Archivo | Violación |
|---------|-----------|
| `stat_card.py` | `style("min-width:200px; padding:var(--space-lg)")` — layout estático |
| `stat_card.py` | `_BG_MAP` con hex hardcodeados (`#E8F5E9`, `#FFF3E0`…) en lugar de variables CSS |
| `performance_indicator.py` | 100 % de estilos en `style=""`, solo 2 son realmente dinámicos |
| `page_header.py` | Border-bottom, márgenes y tipografía en `style=""` |
| `data_table.py` | `style("max-width:280px;")` y `style("cursor:pointer;")` estáticos |
| `base_form.py` | Todo el layout via `style=""` con valores estáticos |
| `confirm_dialog.py` | Dimensiones del card y tipografía en `style=""` + bug: usa `var(--color-divider)` como valor de `margin` |
| `confirmation_card.py` | `padding:var(--space-md); width:100%;` dentro de `style=f"background:..."` |

### Violación B — Components no usados en páginas

Auditoría de imports en `src/interface/pages/`:

| Component | Usado en páginas | Nota |
|-----------|-----------------|------|
| `status_badge` | `inicio.py` solamente | Parcialmente adoptado |
| `context_chip` | `registro_asistencia.py`, `layout.py` | OK |
| `abrir_selector` | `registro_asistencia.py` | OK |
| `page_header` | **0 páginas** | No adoptado |
| `stat_card` | **0 páginas** | `inicio.py` tiene copia inline |
| `data_table` | **0 páginas** | Páginas usan `ui.table()` o `ui.aggrid()` directo |
| `confirm_dialog` | **0 páginas** | Páginas construyen `ui.dialog()` ad-hoc |
| `confirmation_card` | **0 páginas** | No adoptado |
| `performance_indicator` | **0 páginas** | No adoptado |
| `base_form` | **0 páginas** | No adoptado |

### Violación C — Botones en páginas sin pasar por el design system

Las páginas usan Quasar props crudos en lugar de las abstracciones del design system:

```python
# ❌ Lo que hay — Quasar puro, sin design system
ui.button("Crear", on_click=...).props("flat")
ui.button(icon="edit", on_click=...).props("flat round dense")
ui.button("Guardar", on_click=...).props("unelevated")
ui.button("Cancelar", on_click=...).props("outlined dense")
```

`buttons.py` existe pero:
1. No está exportado en `components/__init__.py`
2. Le faltan variantes: `btn_ghost`, `btn_icon`, `btn_icon_sm`
3. No lo usa ninguna página ni componente

---

## Requisitos

### R1 — CSS puro en styles.css

**WHEN** un componente en `src/interface/design/components/` necesita aplicar estilos de layout, tipografía, espaciado, o colores de la paleta,
**THE** componente SHALL usar `.classes("nombre-clase")` con clases definidas en `styles.css`.

`style="..."` SHALL usarse **únicamente** para valores calculados en Python en tiempo de ejecución (porcentajes, colores computados según variante, alturas en px configurables).

### R2 — Sin hex hardcodeados fuera de tokens.py

**WHEN** un componente necesita un color de fondo de variante (éxito, error, warning, info),
**THE** componente SHALL referenciar la variable CSS correspondiente (`--color-success-light`, `--color-error-light`, etc.), no un hex literal.

### R3 — buttons.py: cinco variantes canónicas

**WHEN** cualquier parte de la interfaz necesita un botón interactivo,
**THE** sistema SHALL proveer las siguientes funciones en `buttons.py`:

| Función | Descripción | Quasar equiv. reemplazado |
|---------|-------------|--------------------------|
| `btn_primary(text, on_click, icon, size, disabled)` | Acción principal (fondo sólido primario) | `.props("unelevated")` + color |
| `btn_secondary(text, on_click, icon, size, disabled)` | Acción secundaria (borde, fondo transparente) | `.props("outlined")` |
| `btn_danger(text, on_click, icon, size, disabled)` | Acción destructiva (fondo rojo) | color="negative" |
| `btn_ghost(text, on_click, icon, size, disabled)` | Acción terciaria / cancelar (plano, sin borde) | `.props("flat")` |
| `btn_icon(icono, on_click, tooltip, variante, size)` | Botón solo-icono circular | `.props("flat round dense")` |

Todos los botones SHALL pasar `color=None` a `ui.button()` para bloquear la inyección de clases `.bg-*` de Quasar.

### R4 — buttons.py exportado desde __init__.py

**WHEN** se importa `from src.interface.design.components import btn_primary`,
**THE** import SHALL resolverse correctamente (buttons.py en `__init__.py`).

### R5 — Components internos usan btn_*()

**WHEN** `confirm_dialog`, `confirmation_card`, `page_header` o `base_form` crean botones,
**THE** componente SHALL llamar `btn_primary()`, `btn_secondary()` o `btn_danger()` en lugar de `ui.button(...).classes("btn-primary")`.

### R6 — Pages usan btn_*() para todos los botones

**WHEN** una página en `src/interface/pages/` necesita un botón interactivo,
**THE** página SHALL importar y usar la función `btn_*()` apropiada en lugar de `ui.button(...).props("flat")` o similares.

Scope de páginas: todas las páginas con `app_layout` que tienen llamadas a `ui.button()`.

### R7 — CSS completo para todas las variantes

**WHEN** se agregan variantes `btn-ghost` y `btn-icon` a buttons.py,
**THE** `styles.css` SHALL tener las clases `.btn-ghost`, `.btn-ghost:hover`, `.btn-icon`, `.btn-icon:hover`, `.btn-icon-sm`, y sus estados `:disabled`.

### R8 — 0 regresiones

**WHEN** se aplican todos los cambios,
**THE** suite de tests SHALL continuar en 607 passed (o más si se agregan tests).

---

## Lo que este paso NO hace

- No migra páginas de `ui.table()` a `data_table()` (data_table adoption es trabajo futuro)
- No migra páginas de cabeceras inline a `page_header()` (idem)
- No agrega tests nuevos de interfaz (NiceGUI UI tests están fuera del scope de unit tests)
- No toca `context_selector.py` (ya cumple las reglas de CSS)
- No toca `status_badge.py` (ya usa `ui.html` con clases CSS puras)
