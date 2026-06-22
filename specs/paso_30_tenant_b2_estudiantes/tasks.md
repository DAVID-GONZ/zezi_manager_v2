# paso_30 — Frente B2: institucion_id en estudiantes

## Contexto y decisión (David)

Segundo sub-paso del frente B. `estudiantes` gana `institucion_id` con unicidad de documento **por institución**, scopeado vía el mecanismo central del frente C (`institucion_actual()`). Owner: `estudiante_service` / `sqlite_estudiante_repo`.

**Patrón de referencia OBLIGADO:** el rebuild idempotente de paso_27/paso_29 (`_migrar_*_por_institucion` en `schema.py`: crear `_new`, `INSERT ... SELECT` preservando `id`, DROP+RENAME, idempotente vía PRAGMA table_info, manejo de `PRAGMA foreign_keys`).

**CRÍTICO — preservar `id`:** `estudiantes(id)` lo referencian por FK **19 tablas hijas** (notas, control_diario/asistencia, convivencia, observaciones, alertas, planes, traslados, acudientes…). Si el rebuild no preserva ids, se rompen TODOS esos FKs. Desactivar `PRAGMA foreign_keys` durante el rebuild y verificar con `foreign_key_check` al final.

**Scope (frente C):** listados resuelven desde `institucion_actual()` (None → admin ve todo, NO caer a #1 en listados; institución → filtra). Crear/importar asignan `institucion_id = institucion_actual()` o, sin sesión (seed/arranque), `id_por_defecto()` (#1). Repos parametrizados.

**Fuera de alcance:** asignaciones/evaluación (B3), asistencia/convivencia/horarios/salas (B3/B4). Aquí solo `estudiantes`.

## Tareas

> Estado: T1–T5 implementadas y verificadas (init.py verde: 1115 passed, 1 skipped).
> Detalle en `progress/impl_paso_30.md`. NO marcar el paso `done` hasta confirmación de David.

### T1 — [x] estudiantes: institucion_id + unicidad de documento por institución + migración
- DDL BD nueva: `estudiantes` gana `institucion_id INTEGER REFERENCES instituciones(id)`; cambiar `numero_documento TEXT NOT NULL UNIQUE` → `numero_documento TEXT NOT NULL` + `UNIQUE(institucion_id, numero_documento)`. **`id_publico` se mantiene `UNIQUE` global** (es un identificador público surrogate, sin colisión de tenant). Preservar el resto de columnas y el FK `grupo_id → grupos(id)`. Índice por `institucion_id`.
- Migración idempotente: rebuild de `estudiantes` espejando paso_29, **copiando `id`**, `institucion_id = #1`, con manejo de `PRAGMA foreign_keys` y `foreign_key_check` final. Backfill #1.

### T2 — [x] Modelo + repo
- `Estudiante` (`src/domain/models/estudiante.py`) + DTOs (incl. `FiltroEstudiantesDTO`) ganan `institucion_id: int | None`.
- `sqlite_estudiante_repo`: persiste/lee `institucion_id`; `listar_filtrado`/`listar_por_grupo`/`listar_resumenes`/`listar_resumenes_plano` aceptan y aplican `institucion_id` (`WHERE e.institucion_id = ?` cuando se pasa); `crear`/`importar` lo manejan. Actualizar el port.

### T3 — [x] Servicio (scope desde el contextvar)
- `estudiante_service`: los listados resuelven el scope con `institucion_actual()` (None → sin filtro para admin; institución → filtra). NO caer a #1 en listados.
- Crear estudiante e importación masiva (CSV) asignan `institucion_id` = `institucion_actual()` o, si None, `id_por_defecto()`. Mantener validaciones existentes.
- `actualizar_*`: preservar la institución (no mover de tenant).

### T4 — [x] Seed + tests
- Seed: estudiantes sembrados → institución #1.
- Tests: listados auto-scopean (director sí, admin no); mismo `numero_documento` en DOS instituciones NO colisiona; migración de BD preexistente preserva ids y deja los FKs hijos (notas/control_diario/convivencia/…) intactos (`foreign_key_check` limpio); idempotente.

### T5 — [x] Verificación y cierre
- `python init.py` VERDE (baseline 1103 passed, 1 skipped; corregir fallout — fakes/repos de tests de estudiantes deben contemplar institucion_id). check_imports + check_design en verde.
- **Probar la migración a mano** sobre BD preexistente con estudiantes + hijos: sin pérdida, ids preservados, FKs intactos. Documentar.
- `progress/impl_paso_30.md`.

## criterio_done
`estudiantes` tiene `institucion_id` con `UNIQUE(institucion_id, numero_documento)` (id_publico sigue global) y migración idempotente que preserva ids/FKs de las 19 hijas; `estudiante_service` scopea listados desde `institucion_actual()` (admin todo, director lo suyo) y asigna institución al crear/importar; seed → #1; `python init.py` verde y BD preexistente migra sin pérdida ni FKs rotos.
