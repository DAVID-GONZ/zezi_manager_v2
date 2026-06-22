# paso_27 — Configuración académica por institución (frente A multi-tenant)

## Contexto y decisión (David)

Primer frente del multi-tenant real: la **configuración académica** (`configuracion_anio` = año académico activo + datos institucionales + reglas) pasa a ser **por institución**. Hoy es global (`anio UNIQUE`, `get_activa()` sin scope), así que dos instituciones no podrían tener su propio año/SIEE/branding.

Estructura actual relevante:
- `configuracion_anio` (id, **anio INTEGER UNIQUE**, fechas, nombre_institucion/logo/rector…, nota_minima, **activo**). `get_activa()` = `WHERE activo=1 LIMIT 1`.
- `niveles_desempeno`, `configuracion_periodos`, `criterios_promocion` referencian `configuracion_anio(id)` por `anio_id` → **heredan** la institución a través del año (NO necesitan `institucion_id` propio).
- `instituciones` ya existe (paso_24), institución #1 sembrada.

**Enfoque (incremental, compatible con single-tenant):** `get_activa(institucion_id=None)` con fallback a la institución por defecto (#1) cuando no se pasa, para no romper los muchos callers actuales. La cobertura total de callers llegará con el frente C (contextvar central de institución); aquí se cablean los callers con sesión.

**Fuera de alcance:** `institucion_id` en tablas académicas no-config (grupos/estudiantes/asignaciones/notas…) = frente B. Contextvar central de aislamiento = frente C.

## Tareas

### T1 — Schema + migración: institucion_id y unicidad por institución
- **DDL para BD nueva:** en `configuracion_anio`, cambiar `anio INTEGER UNIQUE NOT NULL` → `anio INTEGER NOT NULL`; añadir `institucion_id INTEGER REFERENCES instituciones(id)`; añadir `UNIQUE(institucion_id, anio)`. Índice por `institucion_id`.
- **Migración idempotente para BD existente** (CRÍTICO — hay FKs hijos `niveles_desempeno`/`configuracion_periodos`/`criterios_promocion` → `configuracion_anio(id)`): como la `UNIQUE(anio)` es de columna y SQLite no la puede quitar con ALTER, hacer **rebuild de tabla** SOLO si falta la columna `institucion_id` (PRAGMA table_info):
  1. crear `configuracion_anio_new` con el DDL nuevo,
  2. `INSERT INTO configuracion_anio_new (...) SELECT ..., <institucion_#1> FROM configuracion_anio` **copiando explícitamente `id`** (preservar ids para no romper los FKs hijos),
  3. `DROP TABLE configuracion_anio`, `ALTER TABLE configuracion_anio_new RENAME TO configuracion_anio`,
  4. recrear índices.
  Envolver con el manejo de `PRAGMA foreign_keys` apropiado. La migración debe ser **idempotente** (no re-ejecuta si la columna ya existe) e integrarse donde `init_db()` aplica migraciones.
- Backfill: todas las filas existentes → institución #1.

### T2 — Modelo + repo
- `ConfiguracionAnio` (+ `NuevaConfiguracionAnioDTO`/`ActualizarConfiguracionAnioDTO`) ganan `institucion_id: int | None`.
- `sqlite_configuracion_repo`:
  - `get_activa(institucion_id)` → `WHERE institucion_id=? AND activo=1`.
  - `get_por_anio(institucion_id, anio)`, `listar(institucion_id)` → scopeados.
  - `guardar(...)` persiste `institucion_id`.
  - `activar(anio_id)` → al activar un año, desactivar SOLO los de **su misma institución** (`UPDATE ... SET activo=0 WHERE activo=1 AND institucion_id = (SELECT institucion_id FROM configuracion_anio WHERE id=?)`), luego activar el indicado.
- Actualizar el port `IConfiguracionRepository` en consecuencia.

### T3 — Servicio
- `configuracion_service.get_activa(institucion_id: int | None = None)`: si `None`, resolver a `Container.institucion_service().id_por_defecto()` (#1) → compatible con callers sin sesión. Lanzar/loguear si no hay año activo.
- `crear_anio(dto)`: asignar `institucion_id` (del DTO; si falta, institución por defecto). La unicidad de `anio` ahora es por institución.
- `activar_anio(anio_id)`: usa el `activar` scopeado del repo.
- `get_by_id`, `get_info_institucional`, niveles/criterios siguen por `anio_id` (ya scopeados transitivamente). Mantener firmas salvo lo necesario.

### T4 — Callers con sesión + seed
- Cablear `ctx.institucion_id` en los callers de `get_activa()` que tienen sesión: `src/interface/pages/inicio.py`, `src/interface/design/layout.py` (`_get_logo_institucional`), `src/interface/pages/admin/configuracion_institucion.py`, `src/interface/pages/admin/configuracion_sie.py` y cualquier otra página con `ctx` disponible. Los callers sin sesión usan el default (#1). (La cobertura total llega con frente C.)
- Seed: el/los año(s) sembrados se asignan a la institución #1.

### T5 — Verificación y cierre
- `python init.py` VERDE (baseline 1074 passed, 1 skipped; corregir fallout — fakes/repos de tests de configuración deben contemplar `institucion_id`). check_imports domain/infrastructure/services/interface + check_design en verde.
- **Probar la migración a mano**: una BD de desarrollo preexistente (con `anio UNIQUE` y sin `institucion_id`) debe migrar **sin perder datos y con los FKs hijos intactos** (niveles/periodos/criterios siguen ligados a su año). Documentar cómo se probó.
- Tests: año activo por institución; crear dos años con el mismo número en distinta institución no colisiona; `activar` no desactiva años de otra institución.
- `progress/impl_paso_27.md`.

## criterio_done
`configuracion_anio` tiene `institucion_id` con unicidad `(institucion_id, anio)` y migración idempotente que preserva ids/FKs; `get_activa`/`activar`/`crear_anio` son por institución (con fallback a #1 para callers sin sesión); callers con sesión pasan `ctx.institucion_id`; seed asigna institución #1; `python init.py` verde y una BD preexistente migra sin pérdida ni FKs rotos.
