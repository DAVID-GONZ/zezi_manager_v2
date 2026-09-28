# repo_split_00 — Pasos de ejecucion del split de repositorios

> Generado: 2026-09-27
> Base: `repo_split_00_roadmap.md` + `generar_estructura.py` + agentes actuales

---

## Indice de fases

| Fase | Nombre | Pasos | Riesgo |
|------|--------|-------|--------|
| 0 | Preparacion y snapshot | 0.1 – 0.4 | Bajo |
| 1 | Creacion de repos vacios | 1.1 – 1.2 | Bajo |
| 2 | Split del backend | 2.1 – 2.7 | **Alto** |
| 3 | Shared contracts | 3.1 – 3.5 | Medio |
| 4 | Scaffold frontend Vue | 4.1 – 4.5 | Bajo |
| 5 | Agentes Claude por repo | 5.1 – 5.6 | Medio |
| — | — 5.2.1 Skills de diseño frontend | /design-check, /deslop-ui, /a11y | Medio |
| — | — 5.2.2 Referencias Vue | patrones, composables, design rules | Bajo |
| — | — 5.2.3 Design reviewer agent | aprueba visual + UX | Medio |
| — | — 5.3 Referencia legacy → Vue | migración asistida | Medio |
| — | — 5.4 Anti AI-slop | reviewer rules | Medio |
| 6 | CI/CD cruzado | 6.1 – 6.3 | Medio |
| 7 | Gestión del legado | 7.1 – 7.4 | Bajo |

---

## Fase 0 — Preparacion y snapshot

### 0.1 Verificar estado limpio

```bash
python init.py                     # todo verde
python -m pytest tests/ -x         # suite completa
git status                         # working tree limpio
```

**Criterio:** init.py verde, tests verdes, nada sin commitear.

### 0.2 Tag y rama de respaldo

```bash
git tag pre-split-v2.0
git branch backup/pre-split
git push origin pre-split-v2.0
git push origin backup/pre-split
```

### 0.3 Generar estructura de referencia

```bash
python scripts/generar_estructura.py
```

Guardar `docs/estructura_proyecto.md` y `docs/estructura_tests.md` como referencia
del estado pre-split. Commitear.

### 0.4 Inventario de archivos por destino

Crear un mapa explícito de qué va a cada repo:

| Origen actual | Destino repo | Notas |
|---|---|---|
| `src/domain/` | avedra-backend | Tal cual |
| `src/infrastructure/` | avedra-backend | Tal cual |
| `src/services/` | avedra-backend | Tal cual |
| `src/reference/` | avedra-backend | divipola, enums |
| `src/interface/` | **Descartado** | Legado NiceGUI; referencia en legacy |
| `config.py`, `container.py`, `main.py` | avedra-backend | Raíz de la app |
| `tests/` | avedra-backend | Todo; adaptar imports |
| `scripts/` | avedra-backend | init.py, check_design.py, etc. |
| `deploy/` | avedra-backend | caddy, nginx |
| `pyproject.toml` | avedra-backend | Limpiar deps de NiceGUI |
| `docs/` | avedra-backend | architecture.md, conventions.md |
| `data/` | avedra-backend | Seed data |
| `roadmaps/` | **No migrar** | Quedan en legacy como referencia |
| `specs/` | **No migrar** | Quedan en legacy como referencia |
| `progress/` | **No migrar** | Quedan en legacy como referencia |

---

## Fase 1 — Creacion de repos vacios en GitHub

### 1.1 Crear repos

```bash
gh repo create avedra-backend --private --description "AVEDRA: dominio, servicios, API REST"
gh repo create avedra-frontend --private --description "AVEDRA: Vue 3 + Vite, PWA/Tauri/Capacitor"
gh repo create avedra-shared-contracts --private --description "AVEDRA: OpenAPI, DTOs, enums, design tokens"
```

### 1.2 Configurar .gitignore base

- **avedra-backend:** Python (.venv, __pycache__, .pytest_cache, .ruff_cache, *.pyc, .env)
- **avedra-frontend:** Node (node_modules, dist, .env, *.local)
- **avedra-shared-contracts:** Mínimo (node_modules si usa tooling npm)

---

## Fase 2 — Split del backend (FASE CRITICA)

### 2.1 Clonar repo actual como base del backend

```bash
git clone --no-hardlinks . ../avedra-backend
cd ../avedra-backend
```

### 2.2 Filtrar historial (conservar solo backend)

```bash
pip install git-filter-repo

git filter-repo \
  --path src/domain/ \
  --path src/infrastructure/ \
  --path src/services/ \
  --path src/reference/ \
  --path src/__init__.py \
  --path tests/ \
  --path scripts/ \
  --path deploy/ \
  --path docs/ \
  --path data/ \
  --path config.py \
  --path container.py \
  --path main.py \
  --path pyproject.toml \
  --path requirements.txt \
  --path .gitignore \
  --path CLAUDE.md
```

**Nota:** `src/interface/` NO se incluye — es legado NiceGUI.

### 2.3 Crear stub de API REST

Crear la estructura mínima para FastAPI:

```
avedra-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory
│   ├── deps.py               # dependency injection (Container)
│   └── routes/
│       └── __init__.py
```

`app/main.py` arranca FastAPI, importa rutas, inyecta Container.
Las rutas se implementan según el backend roadmap (no en este split).

### 2.4 Limpiar pyproject.toml

Eliminar dependencias de NiceGUI y UI:
- `nicegui`, `quasar`, `ag-grid`, etc.

Agregar dependencias de API:
- `fastapi`, `uvicorn`, `pydantic` (ya debería estar)

### 2.5 Adaptar scripts/init.py

Eliminar chequeos de design system (tokens, check_design, audit_design) que
pertenecen a la capa de interfaz NiceGUI. Conservar:
- Verificación de imports
- Ruff (defectos de ejecución)
- Tests

### 2.6 Adaptar container.py

Eliminar registros de componentes de interfaz.
Mantener: repos, servicios, config.

### 2.7 Verificar arranque

```bash
python -c "from src.domain import models; print('domain OK')"
python -c "from src.services import usuario_service; print('services OK')"
python -m pytest tests/ -x
```

**Criterio:** imports limpios, tests verdes, sin referencias a `src/interface/`.

---

## Fase 3 — Shared contracts

### 3.1 Inicializar repo

```bash
cd ../avedra-shared-contracts
git init
```

### 3.2 Extraer OpenAPI

Dos opciones según el estado del backend API:

**Opcion A** (API ya implementada):
```bash
# Desde avedra-backend
python scripts/generate_openapi.py > ../avedra-shared-contracts/openapi/avedra-openapi.yaml
```

**Opcion B** (API aún no implementada — caso actual):
Crear un `openapi/avedra-openapi.yaml` manual con los endpoints planificados,
marcados como `x-status: planned`. Se reemplaza cuando la API esté lista.

### 3.3 Extraer enums y DTOs

```bash
# Desde avedra-backend, generar JSON schemas de los modelos Pydantic
python scripts/export_schemas.py --output ../avedra-shared-contracts/dto/
```

Si el script no existe aún, crearlo. Recorre `src/domain/models/` y exporta
cada modelo Pydantic como JSON Schema.

### 3.4 Copiar design tokens

```bash
# tokens.css → tokens.json (vía sync_tokens.py)
cp src/interface/design/styles/tokens.css ../avedra-shared-contracts/design-system/tokens.css
python scripts/sync_tokens.py --emit-json > ../avedra-shared-contracts/design-system/tokens.json
```

Copiar también:
- `styles/CLASS_CONTRACT.md` → `design-system/class-contract.md`
- `styles/PORTABILITY.md` → `design-system/portability.md`

### 3.5 Versionado inicial

```bash
cd ../avedra-shared-contracts
git add .
git commit -m "Initial shared contracts: OpenAPI stub, DTOs, enums, design tokens"
git remote add origin https://github.com/<usuario>/avedra-shared-contracts.git
git push -u origin main
```

---

## Fase 4 — Scaffold frontend Vue

### 4.1 Crear proyecto

```bash
npm create vite@latest ../avedra-frontend -- --template vue-ts
cd ../avedra-frontend
npm install
npm install vue-router@4 pinia @vueuse/core axios
```

### 4.2 Integrar tokens

```bash
# Copiar desde shared-contracts
cp ../avedra-shared-contracts/design-system/tokens.css src/styles/tokens.css
cp ../avedra-shared-contracts/design-system/tokens.json src/types/tokens.json
```

### 4.3 Configurar cliente API

```bash
npm install openapi-typescript-codegen --save-dev
# o usar openapi-ts (más moderno)
npx openapi-typescript ../avedra-shared-contracts/openapi/avedra-openapi.yaml -o src/api/generated.ts
```

### 4.4 Estructura base

```
avedra-frontend/src/
├── api/
│   ├── client.ts          # axios instance + interceptors
│   └── generated.ts       # auto-generado desde OpenAPI
├── components/
│   └── ui/                # design system Vue
├── composables/
├── router/
│   └── index.ts
├── stores/
│   ├── auth.ts
│   └── tenant.ts
├── styles/
│   ├── tokens.css
│   └── theme.css
├── types/
├── views/
└── main.ts
```

### 4.5 Verificar arranque

```bash
npm run dev        # debe levantar en localhost
npm run build      # debe producir bundle sin errores
npm run typecheck  # tsc sin errores
```

---

## Fase 5 — Agentes Claude por repo

### 5.1 Agentes para avedra-backend

```
avedra-backend/.claude/
├── agents/
│   ├── leader.md
│   ├── implementer.md
│   ├── reviewer.md
│   └── spec_author.md
├── settings.json
└── CLAUDE.md (raíz del repo)
```

**Cambios clave en los agentes del backend vs. los actuales:**

| Aspecto | Actual (mono-repo) | Backend (post-split) |
|---|---|---|
| Scope del implementer | `src/` (todo) | `src/` (sin interface/) + `app/` (API) |
| Reglas de design system | Aplican (tokens, CSS) | **Eliminadas** (pertenecen al frontend) |
| init.py | check_design + ruff + tests | ruff + tests + contract validation |
| Reviewer chequea | CSS tokens, imports | API contracts, imports, tests |

**leader.md del backend** agrega:

```markdown
## Regla de contrato API

Cuando un paso modifique un endpoint, schema o enum:
1. Regenerar OpenAPI: `python scripts/generate_openapi.py`
2. Copiar a avedra-shared-contracts
3. Anotar en progress/current.md: "CONTRACT_CHANGED: <qué cambió>"
   para que David sepa que debe actualizar el frontend.
```

### 5.2 Agentes y skills para avedra-frontend

```
avedra-frontend/.claude/
├── agents/
│   ├── leader.md
│   ├── implementer.md
│   ├── reviewer.md
│   ├── spec_author.md
│   └── design_reviewer.md      ← NUEVO: agente especializado en diseño
├── commands/
│   ├── design-check.md          ← skill: auditoría visual de componente
│   ├── deslop-ui.md             ← skill: limpiar patrones AI en UI
│   ├── component-audit.md       ← skill: validar contra design system
│   ├── a11y-check.md            ← skill: accesibilidad WCAG
│   └── migrate-page.md          ← skill: flujo completo legacy → Vue
├── references/
│   ├── vue-patterns.md          ← patrones y anti-patrones Vue
│   ├── composable-catalog.md    ← composables del proyecto + VueUse
│   └── design-system-rules.md   ← tokens, CLASS_CONTRACT, reglas visuales
└── CLAUDE.md
```

**Cambios clave:**

| Aspecto | Backend agents | Frontend agents |
|---|---|---|
| Lenguaje | Python | TypeScript / Vue SFC |
| Implementer escribe en | `src/`, `app/` | `src/` (Vue) |
| Reglas de design | No | Sí: tokens.css, CLASS_CONTRACT |
| Reviewer valida | API contracts, ruff | TypeScript strict, ESLint, axe a11y |
| Design reviewer | No existe | Sí: revisa jerarquía visual, spacing, color, responsive |
| init.py equivalente | `python init.py` | `npm run typecheck && npm run lint && npm run build` |

**leader.md del frontend** agrega:

```markdown
## Regla de contrato API

Antes de implementar un paso que consume un endpoint nuevo:
1. Verificar que el endpoint existe en avedra-shared-contracts/openapi/
2. Regenerar el cliente: `npm run generate:api`
3. Si el endpoint NO existe → PARAR. Reportar a David:
   "El backend necesita implementar <endpoint> primero."

## Skills de diseño disponibles

Después de implementar cualquier componente o vista, ejecutar:
1. `/design-check` — auditoría visual (jerarquía, spacing, color, tipografía)
2. `/deslop-ui` — limpiar patrones genéricos de AI
3. `/a11y-check` — accesibilidad WCAG 2.2 AA

Para migración de páginas: `/migrate-page <nombre>` ejecuta el flujo
completo (lee legacy → extrae referencia → genera scaffold Vue).
```

**implementer.md del frontend** agrega:

```markdown
## Reglas duras
- No usar fetch/axios directo. Siempre usar el cliente generado (`src/api/generated.ts`).
- No hardcodear URLs de API. Usar variables de entorno (`VITE_API_URL`).
- No duplicar tipos que ya existen en el contrato generado.
- Clases CSS solo del CLASS_CONTRACT. Tokens solo de tokens.css.
- Leer `.claude/references/vue-patterns.md` antes de crear un componente nuevo.
- Leer `.claude/references/composable-catalog.md` antes de crear un composable
  (puede que ya exista uno en VueUse o en el proyecto).
```

---

### 5.2.1 Skills de diseño (`.claude/commands/`)

Estas skills se invocan con `/nombre` en Claude Code. Son el equivalente
frontend de `check_design.py` y `audit_design.py` del backend NiceGUI.

#### `/design-check` — Auditoría visual de componente

```markdown
# Skill: design-check

Ejecuta una revisión de calidad visual sobre el componente o vista indicado.
Usa los built-in skills `design-review` y `interface-design` como base.

## Checklist (en este orden)

1. **Jerarquía visual** — ¿Hay un punto focal claro? ¿Los elementos se leen
   en orden de importancia? ¿O todo tiene el mismo peso (señal de AI-slop)?
2. **Spacing** — ¿Usa tokens de spacing (--space-*) consistentemente?
   ¿Hay spacing manual (px/rem hardcodeados)?
3. **Tipografía** — ¿Usa la escala tipográfica del design system?
   ¿Hay más de 3 tamaños de fuente en la misma vista?
4. **Color** — ¿Los colores vienen de tokens? ¿El contraste cumple WCAG AA (4.5:1)?
   ¿Funciona en dark mode?
5. **Layout** — ¿Responsive sin scroll horizontal? ¿Mobile-first?
   ¿Los breakpoints usan tokens?
6. **Estados** — ¿Tiene empty state, loading, error? ¿O solo el happy path?
7. **Densidad de información** — ¿La vista respira o está atiborrada?
   ¿Los datos más importantes se ven sin scroll?

## Output

Lista de hallazgos con severidad:
- 🔴 Bloquea: rompe accesibilidad, ilegible, no funciona en mobile
- 🟡 Corregir: deuda visual que degrada la experiencia
- 🟢 Sugerencia: mejora opcional
```

#### `/deslop-ui` — Limpiar patrones AI en UI

```markdown
# Skill: deslop-ui

Invoca el built-in skill `design-deslop` y agrega reglas específicas de Vue.

## Patrones AI-slop en UI que DEBEN eliminarse

1. **Jerarquía plana** — todo al mismo tamaño/peso/color. Sin focal point.
   Señal: la vista parece una lista de items idénticos sin que nada destaque.

2. **Paleta tímida** — solo grises y un azul. Sin personalidad. Los badges,
   alertas y estados usan variaciones del mismo tono apagado.

3. **Monotone layout** — todo centrado, todo en columna, sin variación de
   ancho. Parece un formulario de registro, no una app de gestión.

4. **Tokens genéricos** — nombres como `primary`, `secondary`, `accent`
   sin significado semántico. Deben mapear al vocabulario del dominio:
   `--color-asistencia`, `--color-convivencia`, `--color-alerta`.

5. **Tipografía por defecto** — sin escala definida, todo en 14-16px,
   sin variación de peso. Los headings no se distinguen del body.

6. **Border-radius uniforme** — todo con el mismo radio. Cards, badges,
   inputs, avatares, botones: todos `rounded-lg`. Sin jerarquía de forma.

7. **Iconos decorativos** — iconos que no comunican nada, puestos porque
   "se ve más profesional". Si quitarlos no pierde información, sobran.

8. **Sombras homogéneas** — toda card con `shadow-md`. Sin elevación
   semántica (lo interactivo eleva, lo estático no).

## Acción

Por cada instancia encontrada:
1. Identificar el archivo y línea
2. Proponer el reemplazo concreto usando tokens del design system
3. Si no existe token adecuado, proponer crearlo en tokens.css
```

#### `/component-audit` — Validar contra design system

```markdown
# Skill: component-audit

Valida que un componente Vue cumple el contrato del design system.

## Verificaciones

1. Clases CSS usadas están en CLASS_CONTRACT.md
2. Colores vienen de CSS custom properties (tokens), no hardcodeados
3. Spacing usa tokens --space-*, no valores arbitrarios
4. Tipografía usa la escala del sistema
5. El componente tiene prop `variant` si aplica (no estilos inline condicionales)
6. Dark mode funciona (no hay colores que solo sirven en light)
7. No hay `!important` (si existe, debe estar justificado con comentario)
8. Los breakpoints responsive usan los tokens de media query
9. Las transiciones/animaciones respetan `prefers-reduced-motion`
```

#### `/a11y-check` — Accesibilidad WCAG 2.2 AA

```markdown
# Skill: a11y-check

Revisión de accesibilidad sobre componente o vista.

## Verificaciones

1. **Estructura semántica** — ¿Usa HTML semántico (nav, main, article, section,
   aside, header, footer)? ¿O todo es div/span?
2. **Headings** — ¿Jerarquía h1→h2→h3 sin saltos? ¿Solo un h1 por página?
3. **Formularios** — ¿Cada input tiene label asociado (for/id o wrapper)?
   ¿Los errores se anuncian con aria-live?
4. **Contraste** — ¿Texto/fondo cumple 4.5:1 (AA)? ¿Elementos interactivos 3:1?
5. **Teclado** — ¿Todos los interactivos son focusables? ¿El orden de tab es lógico?
   ¿Hay indicador de foco visible?
6. **Imágenes** — ¿alt text significativo o aria-hidden si es decorativa?
7. **ARIA** — ¿Usa roles, states y properties correctamente? ¿No duplica
   semántica que el HTML ya da?
8. **Responsive** — ¿Funciona a 200% zoom sin pérdida de contenido?
9. **Motion** — ¿Animaciones respetan prefers-reduced-motion?
```

#### `/migrate-page` — Flujo completo legacy → Vue

```markdown
# Skill: migrate-page

Flujo automatizado para migrar una página de NiceGUI a Vue.
Argumento: nombre de la página (ej: `/migrate-page observaciones`)

## Pasos (ejecutar en orden)

1. Localizar la página legacy:
   ../avedra-legacy-nicegui/src/interface/pages/**/<nombre>.py
   y su presenter (si existe):
   ../avedra-legacy-nicegui/src/interface/presenters/**/<nombre>_presenter.py

2. Leer ambos archivos y extraer:
   - Secciones y layout (tabs, cards, grids)
   - Campos de formulario con tipos y validaciones
   - Permisos por rol
   - Llamadas a servicios (método, params)
   - Flujos CRUD
   - Filtros y búsqueda
   - Tablas: columnas, ordenamiento, paginación

3. Escribir referencia en docs/migration-refs/<nombre>.md

4. Verificar que los endpoints necesarios existen en el contrato API.
   Si faltan → listar los faltantes y PARAR.

5. Generar scaffold Vue:
   - src/views/<modulo>/<Nombre>View.vue (vista principal)
   - src/composables/use<Nombre>.ts (lógica reactiva)
   - src/components/<modulo>/ (componentes específicos si aplica)

6. Ejecutar `/design-check` sobre el scaffold generado
7. Ejecutar `/a11y-check` sobre el scaffold generado
```

---

### 5.2.2 Referencias del proyecto (`.claude/references/`)

Archivos de referencia que los agentes leen antes de implementar.
No son skills invocables — son documentación que el implementer y reviewer
consultan como contexto.

#### `vue-patterns.md` — Patrones y anti-patrones Vue

```markdown
# Patrones Vue para AVEDRA Frontend

## Estructura de un SFC (orden canónico)

<script setup lang="ts"> primero, <template> después, <style scoped> al final.
No mezclar Options API con Composition API. Solo Composition + script setup.

## Composables

- Prefijo `use`: useEstudiantes, useAuth, useTenant
- Un composable = una responsabilidad
- Retornan refs reactivos y funciones, no clases
- Siempre tipar el retorno explícitamente
- Usar VueUse antes de crear uno propio:
  - useLocalStorage, useOnline, useDebounceFn, useInfiniteScroll,
    useBreakpoints, useDateFormat, useClipboard

## Anti-patrones (rechazar en review)

- Props drilling > 2 niveles → usar provide/inject o store
- Watchers que mutan el mismo estado que observan → loop
- v-if + v-for en el mismo elemento → v-if en wrapper
- Eventos custom sin tipado → defineEmits<{...}>()
- Store que hace fetch directo → composable que usa el cliente generado
- Componentes > 300 líneas → dividir
- Template > 100 líneas → extraer componentes
```

#### `composable-catalog.md` — Inventario de composables

```markdown
# Catálogo de composables AVEDRA

## Del proyecto (src/composables/)
[Se llena conforme se implementan]

## De VueUse (ya instalado) — usar ANTES de crear propios

### Estado y storage
- useLocalStorage(key, default) — persistencia local con tipado
- useSessionStorage(key, default)
- useRefHistory(ref) — undo/redo

### Network y API
- useFetch(url, options) — fetch reactivo con loading/error
- useOnline() — detectar conexión/desconexión
- useEventSource(url) — SSE para tiempo real

### UI y DOM
- useBreakpoints(breakpoints) — responsive reactivo
- useInfiniteScroll(el, callback) — scroll infinito
- useDebounceFn(fn, ms) — debounce para filtros/búsqueda
- useThrottleFn(fn, ms)
- useElementVisibility(el) — lazy loading
- useDark() — toggle dark mode reactivo
- useTitle(title) — document.title reactivo

### Formularios
- useVModel(props, key) — v-model bidireccional en componentes
- useCloned(source) — deep clone reactivo para formularios de edición

### Tiempo
- useDateFormat(date, format) — formateo de fechas
- useNow() — reloj reactivo
- useTimeAgo(date) — "hace 5 minutos"
```

#### `design-system-rules.md` — Reglas del design system

```markdown
# Design System AVEDRA — Reglas para Vue

## Fuente de verdad
- Tokens: src/styles/tokens.css (importado global)
- Contrato de clases: docs/CLASS_CONTRACT.md
- Los tokens TS: src/types/tokens.json (para valores en JS)

## Reglas inquebrantables

1. TODO color viene de un token CSS (--color-*)
2. TODO spacing viene de un token (--space-*)
3. TODA tipografía viene de la escala (--font-size-*, --font-weight-*)
4. Los breakpoints usan los tokens de media query
5. Dark mode funciona automáticamente si se usan tokens

## Cómo agregar un nuevo token

1. Agregarlo en tokens.css (en la sección apropiada)
2. Definir valor light Y dark
3. Correr sync_tokens (si aplica)
4. Documentar en CLASS_CONTRACT.md si es una clase nueva
5. NUNCA crear tokens "de conveniencia" para un solo componente

## Librerías de componentes aprobadas

### Radix Vue (headless, accesible)
- Usar para: Dialog, Dropdown, Tooltip, Tabs, Accordion, Toggle
- Estilizar con tokens propios, NUNCA con estilos default
- Docs: https://www.radix-vue.com/

### Alternativa evaluada: shadcn-vue
- Es Radix Vue + Tailwind preconfigurado
- Si se adopta: eliminar estilos default y reemplazar con tokens
- Ventaja: componentes ya armados, menos trabajo
- Riesgo: Tailwind classes pueden colisionar con CLASS_CONTRACT

### Iconify (iconos)
- Usar @iconify/vue con colección 'lucide' (consistente, limpia)
- Nunca mezclar colecciones de iconos
- Iconos siempre con aria-hidden="true" si son decorativos
- Iconos funcionales (botones): aria-label obligatorio

### Floating UI (posicionamiento)
- Para tooltips, popovers, dropdowns custom
- Ya integrado en Radix Vue — preferir la versión de Radix

### Chart.js o Apache ECharts (gráficos)
- Para el módulo de informes/estadísticos
- Wrapper Vue: vue-chartjs o vue-echarts
- Colores de series: usar tokens de la paleta de datos (--color-chart-*)
```

---

### 5.2.3 Agente design_reviewer.md

```markdown
# Subagente: design_reviewer

## Rol

Revisa la calidad visual y de experiencia de usuario de componentes y vistas Vue.
Se ejecuta DESPUÉS del reviewer funcional y ANTES de marcar done.
No edita código. Aprueba o rechaza con hallazgos concretos.

## Protocolo

1. Leer el componente/vista a revisar
2. Leer .claude/references/design-system-rules.md
3. Ejecutar checklist de /design-check
4. Ejecutar checklist de /deslop-ui
5. Ejecutar checklist de /a11y-check
6. Emitir veredicto

## Criterio de aprobación

- 0 hallazgos 🔴 (bloquean)
- ≤ 3 hallazgos 🟡 (deben tener plan de corrección en el mismo PR)
- Los 🟢 se documentan pero no bloquean

## Diferencia con el reviewer funcional

El reviewer verifica que el código FUNCIONA (tipos, lógica, API, tests).
El design_reviewer verifica que el código se VE Y SE SIENTE bien
(jerarquía, spacing, color, accesibilidad, responsive, estados).

Ambos deben aprobar para marcar done.
```

### 5.3 Protocolo de referencia legacy → Vue (migración asistida)

Antes de reescribir cada página en Vue, el implementer del frontend **lee la
página NiceGUI equivalente** como blueprint. Esto evita re-inventar flujos que
ya están validados y minimiza el trabajo de diseño.

**Ubicación del legacy:** El repo `avedra-legacy-nicegui` (o una copia local)
debe estar accesible en una ruta hermana (`../avedra-legacy-nicegui/`).

**Protocolo por página (obligatorio):**

```
1. Identificar la página NiceGUI equivalente:
   ../avedra-legacy-nicegui/src/interface/pages/<modulo>/<pagina>.py

2. Leer y extraer:
   - Estructura de la página (secciones, tabs, cards)
   - Campos de formulario (nombre, tipo, validaciones, valores por defecto)
   - Permisos/roles que controlan visibilidad
   - Flujos de interacción (crear, editar, eliminar, filtrar)
   - Llamadas a servicios (qué método, qué parámetros)
   - Presenter asociado (si existe):
     ../avedra-legacy-nicegui/src/interface/presenters/<modulo>/<presenter>.py

3. Escribir un archivo de referencia ANTES de implementar:
   docs/migration-refs/<pagina>.md
   con: estructura, campos, permisos, endpoints que consumirá

4. Implementar la página Vue usando esa referencia + el contrato API
```

**Ejemplo concreto:**

```
Migrar: página de observaciones de convivencia

1. Leer: ../avedra-legacy-nicegui/src/interface/pages/convivencia/observaciones.py
2. Extraer:
   - Tabla con columnas: fecha, estudiante, tipo, descripción, docente
   - Filtros: grupo, periodo, tipo_observacion
   - Diálogo de creación: 5 campos, validación de fecha no futura
   - Permisos: profesor ve solo sus grupos, coordinador ve todos
   - Servicio: convivencia_service.listar_observaciones(tenant, grupo, periodo)
3. Escribir: docs/migration-refs/observaciones.md
4. Implementar: src/views/convivencia/ObservacionesView.vue
   consumiendo: GET /api/v1/observaciones + POST /api/v1/observaciones
```

**Regla:** El implementer NO puede crear una página Vue sin haber leído
primero la página NiceGUI equivalente. Si no existe equivalente (página nueva),
debe documentarlo explícitamente.

---

### 5.4 Agentes anti AI-slop

Los agentes anti-slop son reglas endurecidas en el `reviewer.md` de CADA repo
(backend y frontend) que detectan y rechazan los patrones típicos de código
generado por LLM que infla, oscurece o degrada la calidad.

**Definición de AI-slop para este proyecto:**

Código que un LLM produce por defecto y que un dev senior eliminaría en review:
verbosidad sin valor, abstracciones prematuras, nombres grandilocuentes,
comentarios que repiten el código, y patrones de "parece profesional" que no
resuelven nada.

**Reglas anti-slop para reviewer.md (ambos repos):**

```markdown
## Puerta anti AI-slop (obligatoria, bloquea merge)

Rechazar si aparece CUALQUIERA de estos patrones:

### 1. Over-commenting
- Comentarios que repiten lo que el código ya dice
  ❌ `# Increment counter` / `counter += 1`
  ❌ `# Get the user from the database` / `user = repo.get(id)`
- Docstrings de más de 1 línea en funciones internas
- Comentarios tipo "This function..." o "This method..."
- Bloques de comentarios decorativos (═══, ───, ★★★)

### 2. Abstracciones prematuras
- Clases con un solo método público (debería ser función)
- Wrappers que solo delegan sin agregar lógica
  ❌ `class UserFetcher: def fetch(self, id): return repo.get(id)`
- Interfaces/protocolos con una sola implementación y sin plan de segunda
- Factories que construyen un solo tipo
- Patterns (Strategy, Observer, Builder) aplicados a un solo caso

### 3. Nombres grandilocuentes
- Sufijos innecesarios: Manager, Handler, Processor, Orchestrator, Engine
  cuando el objeto hace algo simple
  ❌ `DataValidationOrchestrator` → ✅ `validate_data()`
- Prefijos redundantes: Abstract, Base, Core, Common, Shared, Utils
  cuando no hay herencia real ni reutilización demostrada

### 4. Código defensivo sin justificación
- Try/except que atrapa Exception genérica y la silencia
- Validaciones de tipos en lenguaje tipado (TypeScript strict / Python con mypy)
- Null checks redundantes cuando el tipo no admite None
- Fallbacks a valores por defecto que ocultan errores
  ❌ `value = data.get("key", "")  # si falta, string vacío está bien`
      (¿de verdad está bien? ¿o esconde un bug?)

### 5. Inflación estructural
- Archivos de < 20 líneas que deberían ser parte de otro archivo
- Carpetas con un solo archivo (excepto __init__.py / index.ts)
- Re-exportaciones que no agregan nada
  ❌ `index.ts` que solo hace `export { X } from './X'` para 1 módulo
- Constantes extraídas a archivo separado cuando se usan en un solo lugar

### 6. Verbosidad sintáctica
- Variables intermedias que se usan una sola vez y el nombre no aclara nada
  ❌ `const result = await fetchData(); return result;`
- Desestructuraciones innecesarias
- Spread operators para copiar objetos sin motivo
- `async/await` en funciones que no tienen operaciones async

### 7. Testing slop
- Tests que verifican la implementación en lugar del comportamiento
  ❌ `expect(service.method).toHaveBeenCalledWith(exactly, these, args)`
- Mocks de todo (pierde valor el test)
- Tests con nombres genéricos: "should work", "handles correctly"
- Setup de 30+ líneas para un assert de 1 línea
```

**Cómo se aplica:**

El reviewer ejecuta un checklist anti-slop DESPUÉS de validar corrección
funcional. Si encuentra slop:

1. Lista cada instancia con archivo:línea
2. Clasifica la severidad:
   - **Bloquea** (patrones 1-3): no merge hasta corregir
   - **Advierte** (patrones 4-7): merge con compromiso de limpiar en el mismo PR
3. Devuelve al implementer con instrucciones concretas de qué eliminar

**Script de detección automática (futuro):**

```bash
# scripts/check_slop.py
# Análisis estático que detecta los patrones más mecánicos:
# - Ratio comentarios/código > 0.3
# - Clases con 1 método público
# - Archivos con < 15 líneas de código real
# - Nombres que matchean la lista de sufijos grandilocuentes
# - Try/except Exception sin re-raise
```

Este script se agrega al harness de CI como paso informativo (no bloquea build,
pero el reviewer debe revisar sus hallazgos).

---

### 5.5 CLAUDE.md para avedra-shared-contracts

```markdown
# CLAUDE.md — avedra-shared-contracts

## Regla principal
Este repo es de SOLO LECTURA para humanos. Los archivos se generan desde
avedra-backend (OpenAPI, DTOs, enums) o se copian (tokens, class-contract).

## Nunca
- Editar openapi/*.yaml a mano
- Editar dto/*.json a mano
- Cambiar tokens sin actualizar la fuente en avedra-backend

## Cuándo actualizar
Solo cuando avedra-backend haya cambiado un endpoint, enum o modelo.
El flujo es:
  backend genera → shared-contracts recibe → frontend regenera cliente
```

No necesita subagentes complejos. David o un script de CI lo actualiza.

### 5.6 Herramienta generar_estructura.py

- **avedra-backend:** conservar el script actual, adaptado:
  - Eliminar `NOISE_DIRS` de progress/roadmaps/specs (no existen en el backend)
  - Agregar `app/` al árbol principal
- **avedra-frontend:** no necesita este script (usar `tree` o equivalente JS)
- **avedra-shared-contracts:** no lo necesita

---

## Fase 6 — CI/CD cruzado

### 6.1 GitHub Action en avedra-backend: publicar contrato

```yaml
# .github/workflows/publish-contract.yml
# Se dispara cuando cambia app/routes/ o src/domain/models/
# 1. Genera OpenAPI
# 2. Exporta DTOs como JSON Schema
# 3. Abre un PR automático en avedra-shared-contracts
```

### 6.2 GitHub Action en avedra-frontend: validar contrato

```yaml
# .github/workflows/validate-contract.yml
# Se dispara cuando avedra-shared-contracts publica una nueva versión
# 1. Regenera cliente API
# 2. Corre typecheck
# 3. Si falla → issue automático en avedra-frontend
```

### 6.3 Script de deteccion de drift

```bash
# scripts/check_contract_drift.sh
# Compara la versión de OpenAPI en shared-contracts
# con la que el backend generaría ahora.
# Si difieren → alerta.
```

---

## Fase 7 — Gestión del legado

> **Regla crítica:** El repo legacy NO se archiva ni se hace privado mientras
> la migración a Vue esté en curso. El implementer del frontend necesita
> leer `src/interface/pages/` como referencia (ver §5.3).

### 7.1 Renombrar repo actual

El repo `AVEDRA_manager_v2` pasa a ser referencia de migración:

```bash
gh repo rename avedra-legacy-nicegui
```

**NO** archivar en GitHub (el flag "Archive" bloquea clones y la lectura por agentes).
Mantenerlo como repo privado normal, solo de lectura por convención.

### 7.2 Marcar como legacy (sin congelar)

```bash
# En el repo legacy
git checkout main
cat > LEGACY.md << 'EOF'
# AVEDRA — Repo Legacy (NiceGUI)

El desarrollo activo está en:
- Backend: https://github.com/<usuario>/avedra-backend
- Frontend: https://github.com/<usuario>/avedra-frontend

Este repositorio se mantiene SOLO LECTURA como referencia para:
- Migración de páginas a Vue (src/interface/pages/)
- Consulta de flujos y validaciones ya implementados
- Paridad funcional durante el fork

NO hacer commits nuevos aquí. NO archivar hasta que la migración a Vue
esté completa (todas las páginas migradas y validadas).
EOF
git add LEGACY.md
git commit -m "Mark as legacy reference — active development in avedra-backend + avedra-frontend"
```

### 7.3 Documentar mapa de correspondencia

Crear `docs/MIGRATION_MAP.md` en el repo legacy:

```markdown
| Archivo legado | Destino | Estado migración |
|---|---|---|
| src/domain/* | avedra-backend/src/domain/* | Migrado en Fase 2 |
| src/services/* | avedra-backend/src/services/* | Migrado en Fase 2 |
| src/infrastructure/* | avedra-backend/src/infrastructure/* | Migrado en Fase 2 |
| src/interface/pages/inicio.py | avedra-frontend/src/views/InicioView.vue | Pendiente |
| src/interface/pages/convivencia/* | avedra-frontend/src/views/convivencia/* | Pendiente |
| src/interface/pages/academico/* | avedra-frontend/src/views/academico/* | Pendiente |
| src/interface/pages/admin/* | avedra-frontend/src/views/admin/* | Pendiente |
| src/interface/pages/evaluacion/* | avedra-frontend/src/views/evaluacion/* | Pendiente |
| src/interface/pages/informes/* | avedra-frontend/src/views/informes/* | Pendiente |
| src/interface/presenters/* | Lógica absorbida en composables Vue | Pendiente |
| src/interface/design/components/* | avedra-frontend/src/components/ui/* | Pendiente |
| scripts/* | avedra-backend/scripts/* | Migrado en Fase 2 |
| roadmaps/* | Solo referencia, no migra | N/A |
```

### 7.4 Archivado definitivo (post-migración completa)

**Solo** cuando todas las filas de MIGRATION_MAP.md estén marcadas como
"Migrado" y la suite E2E del frontend Vue pase al 100%:

```bash
# Ahora sí, archivar
gh repo archive avedra-legacy-nicegui
```

---

## Flujo de trabajo cross-repo con Claude Code

### Escenario: "Feature que toca backend Y frontend"

Ejemplo: agregar filtro por rango de fechas en el listado de observaciones.

```
PASO 1 — Sesión Claude Code en avedra-backend
├── Leader lee el spec
├── Implementer crea endpoint GET /api/v1/observaciones?desde=&hasta=
├── Implementer escribe tests
├── Reviewer valida
├── Leader ejecuta: python scripts/generate_openapi.py
├── Leader anota: "CONTRACT_CHANGED: GET /observaciones ahora acepta ?desde &hasta"
└── David commitea y pushea

PASO 2 — Actualizar contrato (manual o CI)
├── Copiar openapi.yaml actualizado a avedra-shared-contracts
├── Commitear y pushear (o el CI lo hace automáticamente)

PASO 3 — Sesión Claude Code en avedra-frontend
├── Leader lee el contrato actualizado
├── npm run generate:api  (regenera cliente TypeScript)
├── Implementer crea componente DateRangeFilter.vue
├── Implementer actualiza la vista de observaciones
├── Reviewer valida tipos, a11y, tokens
└── David commitea y pushea
```

### Principios del flujo cross-repo

1. **Backend primero, siempre.** El backend define la verdad; el frontend la consume.
2. **El contrato es el handshake.** Nunca asumir que un endpoint existe sin verificar
   `avedra-shared-contracts/openapi/`.
3. **David es el coordinador humano.** Claude Code no puede abrir sesiones en otros repos.
   David decide cuándo pasar de backend → contrato → frontend.
4. **PRs independientes, issue compartido.** Un GitHub Issue describe el feature completo.
   Cada repo tiene su propio PR que referencia ese issue.
5. **Nunca compartir código productivo entre repos.** Solo contratos (OpenAPI, DTOs, tokens).

### Escenario: "Hotfix que solo toca frontend"

```
Sesión Claude Code en avedra-frontend
├── Leader confirma que no requiere cambio de API
├── Implementer corrige el bug en el componente Vue
├── Reviewer valida
└── David commitea y pushea
```

No se toca backend ni contratos. El frontend evoluciona independientemente
dentro de los límites del contrato existente.

### Escenario: "Cambio de enum que afecta ambos"

```
PASO 1 — avedra-backend: agregar valor al enum
PASO 2 — avedra-shared-contracts: regenerar enums.json
PASO 3 — avedra-frontend: el typecheck falla → implementer actualiza el switch/case
```

El CI de la fase 6 automatiza el paso 2 y alerta sobre el paso 3.

---

## Orden de ejecución recomendado

```
Fase 0 (1 día)    ← preparación, sin riesgo
Fase 1 (30 min)   ← crear repos vacíos
Fase 2 (2-3 días) ← CRÍTICA: split del backend, la más delicada
Fase 3 (1 día)    ← contracts, depende de Fase 2
Fase 5 (1 día)    ← agentes Claude, puede ir en paralelo con Fase 3
Fase 4 (1-2 días) ← scaffold Vue, depende de Fase 3
Fase 6 (1-2 días) ← CI/CD, depende de Fase 2 + 4
Fase 7 (30 min)   ← archivar legado, al final
```

**Total estimado: 7-10 días de trabajo.**

---

## Dependencias y prerrequisitos

```
Fase 0 → Fase 1 → Fase 2 → Fase 3 → Fase 4
                      │                  │
                      └── Fase 5 ────────┘
                                         │
                                     Fase 6 → Fase 7
```

### Prerrequisitos NO negociables antes de iniciar

1. **Backend API operativo** (al menos el stub de FastAPI con 2-3 endpoints reales).
   Sin esto, el contrato compartido es ficción y el frontend no puede generar
   su cliente. Ver `backend_00_roadmap` pasos 01-09.

2. **App NiceGUI funcionalmente completa** (la épica activa terminada).
   Si quedan features críticas sin implementar, el legacy pierde valor como
   referencia de paridad.

3. **Suite de tests verde y estable.** El split va a romper imports; necesitas
   una baseline para detectar regresiones.

---

## Notas sobre generar_estructura.py

El script actual vive en `scripts/` y genera árboles Markdown del proyecto.
Post-split:

- **avedra-backend:** conservar una versión adaptada (sin NOISE_DIRS de roadmaps/specs/progress,
  agregar `app/` al scope). Mantener consola UTF-8.
- **avedra-frontend:** usar herramientas nativas del ecosistema Node si se necesita.
- **avedra-shared-contracts:** no necesita generador de estructura.

La versión adaptada del backend hereda el bloque de consola UTF-8 y la
exclusión de CACHE_DIRS, pero simplifica NOISE_DIRS a solo `logs/` o similar.
