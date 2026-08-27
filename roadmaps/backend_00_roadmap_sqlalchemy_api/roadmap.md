# backend_00 — Roadmap: evolución backend + fork Vue

## Decisión de David (2026-07-27)

La estrategia tiene **dos etapas claras** con un fork de por medio:

### Etapa A — App NiceGUI completamente funcional + backend sólido

1. Terminar toda la funcionalidad pendiente con NiceGUI (app completa, usable).
2. Consolidar la base de tests.
3. Migrar a SQLAlchemy Core para doble backend (SQLite local / Postgres nube).
4. Exponer API REST con FastAPI.
5. Desplegar en la nube con Postgres + canales de tiempo real.
6. Design system portable (tokens JSON, CSS desacoplado, contratos de componentes).

### Etapa B — Fork para comercialización

1. **Fork del proyecto** → front Vue que consume la API ya probada.
   Tres productos del mismo fork:
   - **App web** (navegador, online-offline con PWA/Service Worker).
   - **App WebView2** (empaquetada para escritorio, con SQLite local).
   - **Versión navegador** (la misma PWA desplegada en la nube).
2. **App Android** — desarrollo posterior, consume la misma API REST.

### Decisión de stack técnico para la Etapa B (2026-07-27)

Evaluadas las opciones (Vue, React, Svelte, Next.js, Nest.js), se elige:

**Frontend web: Vue 3 + Vite + Composition API**

- Curva de aprendizaje baja desde Python/NiceGUI (refs reactivos ≈ modelo mental similar).
- Ecosistema maduro de componentes UI (Naive UI o PrimeVue — evaluar contra tokens Aula Serena).
- Documentación oficial traducida al español.
- Complejidad baja para dev solo vs. React (menos decisiones de arquitectura).
- PWA offline con `vite-plugin-pwa` (Service Worker + precache automático).

**Escritorio: Tauri v2**

- Usa WebView2 nativo de Windows (ya preinstalado en Windows 10/11).
- Bundle ~3MB (vs. ~80MB de Electron).
- Plugin oficial de SQLite para la versión local offline.
- Mismo código Vue, empaquetado diferente.

**Android: Capacitor (Ionic)**

- Envuelve la misma PWA Vue en contenedor nativo.
- Acceso a APIs nativas (notificaciones push, almacenamiento, cámara).
- SQLite local vía `@capacitor-community/sqlite`.
- Un solo código fuente → web + Android + iOS.

**Librerías complementarias decididas:**

- Vue Router (navegación).
- Pinia (estado global, reemplaza Vuex).
- VueUse (utilidades reactivas: `useOnline`, `useLocalStorage`, etc.).
- Axios o fetch nativo para consumir la API REST.

**Descartados y por qué:**

- **React / Next.js** — Mayor complejidad (hooks, re-renders, JSX) sin beneficio
  para un dev solo con background Python. Next.js añade SSR innecesario para un
  dashboard privado detrás de login.
- **Svelte / SvelteKit** — Sintaxis más simple pero ecosistema de componentes UI
  inmaduro para apps de gestión (tablas, formularios complejos).
- **Nest.js** — Es un framework de backend (Node.js). No aplica; ya tenemos FastAPI.
- **Electron** — Bundle pesado (~80MB), empaqueta Chromium completo. Tauri es superior
  para este caso.
- **React Native** — Requiere reescribir UI en componentes nativos. Capacitor reutiliza
  el mismo código Vue.

### Estructura del fork (un código, tres productos)

```
zeci-vue/
├── src/                    ← código Vue compartido
│   ├── components/         ← design system (consume tokens.json)
│   ├── views/              ← páginas por módulo
│   ├── stores/             ← Pinia (estado + cola de sync offline)
│   ├── api/                ← cliente REST + SSE
│   └── service-worker.ts   ← PWA offline (vite-plugin-pwa)
├── src-tauri/              ← config Tauri (escritorio)
├── capacitor.config.ts     ← config Capacitor (Android)
└── vite.config.ts          ← build para web
```

Builds:

- `npm run build` → web (PWA desplegable).
- `npm run tauri build` → `.exe` WebView2 (~3MB).
- `npx cap sync && npx cap build android` → APK.

### Principios confirmados

- **Todo en modo desarrollo.** No hay datos de producción. La BD se recrea desde
  `create_all()` + seed. No hay migración de datos en este roadmap.
- **Alembic queda fuera.** Se introduce como paso previo al primer despliegue real
  con datos de producción que preservar, no ahora.
- **SQLAlchemy Core** (no ORM completo ni SQL crudo duplicado), porque hay que
  mantener dos dialectos de por vida.
- **NiceGUI se mantiene como el front principal** durante toda la Etapa A. La
  versión NiceGUI sigue sirviendo como producto de uso propio y referencia funcional.

---

## Estado actual (revisión de 2026-07-27)

### Lo que juega a favor

- **Arquitectura hexagonal real**: `src/domain/ports/*_repo.py` (interfaces) +
  `src/infrastructure/db/repositories/sqlite_*` (adaptadores). Servicios y UI nunca
  tocan SQLite directo. `container.py` es el único punto de cableado.
- **Repos aceptan inyección de conexión** (`__init__(self, conn=None)`) → la costura
  para conmutar backend ya existe.
- **1.331 funciones de test** en 75 archivos. Los tests de **servicios y dominio usan
  `FakeRepository`** (sin BD) → son agnósticos del backend y migran sin coste.
- **Design system con fuente única**: `tokens.css` (187 variables) ↔ `tokens.py`
  sincronizados por `scripts/sync_tokens.py`. CSS separado en 24 archivos por
  componente/dominio.

### Deuda de acoplamiento a SQLite

- **Schema como strings DDL de SQLite** en `schema.py` (56 `AUTOINCREMENT`, tipos
  laxos). No portable a Postgres tal cual.
- **SQL crudo pegado al dialecto** en repos: ~624 placeholders `?`, ~105
  `last_insert_rowid`/`lastrowid`, 9 `INSERT OR REPLACE/IGNORE`, ~41 funciones de
  fecha SQLite.
- **Harness de tests 100% acoplado a SQLite**: `conftest.py` hace
  `sqlite3.connect(":memory:")`, aplica DDL cruda. 8 archivos de test importan
  `sqlite3` directo.

---

## Reglas duras (leader.md / CLAUDE.md)

- Todo código en `src/` lo escribe el subagente `implementer`; verifica el `reviewer`.
- No `.dict()` (usar `model_dump()`); no importar `src.infrastructure.db` fuera de
  infraestructura; repos solo vía `Container`.
- Pasos que tocan schema o `container.py` → puerta de aprobación de David.
- Ningún paso se declara `done` sin `python init.py` VERDE.

---

# ETAPA A — Backend sólido sobre NiceGUI

> No se toca el código de producción antes de tener la Fase 0 verde.

## Fase 0 — Completar funcionalidad NiceGUI

Objetivo: la app debe estar **completamente funcional** antes de tocar la
infraestructura de BD. Esto incluye los módulos pendientes (convivencia,
seguimiento, alertas, etc.) según sus roadmaps propios.

- *criterio_done*: toda la funcionalidad planificada implementada y verde.
- ⚠️ Esta fase ya tiene sus propios roadmaps (`specs/convivencia_00_roadmap`, etc.).
  No se duplica aquí. Este roadmap arranca operativamente en la **Fase 1**.

## Fase 1 — Red de seguridad y harness dual (3–6 días)

Objetivo: poder correr la suite de tests de repositorios contra SQLite **y**
Postgres, sin cambiar todavía el código de producción.

- **backend_01_test_taxonomy** 🕓 — Clasificar los 75 archivos de test en:
  (a) agnósticos de BD (servicios/dominio con `FakeRepository`) → no requieren nada;
  (b) tests de repositorio/integración que tocan BD. Marcar con markers pytest
  (`@pytest.mark.repo`) los que dependen del backend.
  - *criterio_done*: `pytest -m repo` selecciona solo los tests de BD; resto verde.
- **backend_02_conftest_parametrizado** 🕓 — Parametrizar `conftest.py` para que las
  fixtures de BD (`db_conn`, `db_seed`, `seed_result`) funcionen sobre un engine
  inyectable, no sobre `sqlite3.connect(":memory:")` hardcodeado. Aún solo SQLite.
  - *criterio_done*: suite verde con el nuevo conftest, sin `sqlite3` directo en fixtures.
- **backend_03_postgres_test_infra** 🕓 — Infra de Postgres para tests:
  `testcontainers-python` (contenedor efímero) o instancia local vía env var.
  Fixture que arranca Postgres y aplica el schema.
  - *criterio_done*: `pytest -m repo --backend=postgres` levanta Postgres y corre
    (puede fallar por dialecto — eso lo arregla la Fase 2).

## Fase 2 — SQLAlchemy Core y schema portable (1.5–2.5 semanas)

Objetivo: una sola definición de tablas que sirve a ambos dialectos; repos sobre
SQLAlchemy Core detrás de los mismos puertos.

- **backend_04_metadata_schema** 🕓 — Definir el schema como `MetaData`/`Table` de
  SQLAlchemy Core (fuente única), reemplazando los strings DDL de `schema.py`.
  Tipos neutros. *(toca schema → puerta de aprobación)*
  - *criterio_done*: `metadata.create_all()` genera schema equivalente en SQLite;
    tests de schema verdes.
- **backend_05_engine_factory** 🕓 — Factory de engine en `container.py` conmutable
  por config: `DB_BACKEND=sqlite` → `sqlite:///...`; `DB_BACKEND=postgres` →
  `postgresql+psycopg://...`. WAL/pragmas SQLite vía eventos SQLAlchemy.
  *(toca container → puerta de aprobación)*
  - *criterio_done*: la app arranca contra ambos backends según env var.
- **backend_06_queries_sqlalchemy** 🕓 — Reescribir `queries.py` (`fetch_df`,
  `fetch_one`, `fetch_all`, `get_scalar`, `execute`) sobre SQLAlchemy.
  - *criterio_done*: tests de repo verdes en SQLite con el nuevo `queries.py`.
- **backend_07_repos_migracion** 🕓 — Migrar repos a Core, **uno a uno**, manteniendo
  los puertos intactos. Resolver: `?`→params nombrados, `lastrowid`→
  `inserted_primary_key`, `INSERT OR REPLACE`→upsert, fechas→funciones neutras.
  Renombrar `sqlite_*` → `sqla_*`.
  - *criterio_done*: cada repo verde en **SQLite y Postgres**.
- **backend_08_recreacion_seed** 🕓 — Crear/recrear schema desde `create_all()` +
  seed en ambos backends.
  - *criterio_done*: `python init.py` verde en Postgres y SQLite.
- **backend_09_cierre_dual** 🕓 — Suite completa verde contra ambos backends.
  - *criterio_done*: 1.331 tests verdes en SQLite y Postgres.

## Fase 3 — API REST + autenticación (1–2 semanas)

Objetivo: exponer los servicios como API REST con contrato estable.

- **backend_10_fastapi_mount** 🕓 — Router FastAPI montado en NiceGUI. Estructura
  `src/interface/api/`.
  - *criterio_done*: `/api/health` + OpenAPI docs sirviendo junto a la UI.
- **backend_11_api_auth** 🕓 — Auth JWT independiente de la sesión NiceGUI. Reusa
  `AuthService` existente.
  - *criterio_done*: login emite token; middleware valida rol/tenant.
- **backend_12_endpoints_crud** 🕓 — Endpoints que reusan `Container.*_service`.
  Modelos Pydantic → serialización directa. Diseñar para **lotes offline** (recibir
  arrays de registros con timestamps para futura sincronización).
  - *criterio_done*: CRUD completo con tests de API; OpenAPI exportable.

## Fase 4 — Despliegue nube + tiempo real (1–2 semanas)

Objetivo: app desplegada en la nube con Postgres y canales de push.

- **backend_13_deploy_postgres** 🕓 — Despliegue de la app NiceGUI + Postgres en un
  proveedor cloud (Railway, Render, VPS, etc.). Config de producción, variables de
  entorno, seed de producción (`seed_base`).
  - *criterio_done*: app accesible desde internet con Postgres.
- **backend_14_event_bus** 🕓 — Bus de eventos interno: servicios emiten eventos de
  dominio sin conocer el transporte.
  - *criterio_done*: servicio publica evento; test verifica suscriptores.
- **backend_15_ws_endpoint** 🕓 — Endpoint WebSocket/SSE con auth y filtrado por
  tenant. Reenvía eventos del bus a clientes suscritos.
  - *criterio_done*: cliente recibe en vivo un evento emitido por un servicio.

## Fase 5 — Design system portable (3–5 días, paralelo desde Fase 2)

Objetivo: tokens y contratos en formato que Vue pueda consumir en la Etapa B.

- **backend_16_tokens_neutrales** 🕓 — Fuente canónica a JSON (estilo W3C Design
  Tokens). `sync_tokens.py` genera `tokens.css` + `tokens.py` **desde el JSON**.
  - *criterio_done*: `tokens.json` es la fuente; `test_tokens_sync` verifica derivados.
- **backend_17_contratos_componentes** 🕓 — Documentar los 18 componentes (variantes,
  props, estados, clases CSS) como spec independiente de NiceGUI.
  - *criterio_done*: `docs/design_system/components.md` cubre los 18 componentes.
- **backend_18_css_desacoplado** 🕓 — Auditar y aislar dependencias de Quasar en el
  CSS para que sea reutilizable fuera de NiceGUI.
  - *criterio_done*: informe de dependencias Quasar + CSS portable verificado.

---

# TRANSICIÓN — División de repositorios

> Ejecutar **entre la Fase 5 y la Fase 6**. Es el punto natural de corte:
> `tokens.json` ya existe como contrato compartido, la API está desplegada,
> y el código Vue necesita su propio ciclo de build.

## Fase 5.5 — División de repos (1–2 días)

- **backend_18b_split_repos** 🕓 — Dividir el monorepo en repositorios independientes:

  | Repo | Contenido | Ciclo de release |
  | --- | --- | --- |
  | `zeci-api` | Dominio, servicios, repos SQLAlchemy, API REST, auth JWT, event bus, NiceGUI (uso propio), seeds, tests Python | Deploy al servidor (Railway/VPS) |
  | `zeci-vue` | Componentes Vue, vistas, stores Pinia, PWA, `src-tauri/`, `capacitor.config.ts` | Build → 3 artefactos (PWA, .exe, APK) |
  | `zeci-tokens` (opcional) | `tokens.json` + scripts de generación (→ CSS, → TS, → Python) | Paquete consumido por los otros dos |

  - La app NiceGUI se queda en `zeci-api` (producto de uso propio + referencia funcional).
  - El contrato de la API es el OpenAPI spec generado por FastAPI (`/api/openapi.json`).
    `zeci-vue` lo consume en desarrollo; no necesita repo separado.
  - *criterio_done*: cada repo arranca, buildea y corre tests de forma independiente.
  - *pista*: `git filter-branch` o `git subtree split` para conservar historial,
    o simplemente copiar y empezar historial limpio (más simple para un dev solo).

---

# ETAPA B — Fork Vue (producto comercial)

> Prerrequisito: Etapa A completa + repos divididos.
> Todo el trabajo de la Etapa B ocurre en `zeci-vue`.
> `zeci-api` solo recibe cambios si la API necesita un endpoint nuevo.

## Fase 6 — Scaffolding Vue 3 + Vite (1–2 semanas)

- **backend_19_scaffold** 🕓 — Inicializar `zeci-vue` con `npm create vite@latest`
  template `vue-ts`. Instalar stack: Vue Router, Pinia, VueUse, Axios.
  `vite.config.ts` con alias y proxy a la API FastAPI en desarrollo.
  - *criterio_done*: `npm run dev` arranca; proxy a `/api` conecta con FastAPI.
- **backend_20_tokens_vue** 🕓 — Pipeline que consume `tokens.json` y genera
  variables CSS + constantes TypeScript. Tema claro/oscuro automático.
  - *criterio_done*: tokens Aula Serena disponibles como `var(--ink-700)` en Vue.
- **backend_21_libreria_componentes** 🕓 — Componentes Vue que implementan los
  contratos de Fase 5 sobre Naive UI o PrimeVue (evaluar cuál se personaliza
  mejor con los 187 tokens). Mismas variantes, mismos estados.
  - *criterio_done*: los 18 componentes portados y visibles en una página de catálogo.

## Fase 7 — Vistas Vue + motor de sincronización offline (4–8 semanas)

- **backend_22_vistas_core** 🕓 — Login (auth JWT), layout principal, navegación
  modular (menú que refleja módulos activados), selector de contexto
  (institución/periodo/grupo), dashboard por rol.
  - *criterio_done*: navegación completa funcionando contra la API REST.
- **backend_23_vistas_modulos** 🕓 — Módulos por orden de prioridad:
  1. Asistencia (el más crítico para offline).
  2. Convivencia (observaciones, comportamiento, seguimiento 360°).
  3. Evaluación (planilla de notas, cierre de periodo/año).
  4. Informes (boletines, consolidados).
  5. Configuración y admin.
- **backend_24_offline_engine** 🕓 — Motor de sincronización offline compartido
  por las tres plataformas (PWA, Tauri, Capacitor). Es el corazón de la Etapa B:

  **Componentes del motor:**
  1. **Store offline (Pinia + IndexedDB):**
     - `useOfflineStore()` — cola de operaciones pendientes.
     - Cada mutación (crear asistencia, registrar observación) se guarda localmente
       con timestamp + UUID + tenant_id.
     - IndexedDB vía `idb-keyval` o `Dexie.js`.
  2. **Detector de conectividad:**
     - `VueUse.useOnline()` para PWA/navegador.
     - `@capacitor/network` para Android.
     - Tauri: `navigator.onLine` + ping periódico al health endpoint.
  3. **Sync push (subir pendientes):**
     - Al detectar red: `POST /api/sync/push` con array de operaciones.
     - Reintentos con backoff exponencial si falla.
     - Marcar como sincronizado en IndexedDB al recibir 200.
  4. **Sync pull (bajar cambios):**
     - `GET /api/sync/pull?since=T` descarga cambios desde última sincronización.
     - Actualiza IndexedDB local + refresca stores Pinia reactivamente.
  5. **Resolución de conflictos:**
     - Asistencia: último timestamp gana (el profesor en el aula prevalece).
     - Observaciones: aditivas (cada una es un registro nuevo, sin conflicto).
     - Notas: último timestamp gana + notificación al otro editor.
     - Conflictos no resolubles: marcar para revisión manual.

  - *criterio_done*: profesor registra asistencia sin red; al reconectar se
    sincroniza y se refleja en el servidor.

  > Este motor se escribe **una vez** en `src/stores/sync/` y lo consumen
  > las tres plataformas. La única diferencia es el detector de conectividad.

## Fase 8 — PWA: app web instalable + offline (1 semana)

Objetivo: la app Vue funciona como Progressive Web App instalable desde el
navegador, con soporte offline completo.

- **backend_25_pwa_manifest** 🕓 — Configurar `vite-plugin-pwa`:
  - `manifest.json`: nombre, iconos (192px, 512px, maskable), colores Aula Serena,
    `display: standalone`, `start_url: /`, orientación portrait.
  - Splash screen para instalación en móvil.
  - *pista*: `npm install vite-plugin-pwa`, configurar en `vite.config.ts`.
- **backend_26_service_worker** 🕓 — Service Worker con estrategia de cache:
  - **App shell** (HTML/CSS/JS/fuentes): precache en install, siempre desde cache.
  - **API requests**: network-first con fallback a cache para GETs.
    Mutaciones (POST/PUT/DELETE) van a la cola offline del motor (Fase 7).
  - **Imágenes/assets**: cache-first con expiración.
  - *pista*: `vite-plugin-pwa` usa Workbox internamente. Configurar `runtimeCaching`
    con rutas `/api/*`.
- **backend_27_pwa_deploy** 🕓 — Desplegar la PWA en Vercel, Netlify, o servida
  por el mismo servidor de la API (FastAPI con `StaticFiles`).
  - *criterio_done*: app instalable desde Chrome/Edge; funciona offline;
    Lighthouse PWA audit ≥ 90.
  - *pista*: Vercel/Netlify gratis para sitios estáticos. Si se sirve desde
    FastAPI: `app.mount("/", StaticFiles(directory="dist"))`.

## Fase 9 — Tauri: app de escritorio WebView2 (1 semana)

Objetivo: `.exe` ligero (~3MB) para Windows que funciona con SQLite local
o conectado a la API en la nube.

- **backend_28_tauri_init** 🕓 — Inicializar Tauri v2 en el proyecto Vue:
  - `npm install @tauri-apps/cli @tauri-apps/api`.
  - `npx tauri init` → genera `src-tauri/` con `Cargo.toml` y `tauri.conf.json`.
  - Configurar ventana: título, tamaño mínimo, icono, sin menú de navegador.
  - *pista*: Tauri v2 requiere Rust instalado (`rustup`). El build descarga
    dependencias automáticamente.
- **backend_29_tauri_sqlite** 🕓 — Plugin `tauri-plugin-sql` para SQLite local:
  - Crear/abrir BD en `%APPDATA%/zeci/data.db`.
  - Al primer arranque: crear schema + `seed_base` (institución vacía lista
    para que el usuario configure).
  - El store Pinia detecta modo local (Tauri) vs. remoto (API) y redirige
    las queries al plugin SQLite o al endpoint REST según corresponda.
  - *pista*: `npm install @tauri-apps/plugin-sql`. Acceso via
    `import Database from '@tauri-apps/plugin-sql'`.
- **backend_30_tauri_config_dual** 🕓 — Pantalla de configuración al primer
  arranque: "¿Usar base de datos local o conectarse a un servidor?"
  - Local: SQLite, todo funciona sin internet.
  - Remoto: pide URL del servidor + credenciales, usa la API REST.
  - Guardar preferencia en `tauri-plugin-store` (persiste entre sesiones).
- **backend_31_tauri_build** 🕓 — Build del instalador Windows:
  - `npx tauri build` → genera `.exe` y `.msi`.
  - Firmado de código (opcional para distribución directa, requerido para
    evitar warnings de SmartScreen).
  - *criterio_done*: `.exe` de ~3MB que arranca en PC sin Python ni Node,
    funciona contra SQLite local.
  - *pista*: para evitar SmartScreen sin firma, distribuir como `.zip`
    con instrucciones. Firma con certificado de código ~$70/año (SignPath
    ofrece gratuito para open source).

## Fase 10 — Capacitor: app Android (2–4 semanas, posterior)

Objetivo: app Android nativa que funciona offline con SQLite local y
sincroniza con la API cuando hay red.

- **backend_32_capacitor_init** 🕓 — Inicializar Capacitor en el proyecto Vue:
  - `npx cap init "ZECI" "com.zeci.app"`.
  - `npx cap add android`.
  - Configurar `capacitor.config.ts`: `webDir: 'dist'`, server URL para dev.
  - *pista*: necesita Android Studio instalado. `npx cap open android` abre
    el proyecto.
- **backend_33_capacitor_plugins** 🕓 — Instalar y configurar plugins nativos:
  - `@capacitor-community/sqlite` — BD local en el dispositivo.
  - `@capacitor/network` — detectar online/offline (alimenta el motor de sync).
  - `@capacitor/push-notifications` — recibir notificaciones push (alertas de
    seguimiento, cambios de horario).
  - `@capacitor/splash-screen` — pantalla de carga con logo.
  - `@capacitor/status-bar` — estilo de barra de estado (colores Aula Serena).
  - *criterio_done*: `npx cap sync && npx cap run android` abre en emulador
    con todos los plugins funcionando.
- **backend_34_android_sqlite_sync** 🕓 — Conectar el motor de sincronización
  offline (backend_24) con el plugin SQLite de Capacitor:
  - Al primer arranque: crear schema + `seed_base` en SQLite del dispositivo.
  - El detector de conectividad usa `@capacitor/network` en lugar de
    `navigator.onLine`.
  - Push/pull idéntico al de la PWA pero contra SQLite local como almacenamiento
    en lugar de IndexedDB.
  - *criterio_done*: profesor registra asistencia offline en el teléfono;
    al conectarse a WiFi se sincroniza con el servidor.
- **backend_35_android_ux** 🕓 — Ajustes de UX específicos de Android:
  - Navegación por gestos (swipe back).
  - Teclado numérico para campos de notas.
  - Notificaciones push cuando llega una alerta de seguimiento.
  - Ícono adaptativo (foreground + background layers) y splash screen.
  - Permisos de Android (internet, almacenamiento, notificaciones).
  - *criterio_done*: la app se siente nativa, no como una web metida en un frame.
- **backend_36_android_release** 🕓 — Build de release y distribución:
  - `npx cap build android` → genera APK y AAB (Android App Bundle).
  - Firma con keystore de producción.
  - Publicación en Play Store (cuenta de dev $25 una vez) o distribución
    directa de APK (sideload).
  - *criterio_done*: APK instalable en un teléfono real; o publicada en Play Store.
  - *pista*: Play Store exige target API level actualizado, política de privacidad
    publicada, y clasificación de contenido. Preparar antes de subir.

---

## Estimación de esfuerzo total

| Fase | Enfocado | Calendario* |
| --- | --- | --- |
| **ETAPA A** | | |
| 0 — Completar NiceGUI | (tiene sus propios roadmaps) | |
| 1 — Harness dual | 3–6 días | 1–2 semanas |
| 2 — SQLAlchemy Core | 1.5–2.5 semanas | 3–5 semanas |
| 3 — API REST + auth | 1–2 semanas | 2–4 semanas |
| 4 — Deploy + tiempo real | 1–2 semanas | 2–3 semanas |
| 5 — Design system portable | 3–5 días | absorbido en paralelo |
| **Subtotal Etapa A** | **~5–8 semanas** | **~2.5–4 meses** |
| **TRANSICIÓN** | | |
| 5.5 — División de repos | 1–2 días | ~1 semana |
| **ETAPA B** | | |
| 6 — Scaffold Vue 3 + Vite | 1–2 semanas | 2–3 semanas |
| 7 — Vistas + motor offline | 4–8 semanas | 2–4 meses |
| 8 — PWA (web instalable + offline) | ~1 semana | 1–2 semanas |
| 9 — Tauri (escritorio WebView2) | ~1 semana | 1–2 semanas |
| **Subtotal Etapa B web+escritorio** | **~7–12 semanas** | **~3–5 meses** |
| 10 — Android (Capacitor) | 2–4 semanas | 1–2 meses |
| **TOTAL (A + B + Android)** | **~14–26 semanas** | **~7–12 meses** |

*Calendario = trabajo enfocado estirado por puertas de aprobación, trabajo en
paralelo con funcionalidad pendiente, y los imprevistos normales de desarrollo.

## Secuencia visual

```
ETAPA A (monorepo — NiceGUI + backend sólido)
══════════════════════════════════════════════════════════════

  [F0 App completa] → [F1 Tests] → [F2 SQLAlchemy] → [F3 API] → [F4 Deploy+RT]
                                          ↑
                                    [F5 Design system] (paralelo)

                                          ↓
                              ╔═══════════════════════╗
                              ║ F5.5 DIVIDIR REPOS    ║
                              ║ zeci-api / zeci-vue   ║
                              ╚═══════════════════════╝
                                          ↓

ETAPA B (zeci-vue — producto comercial, tres plataformas)
══════════════════════════════════════════════════════════════

  [F6 Scaffold Vue] → [F7 Vistas + motor offline] ──┬── [F8 PWA]
                                                     ├── [F9 Tauri .exe]
                                                     └── [F10 Capacitor Android]
                                                              ↓
                                                     Cuatro productos:
                                                     • PWA instalable (offline)
                                                     • Web en nube (navegador)
                                                     • .exe ~3MB (SQLite local)
                                                     • APK Android (SQLite + sync)
```
