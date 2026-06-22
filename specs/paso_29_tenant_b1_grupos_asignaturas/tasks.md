# paso_29 — Frente B1: institucion_id en grupos + asignaturas

## Contexto y decisión (David)

Primer sub-paso del frente B (particionar las tablas académicas por institución). Acotado a **`grupos`** y **`asignaturas`** — ambos los maneja `infraestructura_service` (un servicio/repo), ambos son catálogos con `UNIQUE` global que hay que volver **compuesto por institución** vía rebuild de tabla. Se construye sobre el mecanismo central del frente C (`institucion_actual()` de `src/services/contexto_tenant.py`).

`estudiantes` (B2), `asignaciones`+evaluación (B3), asistencia/convivencia (B3/B4), horarios/salas (B4) van en sub-pasos posteriores.

**Patrón de referencia OBLIGADO:** el rebuild idempotente de `configuracion_anio` de **paso_27** (en `schema.py`, migración que crea `_new`, `INSERT ... SELECT` preservando `id`, DROP+RENAME). Reutilízalo/espéjalo.

**CRÍTICO — preservar `id`:** `grupos(id)` es referenciado por FK desde `estudiantes`, `asignaciones`, `control_diario`, traslados, alertas, etc.; `asignaturas(id)` desde `asignaciones`, plan. El rebuild DEBE preservar los ids o se rompen todos esos FKs.

**Scope (frente C):** los servicios resuelven `institucion_id` desde `institucion_actual()` → `None` para admin (ve todo) / institución para director / objetivo en "Ver como". Sin sesión (seed/arranque) cae a `id_por_defecto()` (#1). Los repos siguen parametrizados (reciben `institucion_id`).

## Tareas

### [x] T1 — grupos: institucion_id + unicidad por institución + migración
- DDL BD nueva: `grupos` gana `institucion_id INTEGER REFERENCES instituciones(id)`; cambiar `codigo TEXT NOT NULL UNIQUE` → `codigo TEXT NOT NULL` + `UNIQUE(institucion_id, codigo)`. Índice por `institucion_id`. Preservar el resto (grado, jornada, capacidad_maxima, sala_id).
- Migración idempotente (solo si falta la columna, PRAGMA table_info): **rebuild** de `grupos` espejando paso_27, **copiando `id`** y poniendo `institucion_id = #1`. Manejo de `PRAGMA foreign_keys`. Backfill #1.

### [x] T2 — asignaturas: institucion_id + unicidad por institución + migración
- DDL BD nueva: `asignaturas` gana `institucion_id INTEGER REFERENCES instituciones(id)`; cambiar `nombre TEXT NOT NULL UNIQUE` → `nombre TEXT NOT NULL` + `UNIQUE(institucion_id, nombre)`; `codigo TEXT UNIQUE` → `codigo TEXT` + `UNIQUE(institucion_id, codigo)`. Preservar `area_id` + su FK a `areas_conocimiento` (las áreas siguen siendo catálogo global por ahora). Índice por `institucion_id`.
- Migración idempotente: rebuild de `asignaturas` preservando `id`, backfill #1.

### [x] T3 — Modelos + repo
- `Grupo` y `Asignatura` (`src/domain/models/infraestructura.py`) + sus DTOs ganan `institucion_id: int | None`.
- `sqlite_infraestructura_repo`: persiste/lee `institucion_id` en grupos y asignaturas; `listar_grupos(...)` y `listar_asignaturas(...)` aceptan y aplican `institucion_id` (cuando se pasa, `WHERE institucion_id = ?`); `crear_*`/`actualizar_*` lo manejan. Actualizar el port en consecuencia.

### [x] T4 — Servicio (scope desde el contextvar)
- `infraestructura_service.listar_grupos(...)` y `listar_asignaturas(...)`: resolver el scope con `institucion_actual()` (None → sin filtro, admin ve todo; institución → filtra) y pasarlo al repo. Mantener los filtros existentes (`grado`, `area_id`).
- `crear_grupo`/`crear_asignatura`: asignar `institucion_id` = `institucion_actual()` o, si None (seed/arranque), `id_por_defecto()`.
- `actualizar_*`: preservar la institución existente (no permitir moverla entre instituciones en este paso).

### [x] T5 — Seed + tests
- Seed: grupos y asignaturas sembrados → institución #1.
- Tests: `listar_grupos`/`listar_asignaturas` auto-scopean para director y NO filtran para admin (contextvar None); mismo `codigo` de grupo / mismo `nombre` de asignatura en DOS instituciones NO colisiona; la migración de una BD preexistente preserva ids y deja los FKs hijos (estudiantes/asignaciones/control_diario) intactos (`foreign_key_check` limpio).

### [x] T6 — Verificación y cierre
- `python init.py` VERDE (baseline 1092 passed, 1 skipped; corregir fallout — fakes/repos de tests de infraestructura deben contemplar institucion_id). check_imports domain/infrastructure/services/interface + check_design en verde.
- **Probar la migración a mano** sobre una BD preexistente con grupos/asignaturas + hijos (estudiantes/asignaciones): sin pérdida, ids preservados, FKs intactos. Documentar.
- `progress/impl_paso_29.md`.

## criterio_done
`grupos` y `asignaturas` tienen `institucion_id` con unicidad compuesta `(institucion_id, codigo/nombre)` y migración idempotente que preserva ids/FKs; `infraestructura_service` scopea los listados desde `institucion_actual()` (admin ve todo, director lo suyo) y asigna institución al crear; seed → #1; `python init.py` verde y BD preexistente migra sin pérdida ni FKs rotos. (estudiantes/asignaciones quedan para B2/B3.)
