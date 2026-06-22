# paso_32 — Frente B4: asistencia, convivencia, horarios y salas por institución

## Contexto y decisión (David)

Último sub-paso del frente B. Mezcla **catálogos con `UNIQUE` global → rebuild** y **scope transitivo de agregados** que cruzan grupos. Se apoya en el mecanismo central del frente C (`institucion_actual()`).

Análisis del schema:
- **`salas`**: `nombre TEXT NOT NULL UNIQUE` global → necesita `institucion_id` + `UNIQUE(institucion_id, nombre)` (catálogo físico por institución). Referenciada por `grupos.sala_id`, escenarios/bloques → **rebuild preservando id**.
- **`plantillas_franja`**: `nombre TEXT NOT NULL UNIQUE` global → `institucion_id` + `UNIQUE(institucion_id, nombre)`. Referenciada por `franjas` → **rebuild preservando id**.
- **`control_diario`** (asistencia): `estudiante_id`+`grupo_id` (ya scopeados) → transitivo; solo scopear los **agregados que cruzan grupos** (consolidados de asistencia) por `institucion_actual()`.
- **Convivencia** (observaciones/seguimiento/comportamiento): `estudiante_id`/`grupo_id` (scopeados) → transitivo; scopear listados/agregados que crucen grupos.
- **`escenarios_horario`** (`anio_id` → scopeado en paso_27) y **`franjas`** (por `plantilla_id`) → transitivos.

**Patrón de referencia OBLIGADO para los rebuilds:** `_migrar_*_por_institucion` de paso_27/29/30 (crear `_new`, `INSERT ... SELECT` preservando `id`, DROP+RENAME, idempotente vía PRAGMA table_info, `foreign_keys OFF` durante + `foreign_key_check` al final). Backfill #1.

**Scope (frente C):** catálogos (salas/plantillas) → listados resuelven desde `institucion_actual()` (None → admin todo; institución → filtra), crear asigna institución (o #1 sin sesión). Agregados de asistencia/convivencia que cruzan grupos → filtrar por `institucion_actual()`. Repos parametrizados.

**Fuera de alcance:** username por institución + login (frente D).

## Tareas

### T1 — salas: institucion_id + unicidad por institución + migración
- DDL nueva: `salas` gana `institucion_id INTEGER REFERENCES instituciones(id)`; `nombre UNIQUE` → `UNIQUE(institucion_id, nombre)`. Índice por institución.
- Migración rebuild idempotente preservando `id` (FKs: `grupos.sala_id`, escenarios/bloques), backfill #1.
- Modelo `Sala` + DTOs ganan institucion_id; repo (en `infraestructura`/salas) persiste/lee y `listar_salas` aplica scope; crear asigna institución. Servicio resuelve desde `institucion_actual()`.

### T2 — plantillas_franja: institucion_id + unicidad por institución + migración
- DDL nueva: `plantillas_franja` gana `institucion_id INTEGER REFERENCES instituciones(id)`; `nombre UNIQUE` → `UNIQUE(institucion_id, nombre)`. 
- Migración rebuild idempotente preservando `id` (FK: `franjas.plantilla_id`), backfill #1.
- Modelo/DTO + repo + servicio (el que liste plantillas) scopean desde `institucion_actual()`; crear asigna institución.

### T3 — Asistencia (control_diario): scope de agregados
- `asistencia_service`: los listados/agregados que cruzan grupos (consolidados de asistencia, conteos institucionales) filtran por `institucion_actual()` (join a `grupos`). Los flujos sobre UN grupo/UN estudiante ya scopeado no cambian.

### T4 — Convivencia: scope de agregados
- `convivencia_service`: listados/agregados que crucen grupos filtran por `institucion_actual()`. Los flujos por estudiante/grupo ya scopeado no cambian.

### T5 — Horarios: auditoría de scope
- Revisar `horario_service`/`generador_horario_service`/`preparacion_horario_service` por listas que crucen instituciones sin padre scopeado. `escenarios_horario` (anio_id) y `franjas` (plantilla_id) deben quedar transitivamente scopeados; reforzar con `institucion_actual()` solo si alguna consulta lista a través de instituciones. Documentar lo auditado.

### T6 — Seed + tests + verificación
- Seed: salas y plantillas → institución #1.
- Tests: mismo `nombre` de sala/plantilla en DOS instituciones no colisiona; listados de salas/plantillas y agregados de asistencia/convivencia de la institución A no incluyen B (director); admin ve todo; migraciones preservan ids/FKs (`foreign_key_check` limpio), idempotentes.
- `python init.py` VERDE (baseline 1121 passed, 1 skipped; corregir fallout). check_imports + check_design en verde. Regla de capas intacta.
- **Probar migraciones a mano** sobre BD preexistente (salas con grupos que las referencian; plantillas con franjas): ids preservados, FKs intactos. Documentar.
- `progress/impl_paso_32.md`.

## criterio_done
`salas` y `plantillas_franja` con `institucion_id` + unicidad compuesta y migración idempotente que preserva ids/FKs; sus servicios scopean desde `institucion_actual()` y asignan institución al crear; agregados de asistencia y convivencia que cruzan grupos filtran por institución; horarios auditados (scope transitivo confirmado o reforzado); seed → #1; `python init.py` verde y BD preexistente migra sin pérdida ni FKs rotos. Con esto el frente B queda completo (queda D: username por institución).
