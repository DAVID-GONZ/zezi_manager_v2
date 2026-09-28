# Repo Split — Guia manual paso a paso

> David ejecuta estos pasos directamente. Los que necesitan Claude Code
> tienen specs en `specs/split_*` y se marcan con **[SPEC]**.
>
> Referencia completa: `repo_split_00_pasos.md`

---

## Prerrequisitos NO negociables

- [ ] Rebrand completado (rebrand_01 a rebrand_05 en `done`)
- [ ] `python init.py` todo verde
- [ ] `python -m pytest tests/ -x` todo verde
- [ ] Working tree limpio (`git status` sin pendientes)
- [ ] Backend API con al menos stub FastAPI + 2-3 endpoints reales
- [ ] App NiceGUI funcional y estable como referencia de paridad

---

## Fase 0 — Preparacion y snapshot (~1 dia)

### 0.1 Verificar estado limpio

```bash
python init.py
python -m pytest tests/ -x
git status
```

- [ ] init.py verde
- [ ] Tests verdes
- [ ] Working tree limpio

### 0.2 Tag y rama de respaldo

```bash
git tag pre-split-v2.0
git branch backup/pre-split
git push origin pre-split-v2.0
git push origin backup/pre-split
```

- [ ] Tag `pre-split-v2.0` creado y pusheado
- [ ] Rama `backup/pre-split` creada y pusheada

### 0.3 Generar estructura de referencia

```bash
python scripts/generar_estructura.py
git add docs/estructura_proyecto.md docs/estructura_tests.md
git commit -m "Pre-split: snapshot de estructura del proyecto"
git push
```

- [ ] Archivos de estructura generados y commiteados

### 0.4 Verificar inventario de archivos

Revisar la tabla en `repo_split_00_pasos.md` seccion 0.4.
Confirmar que el mapa de archivos por destino sigue vigente.

- [ ] Inventario revisado

---

## Fase 1 — Crear repos vacios en GitHub (~30 min)

### 1.1 Crear repos

```bash
gh repo create avedra-backend --private --description "AVEDRA: dominio, servicios, API REST"
gh repo create avedra-frontend --private --description "AVEDRA: Vue 3 + Vite, PWA/Tauri/Capacitor"
gh repo create avedra-shared-contracts --private --description "AVEDRA: OpenAPI, DTOs, enums, design tokens"
```

- [ ] `avedra-backend` creado
- [ ] `avedra-frontend` creado
- [ ] `avedra-shared-contracts` creado

### 1.2 Configurar .gitignore base

**avedra-backend/.gitignore:**
```
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
*.pyc
.env
*.db
logs/
```

**avedra-frontend/.gitignore:**
```
node_modules/
dist/
.env
*.local
```

**avedra-shared-contracts/.gitignore:**
```
node_modules/
```

- [ ] .gitignore en los 3 repos

---

## Fase 2 — Split del backend (CRITICA, ~2-3 dias)

### 2.1 Clonar repo actual como base del backend

```bash
cd ..
git clone --no-hardlinks zeci_manager_v2 avedra-backend
cd avedra-backend
```

> Ajustar `zeci_manager_v2` al nombre real del directorio en disco.

- [ ] Clon creado en `../avedra-backend`

### 2.2 Filtrar historial con git-filter-repo

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

**Verificaciones inmediatas:**

```bash
# NO debe existir
ls src/interface/ 2>/dev/null && echo "ERROR: interface/ sigue aqui" || echo "OK: interface/ eliminado"

# SI deben existir
ls src/domain/ src/services/ src/infrastructure/ tests/
```

- [ ] `filter-repo` ejecutado sin errores
- [ ] `src/interface/` eliminado del historial
- [ ] `src/domain/`, `src/services/`, `tests/` presentes

### [SPEC] 2.3-2.6 Adaptar backend para funcionar sin NiceGUI

> **Spec:** `specs/split_01_adapt_backend/`
>
> Crear stub FastAPI, limpiar pyproject.toml de dependencias NiceGUI,
> adaptar init.py (eliminar chequeos de design system), adaptar
> container.py (eliminar registros de interfaz).

- [ ] Spec `split_01_adapt_backend` activado y completado

### 2.7 Verificar arranque del backend

```bash
python -c "from src.domain import models; print('domain OK')"
python -c "from src.services import usuario_service; print('services OK')"
python -m pytest tests/ -x

# Verificar 0 referencias a src/interface
grep -rn "src\.interface\|src/interface\|from interface" src/ tests/
```

> El grep debe retornar 0 resultados.

- [ ] Imports limpios
- [ ] Tests verdes
- [ ] 0 referencias a `src/interface/`

### 2.8 Conectar remote y pushear

```bash
git remote add origin https://github.com/<tu-usuario>/avedra-backend.git
git push -u origin main
```

- [ ] Push a GitHub exitoso

---

## Fase 3 — Shared contracts (~1 dia)

### 3.1 Inicializar repo

```bash
cd ../avedra-shared-contracts
git init
mkdir -p openapi dto design-system
```

- [ ] Repo inicializado con directorios base

### [SPEC] 3.2-3.3 Extraer OpenAPI y DTOs

> **Spec:** `specs/split_02_shared_contracts/`
>
> Crear OpenAPI stub (si API no esta lista) o generador, crear
> script export_schemas.py para DTOs como JSON Schema.

- [ ] Spec `split_02_shared_contracts` activado y completado

### 3.4 Copiar design tokens

```bash
# Desde el repo legacy
cp ../zeci_manager_v2/src/interface/design/styles/tokens.css design-system/tokens.css

# Generar tokens.json
cd ../zeci_manager_v2
python scripts/sync_tokens.py --emit-json > ../avedra-shared-contracts/design-system/tokens.json
cd ../avedra-shared-contracts

# Copiar documentacion
cp ../zeci_manager_v2/src/interface/design/styles/CLASS_CONTRACT.md design-system/class-contract.md
cp ../zeci_manager_v2/src/interface/design/styles/PORTABILITY.md design-system/portability.md
```

> Ajustar rutas si el repo legacy ya fue renombrado.

- [ ] `tokens.css` copiado
- [ ] `tokens.json` generado
- [ ] `class-contract.md` copiado
- [ ] `portability.md` copiado

### 3.5 Commit inicial y push

```bash
git add .
git commit -m "Initial shared contracts: OpenAPI stub, DTOs, enums, design tokens"
git remote add origin https://github.com/<tu-usuario>/avedra-shared-contracts.git
git push -u origin main
```

- [ ] Commit y push exitoso

---

## Fase 4 — Scaffold frontend Vue (~1-2 dias)

> Corresponde a `vue_00_scaffold` y `vue_01_ci_build` del roadmap Vue
> (`fork_ui_vue_00_roadmap/roadmap.md`). No hay spec separada aqui.

### 4.1 Crear proyecto

```bash
npm create vite@latest ../avedra-frontend -- --template vue-ts
cd ../avedra-frontend
npm install
npm install vue-router@4 pinia @vueuse/core axios
```

- [ ] Proyecto Vite + Vue 3 + TS creado

### 4.2 Integrar tokens desde shared-contracts

```bash
mkdir -p src/styles src/types
cp ../avedra-shared-contracts/design-system/tokens.css src/styles/tokens.css
cp ../avedra-shared-contracts/design-system/tokens.json src/types/tokens.json
```

Importar `tokens.css` en `src/main.ts`:
```typescript
import './styles/tokens.css'
```

- [ ] Tokens integrados y referenciados

### 4.3 Configurar cliente API

```bash
npm install openapi-typescript --save-dev
npx openapi-typescript ../avedra-shared-contracts/openapi/avedra-openapi.yaml -o src/api/generated.ts
```

Agregar script en `package.json`:
```json
{
  "scripts": {
    "generate:api": "openapi-typescript ../avedra-shared-contracts/openapi/avedra-openapi.yaml -o src/api/generated.ts"
  }
}
```

- [ ] Cliente API generado
- [ ] Script `generate:api` en package.json

### 4.4 Estructura base

Crear la estructura descrita en `repo_split_00_pasos.md` seccion 4.4:

```
src/
├── api/           (client.ts + generated.ts)
├── components/ui/ (design system Vue)
├── composables/
├── router/index.ts
├── stores/        (auth.ts, tenant.ts)
├── styles/        (tokens.css, theme.css)
├── types/
├── views/
└── main.ts
```

- [ ] Estructura creada

### 4.5 Verificar arranque

```bash
npm run dev        # levanta en localhost
npm run build      # bundle sin errores
```

- [ ] Dev server arranca
- [ ] Build exitoso

### 4.6 Push a GitHub

```bash
git remote add origin https://github.com/<tu-usuario>/avedra-frontend.git
git push -u origin main
```

- [ ] Push exitoso

---

## Fase 5 — Agentes Claude por repo (~1 dia)

### [SPEC] 5.1 + 5.5 + 5.6 Agentes para avedra-backend

> **Spec:** `specs/split_03_agents_backend/`
>
> CLAUDE.md, leader.md, implementer.md, reviewer.md, spec_author.md,
> generar_estructura.py adaptado, CLAUDE.md de shared-contracts.

- [ ] Spec `split_03_agents_backend` activado y completado

### [SPEC] 5.2-5.4 Agentes para avedra-frontend

> **Spec:** `specs/split_04_agents_frontend/`
>
> Agents (leader, implementer, reviewer, spec_author, design_reviewer),
> skills (/design-check, /deslop-ui, /component-audit, /a11y-check, /migrate-page),
> references (vue-patterns, composable-catalog, design-system-rules),
> reglas anti AI-slop, protocolo legacy-to-Vue, CLAUDE.md.

- [ ] Spec `split_04_agents_frontend` activado y completado

---

## Fase 6 — CI/CD cruzado (~1-2 dias)

### [SPEC] 6.1-6.3 GitHub Actions y drift

> **Spec:** `specs/split_05_cicd/`
>
> publish-contract.yml (backend), validate-contract.yml (frontend),
> check_contract_drift.sh (backend).

- [ ] Spec `split_05_cicd` activado y completado

---

## Fase 7 — Gestion del legado (~30 min)

### 7.1 Renombrar repo actual

```bash
gh repo rename avedra-legacy-nicegui
```

> **NO archivar.** El flag Archive bloquea clones y lectura por agentes.
> Mantener como repo privado normal.

- [ ] Repo renombrado a `avedra-legacy-nicegui`

### 7.2 Marcar como legacy

Crear `LEGACY.md` en el repo legacy:

```markdown
# AVEDRA -- Repo Legacy (NiceGUI)

El desarrollo activo esta en:
- Backend: https://github.com/<tu-usuario>/avedra-backend
- Frontend: https://github.com/<tu-usuario>/avedra-frontend

Este repositorio se mantiene SOLO LECTURA como referencia para:
- Migracion de paginas a Vue (src/interface/pages/)
- Consulta de flujos y validaciones ya implementados
- Paridad funcional durante el fork

NO hacer commits nuevos aqui. NO archivar hasta que la migracion a Vue
este completa (todas las paginas migradas y validadas).
```

```bash
git add LEGACY.md
git commit -m "Mark as legacy reference -- active development in avedra-backend + avedra-frontend"
git push
```

- [ ] LEGACY.md creado y pusheado

### 7.3 Documentar mapa de correspondencia

Crear `docs/MIGRATION_MAP.md` en el repo legacy con la tabla de
correspondencias de `repo_split_00_pasos.md` seccion 7.3.

```bash
git add docs/MIGRATION_MAP.md
git commit -m "Add migration map: legacy files -> new repos"
git push
```

- [ ] MIGRATION_MAP.md creado y pusheado

### 7.4 Archivado definitivo (solo post-migracion)

**Condiciones (las dos deben cumplirse):**

1. Todas las filas de MIGRATION_MAP.md marcadas como "Migrado"
2. Suite E2E del frontend Vue pasa al 100%

```bash
gh repo archive avedra-legacy-nicegui
```

- [ ] Archivado (cuando la migracion este completa)

---

## Resumen de dependencias

```
Fase 0 (1d)     Preparacion
    |
Fase 1 (30m)    Crear repos
    |
Fase 2 (2-3d)   Split backend  [SPEC: split_01]
    |         \
Fase 3 (1d)     Contracts [SPEC: split_02]
    |           |
    |       Fase 5 (1d)   Agentes [SPEC: split_03, split_04]
    |           |
Fase 4 (1-2d)   Scaffold Vue (roadmap vue_00)
    |
Fase 6 (1-2d)   CI/CD [SPEC: split_05]
    |
Fase 7 (30m)    Legacy
```

**Total estimado: 7-10 dias.**
