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
7. **Fork del proyecto** → front Vue que consume la API ya probada.
   Tres productos del mismo fork:
   - **App web** (navegador, online-offline con PWA/Service Worker).
   - **App WebView2** (empaquetada para escritorio, con SQLite local).
   - **Versión navegador** (la misma PWA desplegada en la nube).
8. **App Android** — desarrollo posterior, consume la misma API REST.

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

# ETAPA B — Fork Vue (producto comercial)

> Prerrequisito: Etapa A completa (API desplegada, tiempo real funcionando,
> design system portable).

## Fase 6 — Fork y scaffolding Vue (1–2 semanas)

- **backend_19_fork_vue** 🕓 — Fork del repositorio. Scaffolding Vue 3 + Vite +
  TypeScript. Consumo de `tokens.json` para generar variables CSS/tokens TS.
  - *criterio_done*: proyecto Vue arranca, importa tokens, conecta a la API REST.
- **backend_20_libreria_componentes** 🕓 — Librería de componentes Vue que implementa
  los contratos documentados en Fase 5 (mismas variantes, mismos estados).
  - *criterio_done*: storybook o equivalente con los 18 componentes portados.

## Fase 7 — Migración de vistas a Vue (4–8 semanas)

- **backend_21_vistas_core** 🕓 — Vistas principales: login, dashboard, navegación,
  selector de contexto (institución/periodo/grupo).
- **backend_22_vistas_modulos** 🕓 — Módulos por orden de prioridad: asistencia,
  evaluación, convivencia, horarios, configuración.
- **backend_23_offline_sync** 🕓 — PWA con Service Worker. Cache de datos críticos en
  IndexedDB (asistencia, notas). Sincronización por lotes cuando hay red, usando los
  endpoints diseñados para lotes offline en Fase 3.
  - *criterio_done*: profesor registra asistencia sin red; al reconectar se sincroniza.

## Fase 8 — Empaquetado multiplataforma (1–2 semanas)

- **backend_24_pwa_deploy** 🕓 — PWA desplegada (app web de navegador). La misma PWA
  que funciona offline.
  - *criterio_done*: app instalable desde el navegador.
- **backend_25_webview2_exe** 🕓 — Empaquetado WebView2 para escritorio (Tauri, o
  electron-lite). Puede apuntar a SQLite local o a la nube.
  - *criterio_done*: `.exe` que carga la app Vue contra SQLite local.

## Fase 9 — App Android (posterior, no estimada)

- **backend_26_android** 🕓 — App nativa o híbrida (Capacitor/Kotlin). Consume la
  API REST + WS. SQLite local para offline + sincronización.
  - *Desarrollo separado, después de validar la Etapa B en producción.*

---

## Estimación de esfuerzo total

| Fase | Enfocado | Calendario* |
|---|---|---|
| **ETAPA A** | | |
| 0 — Completar NiceGUI | (tiene sus propios roadmaps) | |
| 1 — Harness dual | 3–6 días | 1–2 semanas |
| 2 — SQLAlchemy Core | 1.5–2.5 semanas | 3–5 semanas |
| 3 — API REST + auth | 1–2 semanas | 2–4 semanas |
| 4 — Deploy + tiempo real | 1–2 semanas | 2–3 semanas |
| 5 — Design system portable | 3–5 días | absorbido en paralelo |
| **Subtotal Etapa A** | **~5–8 semanas** | **~2.5–4 meses** |
| **ETAPA B** | | |
| 6 — Fork + scaffolding Vue | 1–2 semanas | 2–3 semanas |
| 7 — Vistas + offline | 4–8 semanas | 2–4 meses |
| 8 — Empaquetado multi | 1–2 semanas | 2–3 semanas |
| **Subtotal Etapa B** | **~6–12 semanas** | **~3–5 meses** |
| 9 — Android | por estimar | posterior |
| **TOTAL (A + B sin Android)** | **~11–20 semanas** | **~6–9 meses** |

*Calendario = trabajo enfocado estirado por puertas de aprobación, trabajo en
paralelo con funcionalidad pendiente, y los imprevistos normales de desarrollo.

## Secuencia visual

```
ETAPA A (NiceGUI + backend sólido)
══════════════════════════════════════════════════════════════

  [F0 App completa] → [F1 Tests] → [F2 SQLAlchemy] → [F3 API] → [F4 Deploy+RT]
                                          ↑
                                    [F5 Design system] (paralelo)

                                          ║ FORK
                                          ↓

ETAPA B (Vue — producto comercial)
══════════════════════════════════════════════════════════════

  [F6 Scaffold Vue] → [F7 Vistas + offline] → [F8 WebView2 + PWA]
                                                        ↓
                                               Tres productos:
                                               • App web (navegador)
                                               • App WebView2 (.exe)
                                               • PWA offline

                                                        ↓ (posterior)
                                               [F9 App Android]
```
