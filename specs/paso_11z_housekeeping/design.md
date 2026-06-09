# Diseño — paso_11z_housekeeping

## Estrategia general

Refactor mecánico, archivo por archivo, validando con `python init.py` después de cada
archivo. Ningún cambio cruzado: cada archivo es una unidad atómica.

Cuando aparece una clase Tailwind-style nueva, se añade a `styles.css` **solo si no
existe equivalente** en el design system. La lista de clases utilitarias nuevas que se
agregan está acotada y se documenta abajo (§F).

## A. Sustitución de `ui.icon()` por `ThemeManager.icono()`

**Mapeo:**

```python
# Antes
ui.icon("warning", size="lg", color="warning")

# Después
ThemeManager.icono(
    "warning",
    size=24,           # "sm"=20, "md"=24, "lg"=32, "xl"=48
    color="var(--color-warning)",
)
```

Mapeo de tamaños Quasar → Material Symbols:

| Quasar | px |
|---|---|
| `xs` | 16 |
| `sm` | 20 |
| `md` | 24 (default) |
| `lg` | 32 |
| `xl` | 48 |

**Casos especiales:**

- `habilitaciones.py:453`: `ui.icon("construction", size="lg", color="#d97706")`.
  Se reemplaza por `ThemeManager.icono("construction", size=32, color="var(--color-warning)")`.
  `#d97706` ≈ warning del design system. Si el reviewer rechaza el cambio visual, se
  abre ticket para añadir `--color-warning-strong`.

**Lista completa (24 ocurrencias):**

| Archivo | Líneas |
|---|---|
| `admin/configuracion_sie.py` | 597, 629, 639, 652, 684, 696, 718, 748, 767 |
| `evaluacion/configuracion_evaluacion.py` | 364, 373, 510, 524, 546 |
| `evaluacion/habilitaciones.py` | 283, 453, 500 |
| `evaluacion/planes_mejoramiento.py` | 287, 337, 398 |
| `evaluacion/planilla_notas.py` | 395, 418, 666, 674 |

## B. `ui.button(icon=…)` → `with ui.button(): ThemeManager.icono(...)`

Tres botones en `estudiantes.py`:

```python
# Antes (línea 321 ejemplo)
ui.button(icon="edit", on_click=_fila_editar)

# Después
with ui.button(on_click=_fila_editar).props("flat round").classes("btn-icon-table"):
    ThemeManager.icono(Icons.EDIT, size=18)
```

La clase `.btn-icon-table` se reutiliza del design system existente
(verificar en `styles.css` antes de la implementación; si no existe, usar `btn-ghost`).

## C. Colores Quasar hardcodeados

```python
# estudiantes.py:307 — Antes
_piar_color = "teal" if fila["posee_piar"] else "grey-4"
ui.badge("PIAR", color=_piar_color)

# Después
clase_piar = "badge-info" if fila["posee_piar"] else "badge-neutral"
ui.html(f'<span class="badge {clase_piar}">PIAR</span>')
```

```python
# planes_mejoramiento.py:290 — Antes
ui.badge("Sin corte", color="grey").classes("text-xs")

# Después
ui.html('<span class="badge badge-neutral text-xs">Sin corte</span>')
```

Estas clases (`badge-info`, `badge-neutral`) ya existen en el design system (ver
`status_badge.py`).

## D. `cellStyle` en ag-Grid (planilla_notas.py)

Añadir a `styles.css` bajo la sección de ag-Grid:

```css
.ag-theme-balham .ag-cell-xs   { font-size: 11px; }
.ag-theme-balham .ag-cell-info  { color: var(--color-info); }
.ag-theme-balham .ag-cell-error { color: var(--color-error); }
```

Migración:

```python
# Antes
"cellStyle": {"fontSize": "11px"}
# Después
"cellClass": "ag-cell-xs"

# Antes
"cellStyle": {"color": "#0284C7"}
# Después
"cellClass": "ag-cell-info"

# Antes
"cellStyle": {"color": "#DC2626"}
# Después
"cellClass": "ag-cell-error"
```

Nota: el añadido a `styles.css` es la **única** excepción al alcance "solo páginas" de
este paso. Es necesario para resolver D sin contaminar futuros pasos.

## E. Imports prohibidos de `src.domain.models`

| Archivo | Import actual | Estrategia |
|---|---|---|
| `configuracion_sie.py:32` | `from src.domain.models.configuracion import …` | Mover a `if TYPE_CHECKING:` y depender solo del servicio para datos en runtime. |
| `habilitaciones.py:30` | `from src.domain.models.nivelacion import …` | Idem. |
| `estadisticos.py:34` | `from src.domain.models.dtos import …` | Idem. Posible re-export desde `src.services.*` si se usa intensivamente — decisión del implementer durante la tarea, justificada en `progress/impl_11z.md`. |

Patrón:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.models.configuracion import ConfiguracionSIE
```

Esto satisface el linter del design system (no es import en runtime) y mantiene
los tipos para Pylance/mypy.

## F. Clases CSS Tailwind-style no soportadas — mapeo

### F.1. Quasar grid columns (5 ocurrencias)

| Tailwind/Quasar | Reemplazo |
|---|---|
| `col-2` | `flex-2` (añadir en styles.css: `.flex-2 { flex: 2; min-width: 0; }`) |
| `col-3` | `flex-3` |
| `col-4` | `flex-4` |

Las nuevas clases utilitarias se añaden a `styles.css` en un bloque
`/* ── Utilidades de layout ───────────────────── */`.

### F.2. Tailwind backgrounds (3 ocurrencias)

| Tailwind | Reemplazo del design system |
|---|---|
| `bg-blue-50` | `bg-info-soft` (nueva: `.bg-info-soft { background: var(--color-info-light); }`) |
| `bg-amber-50` | `bg-warning-soft` (nueva: `.bg-warning-soft { background: var(--color-warning-light); }`) |
| `border-amber-200` | `border-warning-soft` (nueva: `.border-warning-soft { border: 1px solid var(--color-warning); }`) |

### F.3. Tailwind dividers/grid (4 ocurrencias)

| Tailwind | Reemplazo |
|---|---|
| `divide-y` | `divider-y` (`.divider-y > * + * { border-top: 1px solid var(--color-divider); }`) |
| `divide-grey-3` | borrar (redundante con `.divider-y`) |
| `grid-cols-1` | `grid-1` (`.grid-1 { display: grid; grid-template-columns: 1fr; }`) |
| `lg:grid-cols-2` | `grid-2-lg` (`.grid-2-lg { display: grid; grid-template-columns: 1fr; } @media (min-width: 1024px) { .grid-2-lg { grid-template-columns: 1fr 1fr; } }`) |

### F.4. Tailwind flex/sizing (8 ocurrencias)

| Tailwind | Reemplazo |
|---|---|
| `flex-shrink-0`, `shrink-0` | `no-shrink` (`.no-shrink { flex-shrink: 0; }`) |
| `truncate` | `text-truncate` (`.text-truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }`) |
| `max-w-full` | `max-w-full` (mantener clase pero definir: `.max-w-full { max-width: 100%; }`) |
| `border-t` | `border-top-soft` (`.border-top-soft { border-top: 1px solid var(--color-divider); }`) |
| `h-[600px]` | clase `h-grid-default` (`.h-grid-default { height: 600px; }`) — uso específico de planilla |
| `w-px` | `w-px` (definir: `.w-px { width: 1px; }`) |
| `h-full` | `h-full` (definir: `.h-full { height: 100%; }`) |

### F.5. Total de clases utilitarias nuevas a añadir a styles.css

13 clases. Todas se agrupan en un bloque al final del archivo:

```css
/* ════════════════════════════════════════════════════════════════
   Utilidades — añadidas en paso_11z para sustituir Tailwind ad-hoc
   ════════════════════════════════════════════════════════════════ */
.flex-2, .flex-3, .flex-4 { … }
.bg-info-soft, .bg-warning-soft, .border-warning-soft { … }
.divider-y > * + * { … }
.grid-1, .grid-2-lg { … }
.no-shrink, .text-truncate, .border-top-soft { … }
.h-grid-default, .w-px, .h-full, .max-w-full { … }
```

Este es el **único cambio aceptado fuera de pages/** en este paso. Justificado en
`progress/impl_11z.md`.

## Alternativa descartada

**Adoptar Tailwind oficialmente en NiceGUI.** Descartada: NiceGUI ya inyecta Quasar +
nuestro design system; añadir Tailwind multiplica peso del bundle, fuerza migración
masiva en pasos futuros, y choca con la regla del proyecto de "fuente canónica es
styles.css". Definir 13 clases utilitarias propias es contención de daños suficiente.

## Orden de ejecución

1. Añadir clases utilitarias a `styles.css` (T1) — desbloquea las demás tareas.
2. Por archivo (T2..T11), en orden de menor a mayor impacto.
3. Verificación final (T12).

Después de cada archivo, ejecutar `python init.py` y confirmar reducción de violaciones.
