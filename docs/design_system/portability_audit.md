# Auditoría de portabilidad CSS — Design System Aula Serena

> Generado: 2026-09-28 | Herramienta: `scripts/audit_css_portability.py`

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| LOC total | 5 637 |
| LOC core (portable a Vue) | 5 353 |
| LOC adapter (a reescribir) | 284 |
| **Ratio de portabilidad** | **95%** |
| Reglas `!important` | 170 |
| Selectores de framework únicos | 54 |
| Archivos mixtos (CORE + secciones adapter) | 8 |

**Conclusión:** El 95% del CSS transfiere a Vue sin cambios. El 5% restante (284 LOC adapter) se concentra en cinco archivos con acoplamiento a Quasar (`forms.css`, `topbar.css`, `cards.css`) y a ag-Grid (`desempeno.css`, `tables.css`). El adapter puro (`adapter/`) suma solo 117 LOC. Las secciones adapter en archivos MIXED son el trabajo real del fork.

---

## Distribución por categoría

### Archivos ADAPTER puros

| Archivo | LOC | Selectores de framework |
|---|---|---|
| `adapter/aggrid.css` | 102 | `.ag-theme-balham`, `.ag-root-wrapper`, `.ag-header`, `.ag-header-cell`, `.ag-row`, `.ag-row-odd`, `.ag-row-focus`, `.ag-row-selected`, `.ag-cell`, `.ag-cell.cell-multiline`, `.ag-body-viewport`, `.ag-header-cell-label`, `.nicegui-aggrid` |
| `adapter/quasar.css` | 15 | `.nicegui-content`, `.q-btn` |

### Archivos CORE puros (portables a Vue)

| Archivo | LOC | Tokens consumidos (muestra) |
|---|---|---|
| `tokens.css` | 276 | fuente canónica — 187 vars |
| `components/badges.css` | 189 | `--color-*`, `--attend-*`, `--desempeno-*` |
| `components/buttons.css` | 125 | `--color-primary`, `--btn-height-*`, `--radius-md` |
| `components/cards.css` — **MIXED** | 1 199 | ver sección MIXED |
| `components/counter-card.css` | 71 | `--color-*`, `--shadow-card` |
| `components/date_input.css` | 61 | `--color-primary`, `--radius-full` |
| `components/dialogs.css` | 132 | `--color-*`, `--shadow-modal` |
| `components/empty_state.css` | 40 | `--color-*`, `--space-*` |
| `components/flujo.css` | 84 | `--color-*`, `--radius-pill` |
| `components/impersonation.css` | 41 | `--color-warning*`, `--z-index-topbar` |
| `components/inline_selectors.css` | 50 | `--color-primary*`, `--radius-full` |
| `components/password_change.css` | 111 | `--color-*`, `--transition-base` |
| `components/skeleton_loader.css` | 69 | `--color-border`, `--radius-*` |
| `components/theme-toggle.css` | 51 | `--color-border`, `--transition-fast` |
| `components/toast.css` | 18 | `--color-*`, `--shadow-lg` |
| `domain/asistencia.css` | 385 | `--attend-*`, `--color-*`, `--font-size-*` |
| `domain/convivencia.css` | 50 | `--font-size-body`, `--space-*` |
| `domain/disponibilidad.css` | 40 | `--color-success*`, `--color-error*` |
| `domain/horario_generar.css` | 109 | `--color-*`, `--font-mono` |
| `domain/horario_parrilla.css` | 400 | `--parrilla-acento`, `--color-*` |
| `layout/content.css` | 96 | `--content-padding`, `--topbar-height` |
| `layout/sidebar.css` | 169 | `--rail-width`, `--nav-sidebar-*` |
| `layout/spacing.css` | 20 | `--space-*` |
| `pages/buscar.css` | 91 | `--color-*`, `--font-weight-*` |
| `pages/wizard_configuracion.css` | 54 | `--radius-xl`, `--shadow-modal` |
| `themes/dark.css` | 25 | `--color-primary`, `--nav-rail-marker` |
| `typography.css` | 71 | `--font-family`, `--font-size-*` |

### Archivos MIXED (CORE con secciones adapter in-situ)

Estos son los archivos que requieren trabajo real en el fork Vue. La columna "LOC adapter" es una estimación; el núcleo semántico (clases `.andes-*`, `.panel-*`, etc.) transfiere intacto.

| Archivo | LOC total | LOC adapter est. | Selectores de framework |
|---|---|---|---|
| `components/forms.css` | 298 | **100** | `.q-field__*` (11 sels), `.q-item*`, `.q-menu`, `.q-select__dropdown-icon`, `.q-separator` |
| `layout/topbar.css` | 243 | **27** | `.q-btn`, `.q-field__control`, `.q-field__native`, `.q-field__prepend` |
| `domain/desempeno.css` | 277 | **22** | `.ag-theme-alpine`, `.ag-theme-quartz`, `.ag-cell`, `.ag-cell.tablero-promedio-*` (4) |
| `components/cards.css` | 1 199 | **12** | `.q-field__control`, `.q-field__native` |
| `components/tables.css` | 315 | **6** | `.ag-theme-balham`, `.ag-cell-*` (3), `.q-field__control` |
| `reset.css` | 105 | 0\* | `.nicegui-content` |
| `components/historial.css` | 92 | 0\* | referencia en comentario |
| `components/marketing.css` | 163 | 0\* | referencia en comentario |

\* Detectados como MIXED por el analizador léxico, pero los selectores aparecen solo en comentarios; el archivo es funcionalmente CORE. La estimación de adapter_loc es 0.

---

## Análisis de `!important`

| Archivo | Usos de `!important` | Contexto |
|---|---|---|
| `components/forms.css` | **71** | Sobrescrituras de Quasar — todos en secciones adapter |
| `domain/asistencia.css` | 26 | Celdas de estado de asistencia |
| `components/tables.css` | 15 | Overrides de ag-Grid y altura de rows |
| `components/toast.css` | 11 | Posición fixed y z-index de toasts |
| `layout/topbar.css` | 11 | Overrides del buscador Quasar |
| `components/cards.css` | 9 | Inputs del login (Quasar) y estados disabled |
| `adapter/aggrid.css` | 9 | Overrides dark de ag-Grid |
| `typography.css` | 7 | Resets de tipografía globales |
| `components/dialogs.css` | 2 | Overflow y scroll |
| `reset.css` | 2 | Box-sizing global |
| Resto de archivos | 7 | Casos aislados |

**Observación:** 71 de los 170 `!important` (42%) están en `forms.css` y son consecuencia directa de combatir la especificidad de Quasar. En Vue con `<input>` nativo, esas reglas desaparecen completamente.

---

## Selectores de framework por archivo

| Archivo | Framework | Selectores únicos |
|---|---|---|
| `adapter/aggrid.css` | ag-Grid + NiceGUI | 13 selectores (ver tabla ADAPTER) |
| `components/forms.css` | Quasar | `.q-field__bottom`, `.q-field__control`, `.q-field__control-container`, `.q-field__input`, `.q-field__label`, `.q-field__messages`, `.q-field__native`, `.q-field__prefix`, `.q-field__suffix`, `.q-item`, `.q-item--active`, `.q-item--clickable`, `.q-menu`, `.q-select__dropdown-icon`, `.q-separator` |
| `domain/desempeno.css` | ag-Grid | `.ag-cell`, `.ag-cell.tablero-promedio-alto`, `.ag-cell.tablero-promedio-basico`, `.ag-cell.tablero-promedio-riesgo`, `.ag-cell.tablero-promedio-superior`, `.ag-theme-alpine`, `.ag-theme-quartz` |
| `layout/topbar.css` | Quasar | `.q-btn`, `.q-field__control`, `.q-field__native`, `.q-field__prepend` |
| `adapter/quasar.css` | NiceGUI + Quasar | `.nicegui-content`, `.q-btn` |
| `components/cards.css` | Quasar | `.q-field__control`, `.q-field__native` |
| `components/tables.css` | ag-Grid + Quasar | `.ag-cell-error`, `.ag-cell-info`, `.ag-cell-xs`, `.ag-theme-balham`, `.q-field__control` |
| `reset.css` | NiceGUI | `.nicegui-content` (en comentario) |

---

## Recomendaciones para el fork Vue

### 1. Inputs — `components/forms.css` (mayor bloque adapter: ~100 LOC, 71 `!important`)

El wrapper `.andes-input` y su API pública se conservan. Los internals que pegan al DOM de Quasar (`.q-field__*`, `.q-item`, `.q-menu`) se reescriben contra `<input>` / `<select>` nativos o la API del sistema de componentes Vue elegido (PrimeVue, Radix, Headless UI). Resultado esperado: desaparecen los 71 `!important`.

### 2. Buscador del topbar — `layout/topbar.css` (~27 LOC adapter)

El buscador `.topbar-search` usa un `<q-input>` internamente. En Vue se reemplaza por un `<input type="search">` nativo dentro del mismo wrapper. Las 4 reglas de framework se eliminan.

### 3. Tablero de desempeño — `domain/desempeno.css` (~22 LOC adapter)

ag-Grid tiene binding Vue nativo (`ag-grid-vue3`). Si se conserva ag-Grid, solo hay que actualizar la clase del tema: `.ag-theme-balham` → `.ag-theme-quartz` (ya previsto: ambas aparecen en el CSS). Los 7 selectores transfieren con mínimos ajustes.

### 4. Inputs del login — `components/cards.css` (~12 LOC adapter)

Mismo patrón que `forms.css` pero menos volumen: 2 selectores `.q-field__control` y `.q-field__native` dentro del login card. Se reescriben junto con el punto 1.

### 5. Toolbar de tablas — `components/tables.css` (~6 LOC adapter)

Solo `.q-field__control` dentro de `.panel-toolbar .andes-input`. Queda eliminado al resolver el punto 1.

### 6. `.nicegui-content` en `reset.css` y `adapter/quasar.css`

En NiceGUI, `.nicegui-content` es el contenedor raíz de la aplicación. En Vue, el equivalente es el `<div id="app">` o el contenedor del router-view. Reemplazar con el selector apropiado en el reset Vue (1 cambio en 1 línea).

---

## Cómo verificar la portabilidad

```bash
# Ejecutar la auditoría y ver el resumen
python scripts/audit_css_portability.py | python -c "
import sys, json
d = json.load(sys.stdin)
r = d['resumen']
print(f'Archivos: {r[\"total_archivos\"]} | LOC: {r[\"total_loc\"]} | Core: {r[\"core_loc\"]} | Adapter: {r[\"adapter_loc\"]} | Ratio: {r[\"ratio_portabilidad\"]:.0%}')
"

# Guardar el JSON completo
python scripts/audit_css_portability.py --output docs/design_system/audit_result.json

# Verificar portabilidad actual (check_design regla N)
python scripts/check_design.py --all

# Ver tokens sincronizados
python scripts/sync_tokens.py --check
```

### Test visual sin framework

Abre `docs/design_system/portability_test.html` en cualquier navegador. Los 18 componentes del contrato se renderizan **sin NiceGUI ni Quasar**. Si se ven legibles y coherentes, el CSS core está desacoplado. Si algo aparece completamente sin estilo, busca el selector de framework responsable con:

```bash
python -m ruff check . --select F821,F811 --output-format concise
```

---

## Apéndice — LOC por archivo (completo)

| Archivo | Tier | LOC | Core | Adapter | Important |
|---|---|---|---|---|---|
| `tokens.css` | CORE | 276 | 276 | 0 | 0 |
| `reset.css` | MIXED | 105 | 105 | 0 | 2 |
| `typography.css` | CORE | 71 | 71 | 0 | 7 |
| `layout/sidebar.css` | CORE | 169 | 169 | 0 | 0 |
| `layout/topbar.css` | MIXED | 243 | 216 | 27 | 11 |
| `layout/content.css` | CORE | 96 | 96 | 0 | 0 |
| `layout/spacing.css` | CORE | 20 | 20 | 0 | 0 |
| `components/badges.css` | CORE | 189 | 189 | 0 | 0 |
| `components/buttons.css` | CORE | 125 | 125 | 0 | 0 |
| `components/cards.css` | MIXED | 1 199 | 1 187 | 12 | 9 |
| `components/counter-card.css` | CORE | 71 | 71 | 0 | 0 |
| `components/date_input.css` | CORE | 61 | 61 | 0 | 0 |
| `components/dialogs.css` | CORE | 132 | 132 | 0 | 2 |
| `components/empty_state.css` | CORE | 40 | 40 | 0 | 0 |
| `components/flujo.css` | CORE | 84 | 84 | 0 | 0 |
| `components/forms.css` | MIXED | 298 | 198 | 100 | 71 |
| `components/historial.css` | MIXED* | 92 | 92 | 0 | 0 |
| `components/impersonation.css` | CORE | 41 | 41 | 0 | 0 |
| `components/inline_selectors.css` | CORE | 50 | 50 | 0 | 0 |
| `components/marketing.css` | MIXED* | 163 | 163 | 0 | 0 |
| `components/password_change.css` | CORE | 111 | 111 | 0 | 0 |
| `components/skeleton_loader.css` | CORE | 69 | 69 | 0 | 0 |
| `components/tables.css` | MIXED | 315 | 309 | 6 | 15 |
| `components/theme-toggle.css` | CORE | 51 | 51 | 0 | 0 |
| `components/toast.css` | CORE | 18 | 18 | 0 | 11 |
| `domain/asistencia.css` | CORE | 385 | 385 | 0 | 26 |
| `domain/convivencia.css` | CORE | 50 | 50 | 0 | 0 |
| `domain/desempeno.css` | MIXED | 277 | 255 | 22 | 0 |
| `domain/disponibilidad.css` | CORE | 40 | 40 | 0 | 0 |
| `domain/horario_generar.css` | CORE | 109 | 109 | 0 | 0 |
| `domain/horario_parrilla.css` | CORE | 400 | 400 | 0 | 1 |
| `pages/buscar.css` | CORE | 91 | 91 | 0 | 4 |
| `pages/wizard_configuracion.css` | CORE | 54 | 54 | 0 | 0 |
| `themes/dark.css` | CORE | 25 | 25 | 0 | 1 |
| `adapter/aggrid.css` | ADAPTER | 102 | 0 | 102 | 9 |
| `adapter/quasar.css` | ADAPTER | 15 | 0 | 15 | 1 |
| **Total** | | **5 637** | **5 353** | **284** | **170** |

\* MIXED por detección léxica de prefijos en comentarios; funcionalmente CORE (0 LOC adapter estimado).
