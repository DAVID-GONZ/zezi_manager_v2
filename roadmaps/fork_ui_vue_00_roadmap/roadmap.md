# fork_ui_vue — Roadmap: migración del frontend a Vue 3

> **Origen:** cierre del trabajo de design system portable (2026-08-09). Ver
> memoria `design-system-core-adapter-tokens` y `styles/PORTABILITY.md`.
> **Tipo:** roadmap (agrupa una familia de pasos; cada fase se convierte en spec propia
> cuando se active).
> **Meta estratégica:** Etapa B del plan — un código, tres productos (Vue web + Tauri
> escritorio + Capacitor Android). Ver `decision-stack-frontend`, `estrategia-backend-vue-fork`.
>
> **Revisión 2026-09-27:** la estrategia evolucionó de "fork" a **split en 3 repos**
> (`avedra-backend`, `avedra-frontend`, `avedra-shared-contracts`). El trabajo de este
> roadmap ocurre en `avedra-frontend`. NiceGUI pasa a `avedra-legacy-nicegui` como
> referencia de migración (cada página se lee antes de reescribirla en Vue).
> Agentes Claude, skills de diseño, anti AI-slop y librerías aprobadas documentados
> en `repo_split_00_pasos.md` §5.2–5.4.

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

## Evaluación de skills externos: ui-ux-pro-max-skill

> Revisión 2026-09-28. Fuente: `github.com/nextlevelbuilder/ui-ux-pro-max-skill`
> (7 skills: ui-ux-pro-max, design-system, design, ui-styling, brand, banner-design, slides).

### Resumen del repositorio

Kit de 7 skills de Claude Code orientado a diseño genérico y branding:

| Skill | Contenido | Stack |
| --- | --- | --- |
| **ui-ux-pro-max** | DB buscable: 79 estilos, 192 paletas, 74 pairings tipográficos, 119 guías UX, 105 iconos, 17 presets GSAP, 25 tipos de chart, 22 stacks. Script Python de búsqueda BM25. | Python |
| **design-system** | Arquitectura de tokens 3 capas (primitives→semantic→component), templates de slides, validación de tokens. | Python |
| **ui-styling** | shadcn/ui + Tailwind + Radix UI. Catálogo de componentes, theming, accesibilidad, responsive. References detallados. | React/Next.js |
| **brand** | Identidad de marca, voz, messaging, asset management. Scripts Node.js para sync brand→tokens. | Node.js |
| **design** | Hub unificado: rutas a sub-skills. Logo con Gemini AI, CIP (identidad corporativa), banners, iconos SVG, social photos. | Python + Gemini API |
| **banner-design** | Banners multi-formato: redes sociales, ads, web, print. 22 estilos artísticos. | CSS/HTML |
| **slides** | Presentaciones HTML con Chart.js, copywriting, estrategias de slides. | HTML/JS |

### Lo que SÍ aporta a AVEDRA

1. **ui-ux-pro-max — guías UX y prioridades de accesibilidad.** Su framework de
   prioridades (accesibilidad > touch/interacción > performance > estilo > layout)
   complementa nuestro `/design-check`. Las 119 guías UX y los patrones de
   interacción táctil (targets ≥ 44px, spacing, feedback states) son universales
   y aplicables sin adaptación.

2. **ui-styling — references de accesibilidad y responsive.** Los documentos
   `shadcn-accessibility.md` (ARIA, keyboard nav, focus management, screen reader)
   y `tailwind-responsive.md` (mobile-first, breakpoints, container queries)
   enriquecen nuestro `design-system-rules.md`. shadcn-vue es wrapper de Radix Vue,
   que es una de nuestras librerías aprobadas.

3. **design-system — naming de tokens 3 capas.** Nuestra arquitectura ya tiene
   `tokens.css` como fuente única, pero no distingue formalmente entre primitivos
   (raw values), semánticos (purpose) y de componente (component-specific). Adoptar
   esta taxonomía mejoraría la escalabilidad del sistema de tokens cuando el frontend
   Vue crezca.

### Lo que NO aporta (descartar)

| Skill | Razón de descarte |
| --- | --- |
| **brand** | AVEDRA ya tiene "Aula Serena" definido. No hay necesidad de branding generativo. Los scripts Node.js no encajan con nuestro toolchain Python. |
| **banner-design** | AVEDRA es una herramienta de gestión educativa, no un producto de marketing. Sin caso de uso. |
| **slides** | Irrelevante para el producto. |
| **design** (logo/CIP/social) | Generación de logos e identidad corporativa con Gemini AI no aplica. El logo y la identidad ya están decididos. |
| **ui-styling** (código) | Todos los ejemplos son React/JSX. Copiarlos a un proyecto Vue causaría confusión. Los conceptos transfieren; el código no. |

### Riesgos de incorporación directa

1. **Conflicto de design system.** Su enfoque es "shadcn/ui defaults + Tailwind
   utilities". El nuestro es "tokens Aula Serena primero, headless components
   estilados con CSS portable". Importar su approach de styling socavaría la
   estrategia de portabilidad CSS que costó el trabajo de `design-system-core-adapter`.

2. **Framework mismatch.** React ≠ Vue. JSX ≠ SFC. `useForm` ≠ `vee-validate`.
   Los references necesitan reescritura, no copia.

3. **AI-slop amplificado.** Irónicamente, importar un skill genérico masivo
   aumentaría los patrones que el anti AI-slop intenta prevenir: padding
   genérico, colores por defecto, layouts monótonos, componentes sin estados.

4. **Dependencias externas.** Gemini API, MuAPI, Node.js scripts. Nuestro
   toolchain es Python puro.

### Decisión: cherry-pick adaptado, no incorporación wholesale

**Sí adoptar (adaptados a Vue + Aula Serena):**

| Qué | De dónde | Cómo integrarlo | Fase |
| --- | --- | --- | --- |
| Framework de prioridades UX (accesibilidad > touch > perf > estilo > layout) | ui-ux-pro-max | Incorporar como sección en `/design-check` | Fase 2 (vue_04) |
| Guías de interacción táctil (targets, spacing, feedback) | ui-ux-pro-max | Agregar a `design-system-rules.md` como sección "Touch & Mobile" | Fase 4 (vue_10) |
| Patrones ARIA para componentes headless | ui-styling/shadcn-accessibility.md | Adaptar a Radix Vue en `/a11y-check` | Fase 2 (vue_04) |
| Breakpoints y responsive patterns | ui-styling/tailwind-responsive.md | Adaptar a nuestros tokens de breakpoint en `design-system-rules.md` | Fase 4 (vue_10) |
| Taxonomía tokens 3 capas | design-system | Evaluar refactor de `tokens.css` en primitives/semantic/component | Fase 1 (vue_02) |

**No adoptar:** todo lo demás (brand, banner, slides, logo, CIP, social photos,
scripts Node.js, ejemplos React).

---

## Qué NO cambia en el fork (activos que transfieren)

| Activo | Estado |
| --- | --- |
| `styles/tokens.css` + dark mode + a11y hooks | Copiar tal cual |
| CSS core semántico (badges, cards, alerts, stat-cards, page-header, layout) | Copiar + reproducir clases del contrato |
| `tokens.ts` / `tokens.json` | Generados desde Python; consumir |
| Contrato de clases (`CLASS_CONTRACT.md`) | Es la API que los componentes Vue reproducen |
| Reglas de negocio, dominio, servicios | Detrás de la API; no se tocan |

## Qué se reescribe

| Elemento | Motivo |
| --- | --- |
| Capa `styles/adapter/*` + secciones in-situ | Estilaban el DOM de Quasar/ag-Grid, inexistente en Vue |
| Inputs/formularios (`.andes-input .q-field__*`) | Reescritura contra `<input>` nativo / headless |
| `ThemeManager.icono()`, `render_logo()` | Componentes `<Icon>`/`<Logo>` de Vue |
| Render de páginas (Python/NiceGUI) | Componentes Vue consumiendo la API |
