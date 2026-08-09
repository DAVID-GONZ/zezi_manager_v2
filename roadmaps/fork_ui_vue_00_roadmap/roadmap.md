# fork_ui_vue — Roadmap: migración del frontend a Vue 3

> **Origen:** cierre del trabajo de design system portable (2026-08-09). Ver
> memoria `design-system-core-adapter-tokens` y `styles/PORTABILITY.md`.
> **Tipo:** roadmap (agrupa una familia de pasos; cada fase se convierte en spec propia
> cuando se active).
> **Meta estratégica:** Etapa B del plan — un código, tres productos (Vue web + Tauri
> escritorio + Capacitor Android). Ver `decision-stack-frontend`, `estrategia-backend-vue-fork`.

## Contexto

El design system ya se preparó para que este fork sea un **trasplante, no una
reescritura**: tokens en fuente única (`styles/tokens.css`), frontera Core/Adapter
(`styles/PORTABILITY.md`), contrato de clases (`styles/CLASS_CONTRACT.md`) y puente
de tokens a TS (`scripts/sync_tokens.py --emit-ts` → `tokens.ts`/`tokens.json`).

Lo que transfiere ≈ tal cual: **tokens + CSS core + dark mode + a11y**.
Lo que se reescribe: **capa adapter** (inputs Quasar, temas ag-Grid) y la **lógica
de render** (Python → componentes Vue).

## Prerrequisitos (no arrancar antes)

1. **Backend API** operativo (`backend_00_roadmap_sqlalchemy_api`): el frontend Vue
   consume HTTP/JSON, no llama a `Container` en proceso.
2. **App NiceGUI funcional y estable** (step_list en `done`) como referencia de paridad.
3. **`tokens.ts` emitido y sin drift** (`python scripts/sync_tokens.py --check`).
4. **Suite E2E** de `testing_ui_roadmap` verde: es la red de paridad funcional durante el fork.

---

## Fase 0 — Andamiaje del proyecto Vue (2–3 días)

- **vue_00_scaffold** — Proyecto Vite + Vue 3 + TypeScript en `frontend/` (repo o monorepo).
  Router (`vue-router`), estado (Pinia), cliente HTTP (fetch/axios) contra la API.
  - *criterio_done*: `npm run dev` levanta un shell vacío que autentica contra la API.
- **vue_01_ci_build** — Pipeline Vite: TS estricto, ESLint, `vite build` con
  autoprefixer + minify. Base de CI.
  - *criterio_done*: `npm run build` produce bundle hasheado; lint en verde.

## Fase 1 — Capa de tokens y tema (2 días)

- **vue_02_tokens** — Copiar `styles/tokens.css` como capa global. Importar
  `tokens.ts`/`tokens.json` (generados desde Python) para valores en JS/TS
  (charts, estilos calculados). **No** re-teclear valores: consumir el artefacto.
  - *criterio_done*: `getComputedStyle` de `--color-primary` == `Colors.PRIMARY` de `tokens.ts`.
- **vue_03_dark_mode** — Reproducir el theming de 3 estados (`data-theme` + toggle +
  `prefers-color-scheme`) y `prefers-contrast`/`prefers-reduced-motion`.
  - *criterio_done*: paridad de dark mode con la app NiceGUI en 3 pantallas de muestra.

## Fase 2 — Librería de componentes base (1–2 semanas)

- **vue_04_headless_base** — Adoptar una base **headless accesible** (Radix Vue o
  shadcn-vue) estilada con los tokens: Button, Input/Select, Dialog, Menu, Table,
  Toast, Badge. Esto aporta foco/ARIA/teclado que el CSS solo no da (cierra la brecha
  de a11y). Reescribe la capa **adapter** (inputs, tablas) sobre DOM nativo/propio.
  - *criterio_done*: cada componente reproduce las clases del `CLASS_CONTRACT.md` y pasa axe.
- **vue_05_scoped_styles** — Estilos **con scope** (SFC `<style scoped>` o CSS Modules)
  por componente → elimina la cascada global y los ~135 `!important` heredados de Quasar.
  El CSS core semántico se importa; el glue adapter desaparece.
  - *criterio_done*: 0 `!important` fuera de resets justificados; sin fugas de estilo entre componentes.
- **vue_06_storybook** — Storybook como catálogo vivo, con **matriz de estados** por
  componente (default/hover/focus/active/disabled/loading/error/empty).
  - *criterio_done*: cada componente del contrato tiene story con todos sus estados.

## Fase 3 — Migración del CSS core y páginas (varias semanas)

- **vue_07_core_css** — Copiar `styles/core` (todo `styles/**` menos `adapter/` y las
  secciones in-situ del `PORTABILITY.md`) a los componentes que aplican esas clases.
  Reproducir los nombres de clase del contrato → el CSS transfiere sin tocar.
  - *criterio_done*: paridad visual de badges/cards/alerts/stat-cards/page-header.
- **vue_08_paginas_rol** — Migrar páginas por rol (profesor primero: asistencia, notas,
  convivencia; luego coordinador/directivo/admin), consumiendo la API. Paridad funcional
  con NiceGUI, validada contra los flujos E2E de `testing_ui_roadmap`.
  - *criterio_done*: los flujos críticos E2E pasan contra el frontend Vue.

## Fase 4 — Rendimiento y responsive (1–2 semanas)

- **vue_09_perf_build** — PurgeCSS/tree-shaking, critical CSS, code-splitting por ruta,
  **fuentes auto-hospedadas** (woff2 subseteado, `font-display: swap`, `preconnect`) —
  quita los 3 `@import` render-blocking a Google Fonts.
  - *criterio_done*: Lighthouse Performance ≥ 90 en las 3 páginas principales.
- **vue_10_responsive** — Mobile-first real: tokens de breakpoint, sidebar → drawer,
  tipografía/espaciado fluidos con `clamp()`, targets táctiles ≥ 44px.
  - *criterio_done*: pantallas 360/768/1280 sin scroll horizontal ni solapes; navegable táctil.

## Fase 5 — Empaquetado multiplataforma (1 semana)

- **vue_11_pwa** — PWA (manifest + service worker) para la web.
- **vue_12_tauri** — Empaquetado escritorio con Tauri v2 (~3 MB).
- **vue_13_capacitor** — Empaquetado Android con Capacitor.
  - *criterio_done*: los tres artefactos arrancan y autentican contra la API.

## Fase 6 — Cutover

- **vue_14_paridad_final** — Checklist de paridad funcional/visual/a11y NiceGUI ↔ Vue.
  Regresión visual (ver `testing_ui_roadmap`) verde. Congelar la UI NiceGUI como legacy.

---

## Qué NO cambia en el fork (activos que transfieren)

| Activo | Estado |
|---|---|
| `styles/tokens.css` + dark mode + a11y hooks | Copiar tal cual |
| CSS core semántico (badges, cards, alerts, stat-cards, page-header, layout) | Copiar + reproducir clases del contrato |
| `tokens.ts` / `tokens.json` | Generados desde Python; consumir |
| Contrato de clases (`CLASS_CONTRACT.md`) | Es la API que los componentes Vue reproducen |
| Reglas de negocio, dominio, servicios | Detrás de la API; no se tocan |

## Qué se reescribe

| Elemento | Motivo |
|---|---|
| Capa `styles/adapter/*` + secciones in-situ | Estilaban el DOM de Quasar/ag-Grid, inexistente en Vue |
| Inputs/formularios (`.andes-input .q-field__*`) | Reescritura contra `<input>` nativo / headless |
| `ThemeManager.icono()`, `render_logo()` | Componentes `<Icon>`/`<Logo>` de Vue |
| Render de páginas (Python/NiceGUI) | Componentes Vue consumiendo la API |
