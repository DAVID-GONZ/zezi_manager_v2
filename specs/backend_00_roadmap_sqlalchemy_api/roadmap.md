# backend_00 — Roadmap: doble backend (SQLAlchemy), API REST y preparación de front

## Contexto y decisión (David, 2026-07-26)

David está evolucionando ZECI Manager hacia una arquitectura cliente-servidor desacoplada,
manteniendo el frontend NiceGUI actual **sin migrarlo aún**. Objetivos confirmados:

1. **Doble backend permanente** (no una migración de una sola vez):
   - **SQLite** → uso local en su PC, empaquetado `.exe` / WebView2 (single-user).
   - **PostgreSQL** → despliegue en la nube (multiusuario, concurrente).
   - Se elige por configuración según el caso de uso; ambos conviven de por vida.
2. **Backend sólido** para, en el futuro, conectar una **app Android** vía API REST.
3. **Frontend NiceGUI se mantiene**; migrar a Vue/React queda como opción abierta,
   **no como fase planificada**. Se decidirá solo si aparece un dolor concreto.
   Aun así, se preparan los cimientos del design system para no cerrarse la puerta.
4. **Camino técnico elegido: SQLAlchemy Core** (no SQL crudo duplicado), porque hay
   que mantener DOS dialectos de por vida y la librería absorbe esa diferencia.
5. **Todo este trabajo se hace en modo desarrollo.** No hay datos de producción.
   La BD se **recrea desde cero con el seed** (`seed_dev`/`seed_test`) cuantas veces
   haga falta. Por tanto **no existe migración de datos** en este roadmap: cambiar de
   backend = arrancar Postgres vacío y sembrarlo, igual que hoy con SQLite. Las
   "migraciones" que aparecen son de **código** (reescribir repos a SQLAlchemy), no de datos.

## Estado actual (revisión de 2026-07-26)

### Lo que juega a favor
- **Arquitectura hexagonal real**: `src/domain/ports/*_repo.py` (interfaces) +
  `src/infrastructure/db/repositories/sqlite_*` (adaptadores). Servicios y UI nunca
  tocan SQLite directo. `container.py` es el único punto de cableado.
- **Repos aceptan inyección de conexión** (`__init__(self, conn=None)`) → la costura
  para conmutar backend ya existe.
- **1.331 funciones de test** en 75 archivos. Los tests de **servicios y dominio usan
  `FakeRepository`** (sin BD) → son agnósticos del backend y migran sin coste.
- **Design system con fuente única**: `tokens.css` (187 variables) ↔ `tokens.py`
  sincronizados por `scripts/sync_tokens.py`. CSS separado en 24 archivos por componente/dominio.

### Lo que cuesta (deuda de acoplamiento a SQLite)
- **Schema como strings DDL de SQLite** en `schema.py` (56 `AUTOINCREMENT`, tipos laxos,
  `BOOLEAN DEFAULT 1`, etc.). No portable a Postgres tal cual.
- **SQL crudo pegado al dialecto** en repos: ~624 placeholders `?` (Postgres usa `%s`),
  ~105 `last_insert_rowid`/`lastrowid` (Postgres necesita `RETURNING`),
  9 `INSERT OR REPLACE/IGNORE` (Postgres `ON CONFLICT`), ~41 funciones de fecha SQLite.
- **Harness de tests 100% acoplado a SQLite**: `conftest.py` hace
  `sqlite3.connect(":memory:")`, aplica DDL cruda y usa `sqlite3.Row`. 8 archivos de test
  importan `sqlite3` directo. **Este es el bloqueante principal de la Fase 0.**
- **Componentes del design system** son fábricas Python sobre NiceGUI/Quasar
  (`ui.button` + clases `.btn-primary`). Tokens y CSS son portables; las fábricas no.

## Reglas duras aplicables (leader.md / CLAUDE.md)
- Todo código en `src/` lo escribe el subagente `implementer`; verifica el `reviewer`.
- No `.dict()` (usar `model_dump()`); no importar `src.infrastructure.db` fuera de
  infraestructura; repos solo vía `Container`.
- Pasos que tocan schema o `container.py` → **puerta de aprobación explícita de David**
  antes de lanzar el implementer.
- Ningún paso se declara `done` sin `python init.py` VERDE.

---

## Principio rector de la secuencia

> **No se toca el código de producción antes de tener la Fase 0 verde.**
> Sin un harness que corra los mismos tests contra SQLite *y* Postgres, cualquier
> estimación de las fases siguientes se duplica cazando regresiones a mano.
> (Recordatorio: al ser modo desarrollo, "verde en Postgres" significa *schema creado
> desde cero + seed + tests pasan*, no migrar datos existentes.)

Las fases 1–4 son la columna vertebral (backend sólido + API). La Fase 5 (design system)
corre **en paralelo y no bloquea** nada. La migración de front a Vue/React NO está en este
roadmap: es una decisión futura que este trabajo habilita, no exige.

---

## Fase 0 — Red de seguridad y harness dual

Objetivo: poder correr la suite de tests de repositorios contra SQLite **y** Postgres,
sin cambiar todavía el código de producción.

- **backend_01_test_taxonomy** 🕓 — Clasificar los 75 archivos de test en:
  (a) agnósticos de BD (servicios/dominio con `FakeRepository`) → no requieren nada;
  (b) tests de repositorio/integración que tocan `conftest`. Marcar con markers pytest
  (`@pytest.mark.repo`) los que dependen del backend.
  - *criterio_done*: `pytest -m repo` selecciona solo los tests de BD; resto sigue verde.
- **backend_02_conftest_parametrizado** 🕓 — Parametrizar `conftest.py` para que las
  fixtures de BD (`db_conn`, `db_seed`, `seed_result`) funcionen sobre un engine
  inyectable, no sobre `sqlite3.connect(":memory:")` hardcodeado. Aún solo SQLite.
  - *criterio_done*: toda la suite verde con el nuevo conftest, sin `sqlite3` directo en fixtures.
- **backend_03_postgres_test_infra** 🕓 — Infra de Postgres para tests:
  `testcontainers-python` (contenedor efímero) o instancia local vía env var.
  Fixture que arranca Postgres y aplica el schema. *(depende de que exista schema portable
  — se cierra realmente al final de la Fase 1)*.
  - *criterio_done*: `pytest -m repo --backend=postgres` levanta Postgres y corre (aunque
    inicialmente falle por dialecto — eso es lo que arregla la Fase 1).

## Fase 1 — Capa SQLAlchemy Core y schema portable

Objetivo: una sola definición de tablas que sirve a ambos dialectos; repos sobre
SQLAlchemy Core detrás de los mismos puertos.

- **backend_04_metadata_schema** 🕓 — Definir el schema como `MetaData`/`Table` de
  SQLAlchemy Core (fuente única), reemplazando los strings DDL de `schema.py`.
  Tipos neutros (`Integer` autoincrement, `Boolean`, `Date`, etc.). *(toca schema → puerta de aprobación)*
  - *criterio_done*: `metadata.create_all()` genera el schema equivalente en SQLite; tests de schema verdes.
- **backend_05_engine_factory** 🕓 — Factory de engine en `container.py` conmutable por
  config: `DB_BACKEND=sqlite` → `sqlite:///...`; `DB_BACKEND=postgres` → `postgresql+psycopg://...`.
  WAL/pragmas SQLite aplicados vía eventos SQLAlchemy. *(toca container → puerta de aprobación)*
  - *criterio_done*: la app arranca contra ambos backends según env var.
- **backend_06_queries_sqlalchemy** 🕓 — Reescribir `queries.py` (`fetch_df`, `fetch_one`,
  `fetch_all`, `get_scalar`, `execute`) sobre conexiones/Core de SQLAlchemy.
  `fetch_df` → `pd.read_sql` con el engine SQLAlchemy.
  - *criterio_done*: tests de repo verdes en SQLite con el nuevo `queries.py`.
- **backend_07_repos_migracion** 🕓 — Migrar repos a Core, **uno a uno**, manteniendo los
  puertos intactos. Resolver por repo: `?`→parámetros nombrados, `last_insert_rowid`→
  `RETURNING`/`inserted_primary_key`, `INSERT OR REPLACE`→upsert dialect-aware,
  fechas SQLite→funciones neutras. Renombrar `sqlite_*` → adaptador único o `sqla_*`.
  - *criterio_done*: cada repo verde en **SQLite y Postgres** (`pytest -m repo` en ambos).
- **backend_08_recreacion_seed** 🕓 — En desarrollo, crear/recrear el schema desde el
  `MetaData` de SQLAlchemy (`create_all()`) y sembrar con `seed_dev`/`seed_base`, para
  **ambos** backends. Sin versionado de migraciones (no hay datos que preservar).
  - *criterio_done*: `python init.py` crea schema + seed en Postgres vacío igual que en SQLite.
- **backend_09_cierre_dual** 🕓 — Cerrar Fase 0: CI/local corre la suite completa contra
  ambos backends. Documentar en `docs/`.
  - *criterio_done*: suite 100% verde en SQLite y Postgres.

> **Alembic queda FUERA de este roadmap.** El versionado de migraciones de schema solo
> aporta valor cuando existe una BD de producción con datos que no se pueden borrar. Al
> trabajar en desarrollo, la BD se recrea desde `create_all()` + seed. Alembic se
> introduciría **más adelante, como paso previo al primer despliegue real en la nube** —
> no ahora.

## Fase 2 — Empaquetado escritorio (.exe / WebView2)

Objetivo: distribuir la versión SQLite como app de escritorio.

- **backend_10_nicegui_native** 🕓 — Modo `native` de NiceGUI (pywebview → WebView2 en
  Windows). Config de arranque para escritorio vs. servidor.
  - *criterio_done*: la app abre en ventana nativa contra SQLite local.
- **backend_11_build_exe** 🕓 — Empaquetado con PyInstaller (o el recomendado por NiceGUI).
  Ruta de datos de usuario (`%APPDATA%`) para la BD SQLite.
  - *criterio_done*: `.exe` que arranca en una PC limpia sin Python.

## Fase 3 — API REST + autenticación

Objetivo: exponer los servicios existentes como API, contrato estable para Android.

- **backend_12_fastapi_mount** 🕓 — Router FastAPI montado en el mismo proceso NiceGUI
  (NiceGUI ya corre sobre FastAPI/Starlette). Estructura `src/interface/api/`.
  - *criterio_done*: `/api/health` y OpenAPI docs sirviendo junto a la UI NiceGUI.
- **backend_13_api_auth** 🕓 — Autenticación para API (JWT o API keys), independiente de
  la sesión NiceGUI (`route_guard.py`). Reusa `AuthService` existente.
  - *criterio_done*: endpoint de login emite token; middleware valida y resuelve rol/tenant.
- **backend_14_endpoints_crud** 🕓 — Endpoints REST que reusan `Container.*_service`
  (los modelos de dominio ya son Pydantic → serialización directa). Por módulos.
  - *criterio_done*: CRUD de al menos un módulo completo con tests de API; OpenAPI exportable
    como contrato para el cliente Android.

## Fase 4 — Canal de tiempo real (WS/SSE)

Objetivo: push servidor→cliente para móvil y para una futura web reactiva sin NiceGUI.

- **backend_15_event_bus** 🕓 — Bus de eventos interno: los servicios emiten eventos de
  dominio (alerta creada, asistencia registrada) sin conocer el transporte.
  - *criterio_done*: servicio publica evento; test verifica suscriptores.
- **backend_16_ws_endpoint** 🕓 — Endpoint FastAPI WebSocket (o SSE si solo es push) que
  reenvía eventos del bus a clientes suscritos, con auth y filtrado por tenant.
  - *criterio_done*: cliente recibe en vivo un evento emitido por un servicio.

## Fase 5 — Preparación del design system para Vue/React (paralelo, no bloqueante)

Objetivo: dejar los tokens y contratos de componentes en un formato que un futuro front
JS pueda consumir, **sin migrar nada aún**. Corre en paralelo a las fases anteriores.

- **backend_17_tokens_neutrales** 🕓 — Elevar la fuente canónica de tokens a un formato
  neutral (JSON, estilo W3C Design Tokens). `scripts/sync_tokens.py` pasa a **generar**
  `tokens.css` y `tokens.py` **desde el JSON** (no al revés). Los 187 valores ya existen.
  - *criterio_done*: `tokens.json` es la fuente; `test_tokens_sync` verifica CSS+PY derivados.
- **backend_18_contratos_componentes** 🕓 — Documentar cada uno de los 18 componentes
  (variantes, props, estados, clases CSS) en un spec **independiente de NiceGUI**, como
  contrato reutilizable por cualquier front.
  - *criterio_done*: `docs/design_system/components.md` cubre los 18 componentes.
- **backend_19_css_desacoplado** 🕓 — Auditar que las clases (`.btn-primary`, etc.) no
  dependan de internals de Quasar; aislar dependencias para que el CSS sea reutilizable
  fuera de NiceGUI.
  - *criterio_done*: informe de dependencias Quasar y CSS portable verificado.
- **backend_20_libreria_front** 🕓 *(FUTURO, solo si se decide migrar)* — Librería de
  componentes Vue/React que consume `tokens.json` + el CSS portable. **No se ejecuta**
  hasta que exista una decisión explícita de migrar el front.

---

## Estimación de esfuerzo

Asume el flujo actual (David + Claude Code, leader/implementer/reviewer, con puertas de
aprobación). "Enfocado" = tiempo de trabajo neto; "Calendario" = estirado por aprobaciones
y trabajo en paralelo.

| Fase | Enfocado | Calendario |
|---|---|---|
| 0 — Harness dual | 3–6 días | 1–2 semanas |
| 1 — SQLAlchemy + schema portable | 1.5–2.5 semanas | 3–5 semanas |
| 2 — Empaquetado .exe | 2–4 días | ~1 semana |
| 3 — API REST + auth | 1–2 semanas | 2–4 semanas |
| 4 — Tiempo real (WS/SSE) | 4–7 días | 1.5–3 semanas |
| 5 — Design system (paralelo) | 3–5 días | absorbido |
| **Total fases 0–5** | **~5–8 semanas** | **~2.5–4 meses** |
| (Futuro) migración a Vue/React | 6–12 semanas | 3–6 meses |

**Factores que más mueven la aguja**: (1) cuánto de los 1.331 tests resulta ser agnóstico
de BD (cuanto más, más barata la Fase 0); (2) alcance de la auth de API; (3) upserts y
fechas por repo en la Fase 1.

## Orden recomendado de arranque
1. **Fase 0 completa** antes de tocar producción.
2. **Fase 1** (el corazón del doble backend).
3. A partir de ahí, **Fases 2, 3 y 5 pueden solaparse**; la 4 tras la 3.
4. La migración de front **no se agenda**: se reevalúa cuando la API esté madura y en uso
   por el cliente Android.
