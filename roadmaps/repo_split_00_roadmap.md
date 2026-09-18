# repo_split_00 — Roadmap: división del repositorio en backend, frontend y contratos compartidos

## Objetivo

Separar el proyecto actual en tres líneas de responsabilidad claras para que la evolución posterior siga el plan de los roadmaps de backend y Vue sin mezclar arquitectura, versionado ni despliegues.

La meta no es “reorganizar por estética”, sino evitar:

- acoplar lógica de negocio y UI en el mismo historial de Git
- mezclar features de backend y frontend en el mismo pull request
- hacer evolucionar el contrato API sin una fuente de verdad
- mantener NiceGUI como base de desarrollo activo cuando la estrategia ya apunta a Vue + API REST

---

## Decisión estratégica

Se adopta una división por repositorios y responsabilidades:

- `zeci-backend`: fuente de verdad del negocio, repositorios, servicios, modelos y API REST
- `zeci-frontend`: cliente Vue 3 + Vite, PWA/Tauri/Capacitor según roadmap
- `zeci-shared-contracts`: contratos compartidos (OpenAPI, DTOs, enums, design tokens y documentación de frontera API/UI)

Se considera `NiceGUI` como legado funcional, no como repositorio activo de la nueva arquitectura.

---

## Por qué dos repos activos y un contrato compartido

La evidencia de los roadmaps confirma que la evolución del sistema sigue dos rutas distintas:

- [backend_00_roadmap_sqlalchemy_api/roadmap.md](backend_00_roadmap_sqlalchemy_api/roadmap.md) define la civilización del backend, SQLAlchemy/Core y REST
- [fork_ui_vue_00_roadmap/roadmap.md](fork_ui_vue_00_roadmap/roadmap.md) define el frontend Vue como una migración posterior que consume la API

Esto hace que una estructura monolítica sea contraria al objetivo:

- el backend necesita versionado, tests y despliegue propios
- el frontend necesita despliegue, build y UI propios
- el contrato entre ambos debe ser explícito y versionado

---

## Estructura de repositorios

### 1) zeci-backend

Debe contener la lógica del sistema y la API:

```text
zeci-backend/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   ├── main.py
│   │   ├── routes/
│   │   └── schemas/
│   └── main.py
├── src/
│   ├── domain/
│   │   ├── models/
│   │   ├── ports/
│   │   ├── exceptions.py
│   │   └── policies/
│   ├── application/
│   │   ├── services/
│   │   ├── use_cases/
│   │   └── commands/
│   ├── infrastructure/
│   │   ├── db/
│   │   ├── logging/
│   │   ├── exporters/
│   │   └── auth/
│   └── config.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── scripts/
│   ├── init.py
│   ├── run_tests.py
│   ├── check_design.py
│   └── check_auditoria.py
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── security/
│   └── decisions/
├── pyproject.toml
├── requirements.txt
├── README.md
├── .env.example
├── Dockerfile
├── .gitignore
└── CHANGELOG.md
```

Responsabilidades:

- modelado de dominio
- reglas de negocio
- repositorios e infraestructura
- API REST
- autenticación/seguridad
- validación y tests del backend

---

### 2) zeci-frontend

Debe contener la capa de cliente y experiencia de usuario:

```text
zeci-frontend/
├── src/
│   ├── app/
│   │   ├── router/
│   │   ├── layouts/
│   │   └── views/
│   ├── components/
│   │   ├── ui/
│   │   ├── forms/
│   │   ├── tables/
│   │   └── charts/
│   ├── stores/
│   │   ├── auth.ts
│   │   ├── tenant.ts
│   │   └── app.ts
│   ├── api/
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   ├── estudiantes.ts
│   │   ├── convivencia.ts
│   │   └── horarios.ts
│   ├── composables/
│   ├── styles/
│   │   ├── tokens.css
│   │   ├── theme.css
│   │   └── class-contract.css
│   ├── types/
│   ├── utils/
│   └── main.ts
├── public/
│   ├── manifest.json
│   └── icons/
├── tests/
│   ├── unit/
│   ├── e2e/
│   └── visual/
├── vite.config.ts
├── package.json
├── tsconfig.json
├── README.md
├── .env.example
├── .gitignore
├── CHANGELOG.md
└── vitest.config.ts
```

Responsabilidades:

- Vue 3 + Vite
- router, stores, clientes HTTP
- UI con tokens y design system portátil
- PWA/Tauri/Capacitor según roadmap de fork
- tests de UI y E2E

---

### 3) zeci-shared-contracts

Debe contener el contrato explícito y shared entre backend y frontend:

```text
zeci-shared-contracts/
├── openapi/
│   ├── zeci-openapi.yaml
│   └── zeci-openapi.json
├── dto/
│   ├── auth.json
│   ├── estudiante.json
│   ├── convivencia.json
│   └── horario.json
├── enums/
│   ├── roles.json
│   ├── estados.json
│   └── tipos.json
├── design-system/
│   ├── tokens.json
│   ├── class-contract.md
│   └── portability.md
├── README.md
├── CHANGELOG.md
└── package.json
```

Responsabilidades:

- versionar la API contract
- documentar DTOs, enums y payloads
- mantener una fuente unificada para diseño y tipos
- evitar drift entre backend y frontend

---

## Política de actualización de contracts compartidos

Los contracts no deben ser “docs de referencia” sueltas. Deben ser generados y versionados como parte del ciclo de entrega.

### Regla base

- el backend define el contrato real
- la UI consume el contrato generado
- cualquier cambio de payload, enum, ruta o respuesta requiere:
  1. cambio en el backend
  2. regeneración del OpenAPI
  3. actualización del shared contract
  4. regeneración del cliente del frontend
  5. ejecución de CI y tests

### Flujo recomendado

```bash
# Backend
python scripts/generate_openapi.py

# Shared
cp openapi/zeci-openapi.yaml ../zeci-shared-contracts/openapi/

# Frontend
npm run generate:api
npm run typecheck
npm run build
```

### Requisito de CI

- si `openapi.yaml` cambia, el frontend debe regenerar tipos
- si los tipos del frontend no coinciden con la API, el build debe fallar
- si el backend cambia un enum sin tocar el contrato compartido, debe romper la pipeline

---

## Qué hacer con NiceGUI

NiceGUI no debe ser tratado como el futuro activo del producto. Debe quedar como legado funcional para referencia, mas no como base de desarrollo nuevo.

### Estado recomendado

- `NiceGUI` queda como rama o repositorio de legado
- se conserva para:
  - comparar pantallas y flujos
  - recuperar comportamientos ya validados
  - auditar la funcionalidad que todavía no migró a Vue
- no se sigue desarrollando sobre él como si fuera el sistema principal

### Recomendación de gestión

Opción A — mejor para claridad:

- mantener el repo actual como `zeci-legacy-nicegui`
- crear `zeci-backend` y `zeci-frontend` como activos

Opción B — si se quiere mantener el repo actual para historial:

- crear una rama `legacy/nicegui` y dejar `main` para la nueva arquitectura
- mover la referencia funcional a una carpeta `legacy/` o un repo archivado

### Regla operativa

- el nuevo trabajo va sobre backend y frontend
- NiceGUI solo sirve como referencia para migración, no como código de producción activo

---

## Estrategia de Git y split real

### Paso 1: guardar el repo actual como referencia

```bash
git checkout main
git tag pre-split
git branch backup/pre-split
```

### Paso 2: crear los repos nuevos en GitHub

- `https://github.com/<usuario>/zeci-backend`
- `https://github.com/<usuario>/zeci-frontend`
- opcional: `https://github.com/<usuario>/zeci-shared-contracts`

### Paso 3: conservar el repo original como legado

El repositorio actual deja de ser el repo principal de mantenimiento y pasa a tener carácter histórico o de referencia funcional.

### Paso 4: migrar solo backend al nuevo repo

Se usa filtrado del historial para conservar solo archivos de negocio y API.

```bash
git filter-repo \
  --path app \
  --path src \
  --path tests \
  --path scripts \
  --path pyproject.toml \
  --path requirements.txt \
  --path README.md \
  --path docs \
  --path .env.example \
  --path Dockerfile \
  --path .gitignore
```

Luego se conecta el nuevo origen:

```bash
git remote add origin https://github.com/<usuario>/zeci-backend.git
git branch -M main
git push -u origin main
```

### Paso 5: crear frontend desde cero

```bash
npm create vite@latest zeci-frontend -- --template vue-ts
cd zeci-frontend
git init
git remote add origin https://github.com/<usuario>/zeci-frontend.git
git add .
git commit -m "Initial Vue frontend"
git push -u origin main
```

### Paso 6: crear repo de contratos compartidos

```bash
mkdir zeci-shared-contracts
cd zeci-shared-contracts
git init
git remote add origin https://github.com/<usuario>/zeci-shared-contracts.git
```

---

## Política de ramas y versionado

### Ramas por repositorio

Cada repo usa su propio flujo:

```text
main
    develop
    feature/<nombre>
    release/<version>
    hotfix/<nombre>
```

### Versionado SemVer

- backend: `MAJOR.MINOR.PATCH`
- frontend: `MAJOR.MINOR.PATCH`
- shared contracts: `MAJOR.MINOR.PATCH`

Regla:

- `PATCH`: correcciones compatibles
- `MINOR`: nuevas funciones compatibles
- `MAJOR`: breaking changes o cambios del contrato API

### Compatibilidad entre backend y frontend

El frontend debe declarar explícitamente qué versión de API soporta:

```yaml
backend_api_min: "1.8.0"
backend_api_max: "2.x"
```

Esto evita que el UI se rompa con un backend actualizado sin avisar.

---

## Reglas de gobierno del split

1. Backend y frontend nunca comparten código productivo.
2. Todo cambio en API requiere actualizacion del contract compartido.
3. NiceGUI es referencia y no base de trabajo activo.
4. Los PRs de backend y frontend son independientes.
5. El frontend no puede depender de modelos internos del backend; solo de DTOs/contratos publicados.
6. La fuente de verdad del dominio sigue estando en backend.

---

## Criterio de done del split

El split se considera correcto cuando se cumple todo esto:

- `zeci-backend` tiene dominio, servicios, repositorios e infraestructura
- `zeci-frontend` tiene Vue 3 + router + stores + cliente API
- `zeci-shared-contracts` tiene OpenAPI y DTOs versionados
- NiceGUI queda archivado o en legado como referencia
- no hay código activo de UI mezclado en backend
- la API y la UI se pueden evolucionar independientemente pero con contrato explícito
- las ramas y versiones por repo están establecidas y documentadas

---

## Conclusión

La división por repositorios es la estrategia adecuada para este proyecto porque refleja la arquitectura ya documentada en los roadmaps y evita un crecimiento artificial del historial de Git.

El principio guía es simple:

- backend = negocio + API
- frontend = experiencia + consumo API
- shared contracts = contrato formal entre ambos
- NiceGUI = legado funcional, no desarrollo activo

Con esta organización, el roadmap de backend y el roadmap de Vue se pueden ejecutar en paralelo sin mezclarse ni romper la integridad del producto.
