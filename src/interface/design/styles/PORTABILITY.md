# Portabilidad del sistema de estilos — Core vs. Adapter

> Objetivo: cuando se haga el fork del frontend a **Vue 3 + Vite** (Etapa B), esta
> guía dice exactamente **qué se copia tal cual (core)** y **qué se reescribe (adapter)**.
> El límite lo **verifica automáticamente** `scripts/check_design.py` (regla N).

## Regla de oro

- **CORE = todo `styles/**` MENOS `styles/adapter/` y las secciones marcadas abajo.**
  Es CSS sobre nombres de clase **propios** + tokens `var(--…)`. Framework-agnóstico.
  Transfiere a Vue con copy-paste; solo hay que reproducir los **nombres de clase**
  en los componentes Vue (ver `CLASS_CONTRACT.md`).
- **ADAPTER = todo lo que estila el DOM que genera NiceGUI/Quasar/ag-Grid** (`.q-*`,
  `.ag-*`, `.nicegui-content`). En Vue nativo ese DOM no existe → se reescribe.

## Tiers por archivo

| Archivo | Tier | Nota |
|---|---|---|
| `tokens.css` | **CORE** ⭐ | Fuente única. 100% portable. También emite `tokens.ts` (ver `scripts/sync_tokens.py --emit-ts`). |
| `reset.css`, `typography.css` | CORE | Genérico. |
| `layout/*.css` (sidebar, topbar*, content, spacing) | CORE | *topbar.css tiene 1 sección adapter (ver abajo). |
| `components/*.css` (badges, buttons, cards*, dialogs, forms*, tables*, empty_state, skeleton, toast, flujo, impersonation, inline_selectors, badges, theme-toggle, date_input, password_change) | CORE | *cards/forms/tables tienen secciones adapter (ver abajo). |
| `domain/*.css` (asistencia, desempeno*, disponibilidad, horario_*) | CORE | *desempeno tiene celdas ag-Grid (ver abajo). |
| `themes/dark.css` | CORE | Overrides dark de clases propias. |
| `pages/*.css` | CORE | |
| **`adapter/quasar.css`** | **ADAPTER** | `.nicegui-content` + home de futuro glue Quasar. |
| **`adapter/aggrid.css`** | **ADAPTER** | Overrides dark de ag-Grid. |

## Secciones ADAPTER in-situ (interleaved con core — se reescriben en el fork)

No se movieron a `adapter/` porque están intercaladas con reglas portables y
moverlas arriesgaba la cascada. El lint las conoce (baseline) y **bloquea acoplamiento
NUEVO fuera de estos archivos**:

| Archivo | Selectores acoplados | Qué es |
|---|---|---|
| `components/forms.css` | `.andes-input .q-field__*`, `.andes-input.q-field--*`, `.andes-input.q-select …` | **El grueso.** Todo el estilado de inputs pega al DOM de Quasar. En Vue = reescritura completa contra `<input>` nativo. El wrapper `.andes-input` (contrato) se conserva; sus internals no. |
| `components/cards.css` | `.andes-login-card .andes-input .q-field__*`, `.andes-login-loading .andes-input .q-field__control` | Inputs del login (dark + loading). |
| `components/tables.css` | `.ag-theme-balham …`, `.panel-toolbar .andes-input .q-field__control` | Tema base ag-Grid + toolbar. Si el fork conserva ag-Grid (tiene binding Vue) transfiere; si no, se reescribe. |
| `domain/desempeno.css` | `.ag-theme-alpine/quartz .tablero-row-riesgo .ag-cell`, `.ag-cell.tablero-promedio-*` | Coloreado de celdas del tablero en ag-Grid. |
| `layout/topbar.css` | `.andes-topbar .q-btn[flat]` | Botones icon-only Quasar del topbar. |

## Lógica de presentación a re-portar (Python → TS)

- `tokens.py` → espejo en Python; se re-emite como `tokens.ts` desde `tokens.css`.
- `tokens.py` helpers (`AsistenciaColors.css_badge`, `DesempenoColors.para_nivel`, …)
  devuelven **nombres de clase** → se reimplementan en TS devolviendo las mismas clases.
- `Icons` (registro de Material Symbols) → `const` TS. La fuente web transfiere.
- `ThemeManager.icono()` / `render_logo()` → componentes `<Icon>` / `<Logo>` de Vue.

## Cómo mantener esto sano

`python scripts/check_design.py --all` (regla **N**) falla si aparece un selector
`.q-*`/`.ag-*`/`.nicegui-*` fuera de `adapter/` o de los archivos de la tabla in-situ.
Objetivo a largo plazo: vaciar la columna "in-situ" migrando esas secciones a `adapter/`.
