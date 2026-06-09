# Tasks — paso_11z_housekeeping

## Resumen

| ID | Descripción | Archivos | Verificación |
|---|---|---|---|
| T1 | Añadir 13 utilidades CSS | `styles.css` | grep clases en styles.css |
| T2 | `estudiantes.py` — botones + Quasar color + col-N | `academico/estudiantes.py` | init.py: -7 |
| T3 | `horarios.py` — col-N | `academico/horarios.py` | init.py: -2 |
| T4 | `tablero_estadisticos.py` — sin cambios o nota | `academico/tablero_estadisticos.py` | nota progress |
| T5 | `configuracion_sie.py` — 9 ui.icon + import + 7 clases | `admin/configuracion_sie.py` | init.py: -17 |
| T6 | `cierre_periodo.py` — 1 clase | `evaluacion/cierre_periodo.py` | init.py: -1 |
| T7 | `configuracion_evaluacion.py` — 5 ui.icon + 1 clase | `evaluacion/configuracion_evaluacion.py` | init.py: -6 |
| T8 | `habilitaciones.py` — 3 ui.icon + import + 3 clases | `evaluacion/habilitaciones.py` | init.py: -7 |
| T9 | `planes_mejoramiento.py` — 3 ui.icon + Quasar grey + 1 clase | `evaluacion/planes_mejoramiento.py` | init.py: -5 |
| T10 | `planilla_notas.py` — 4 ui.icon + 3 cellStyle + 2 clases | `evaluacion/planilla_notas.py` | init.py: -9 |
| T11 | `estadisticos.py` — import + 1 clase | `informes/estadisticos.py` | init.py: -2 |
| T12 | Verificación final | — | init.py verde + 715 tests |

---

## T1 — Añadir utilidades CSS

**Prerequisito:** ninguno.

Leer `src/interface/design/styles.css` final del archivo.

Añadir bloque al final del archivo (antes de la última línea):

```css
/* ════════════════════════════════════════════════════════════════
   Utilidades — añadidas en paso_11z (cobertura Tailwind/Quasar)
   ════════════════════════════════════════════════════════════════ */
.flex-2 { flex: 2; min-width: 0; }
.flex-3 { flex: 3; min-width: 0; }
.flex-4 { flex: 4; min-width: 0; }

.bg-info-soft       { background: var(--color-info-light); }
.bg-warning-soft    { background: var(--color-warning-light); }
.border-warning-soft { border: 1px solid var(--color-warning); }

.divider-y > * + * { border-top: 1px solid var(--color-divider); }

.grid-1 { display: grid; grid-template-columns: 1fr; gap: var(--space-md); }
.grid-2-lg { display: grid; grid-template-columns: 1fr; gap: var(--space-md); }
@media (min-width: 1024px) {
  .grid-2-lg { grid-template-columns: 1fr 1fr; }
}

.no-shrink     { flex-shrink: 0; }
.text-truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.border-top-soft { border-top: 1px solid var(--color-divider); }

.h-grid-default { height: 600px; }
.h-full         { height: 100%; }
.w-px           { width: 1px; }
.max-w-full     { max-width: 100%; }

/* ag-Grid cell helpers (migración de cellStyle inline) */
.ag-theme-balham .ag-cell-xs    { font-size: 11px; }
.ag-theme-balham .ag-cell-info  { color: var(--color-info); }
.ag-theme-balham .ag-cell-error { color: var(--color-error); }
```

**Verificación:**
```
grep -c "flex-2\|bg-info-soft\|divider-y\|h-grid-default\|ag-cell-xs" src/interface/design/styles.css
# debe retornar >= 5
```

---

## T2 — `academico/estudiantes.py`

**Violaciones:**
- 3× `ui.button(icon=…)` (líneas 321, 326, 331)
- 1× color Quasar `teal`/`grey-4` (línea 307)
- 2× clases `col-3`, `col-4` (sin línea reportada → grep)

**Acciones:**

1. Reemplazar el patrón de columna `.classes("col-3")` por `.classes("flex-3")`, idem `col-4` → `flex-4`.
2. Reemplazar línea 307:
   ```python
   # Antes
   _piar_color = "teal" if fila["posee_piar"] else "grey-4"
   # Después (borrar la variable y el ui.badge correspondiente; usar ui.html)
   _piar_clase = "badge-info" if fila["posee_piar"] else "badge-neutral"
   ```
   Y en el `ui.badge(...)` correspondiente, cambiar por:
   ```python
   ui.html(f'<span class="badge {_piar_clase}">PIAR</span>')
   ```
3. Reemplazar los 3 botones (líneas 321, 326, 331):
   ```python
   # Antes
   ui.button(icon="edit", on_click=_fila_editar)
   # Después
   with ui.button(on_click=_fila_editar).props("flat round").classes("btn-icon-table"):
       ThemeManager.icono(Icons.EDIT, size=18)
   ```
   Idem `person_remove` → `Icons.DELETE` o nombre directo si no existe en `Icons`,
   y `description` → nombre directo `"description"`.

**Verificación:**
```
python init.py 2>&1 | grep estudiantes.py | wc -l   # debe bajar a 0
```

---

## T3 — `academico/horarios.py`

**Violaciones:** clases `col-2`, `col-3`.

**Acciones:** reemplazar `col-2` → `flex-2`, `col-3` → `flex-3` (grep en el archivo).

**Verificación:** `python init.py 2>&1 | grep horarios.py | wc -l` → 0.

---

## T4 — `academico/tablero_estadisticos.py`

**Violación:** `_repo()` directo en línea 763.

**Acción:** este punto es un bug arquitectónico de capa, no de design system. Está
fuera del scope del paso 11z **a menos** que init.py lo cuente como violación de
design system (el reporte lo lista pero bajo bloque distinto).

**Decisión del leader:** si init.py final sigue en verde con esta violación intacta
(porque no la marca como bloqueante en el bloque "DISEÑO"), dejar como está y abrir
ticket aparte `paso_11z_followup_capas`. Si la marca como bloqueante, el implementer
documenta el caso en `progress/impl_11z.md` §T4 y aplica el fix mínimo: usar
`Container.tablero_service()._repo` o el método público equivalente.

**Verificación:** `python init.py` ya no menciona `_repo()` o se mantiene en verde
global.

---

## T5 — `admin/configuracion_sie.py`

**Violaciones:**
- 9× `ui.icon()` (líneas 597, 629, 639, 652, 684, 696, 718, 748, 767)
- 1× import prohibido (línea 32)
- 7× clases CSS no definidas: `bg-blue-50`, `bg-amber-50`, `border-amber-200`,
  `divide-y`, `divide-grey-3`, `grid-cols-1`, `lg:grid-cols-2`

**Acciones:**

1. Línea 32: mover import dentro de `if TYPE_CHECKING:`.
2. Cada `ui.icon(...)` → `ThemeManager.icono(...)` (ver mapeo en design.md §A).
   - Asegurar `from src.interface.design.theme import ThemeManager` ya importado.
3. Reemplazos de clases:
   - `bg-blue-50` → `bg-info-soft`
   - `bg-amber-50` → `bg-warning-soft`
   - `border-amber-200` → `border-warning-soft`
   - `divide-y` → `divider-y`
   - `divide-grey-3` → borrar (redundante)
   - `grid-cols-1` → `grid-1`
   - `lg:grid-cols-2` → `grid-2-lg`

**Verificación:** `python init.py 2>&1 | grep configuracion_sie.py | wc -l` → 0.

---

## T6 — `evaluacion/cierre_periodo.py`

**Violación:** clase `flex-shrink-0`.

**Acción:** reemplazar por `no-shrink`.

---

## T7 — `evaluacion/configuracion_evaluacion.py`

**Violaciones:** 5× `ui.icon()` (364, 373, 510, 524, 546) + clase `bg-amber-50`.

**Acciones:**
1. Cada `ui.icon` → `ThemeManager.icono`.
2. `bg-amber-50` → `bg-warning-soft`.

---

## T8 — `evaluacion/habilitaciones.py`

**Violaciones:**
- 3× `ui.icon()` (283, 453, 500)
- Línea 453 contiene hex hardcodeado `#d97706`
- Import prohibido (línea 30)
- Clases: `shrink-0`, `truncate`, `max-w-full`

**Acciones:**
1. Línea 30: import a `TYPE_CHECKING`.
2. Línea 283: `ui.icon("…")` → `ThemeManager.icono("…")`.
3. Línea 453: `ui.icon("construction", size="lg", color="#d97706")` →
   `ThemeManager.icono("construction", size=32, color="var(--color-warning)")`.
4. Línea 500: idem patrón.
5. Clases: `shrink-0` → `no-shrink`, `truncate` → `text-truncate`,
   `max-w-full` se mantiene (ya añadida en T1).

---

## T9 — `evaluacion/planes_mejoramiento.py`

**Violaciones:**
- 3× `ui.icon()` (287, 337, 398)
- 1× color Quasar `grey` (línea 290)
- 1× clase `border-t`

**Acciones:**
1. `ui.icon` × 3 → `ThemeManager.icono`.
2. Línea 290: `ui.badge("Sin corte", color="grey").classes("text-xs")` →
   `ui.html('<span class="badge badge-neutral text-xs">Sin corte</span>')`.
3. `border-t` → `border-top-soft`.

---

## T10 — `evaluacion/planilla_notas.py`

**Violaciones:**
- 4× `ui.icon()` (395, 418, 666, 674)
- 3× `cellStyle` (483, 509, 518)
- 2× clases: `h-[600px]`, `w-px`

**Acciones:**
1. `ui.icon` × 4 → `ThemeManager.icono`.
2. `cellStyle` → `cellClass`:
   - `483`: `{"fontSize": "11px"}` → `"cellClass": "ag-cell-xs"`.
   - `509`: `{"color": "#0284C7"}` → `"cellClass": "ag-cell-info"`.
   - `518`: `{"color": "#DC2626"}` → `"cellClass": "ag-cell-error"`.
3. Clases: `h-[600px]` → `h-grid-default`, `w-px` se mantiene (T1 la define).

---

## T11 — `informes/estadisticos.py`

**Violaciones:**
- Import prohibido (línea 34)
- Clase `h-full`

**Acciones:**
1. Mover import a `TYPE_CHECKING`.
2. `h-full` se mantiene (T1 la define).

---

## T12 — Verificación final

```
python init.py
```

Debe retornar exit 0 y mostrar:

```
✅ ENTORNO OK
✅ DESIGN SYSTEM OK
715 passed
```

Además, smoke-test manual (lanzar `python main.py` y navegar):
- Página estudiantes con badge PIAR ✓
- Planilla de notas con columnas coloreadas ✓
- Configuración SIE con iconos ✓
- Habilitaciones con icono construction ámbar ✓

Si todo OK, el implementer escribe `progress/impl_11z.md` con resumen y referencias.
El reviewer ejecuta su pase y declara done.
