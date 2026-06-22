# paso_31 — Frente B3: scope por institución en asignaciones, cierres y estadísticos

## Contexto y decisión (David)

Tercer sub-paso del frente B. **Sin migraciones ni columnas nuevas:** las tablas de evaluación no tienen `UNIQUE` global problemático y todo cuelga transitivamente de entidades ya scopeadas (`asignaciones→grupos` [B1], `notas→estudiantes` [B2] / `actividades→categorias→asignacion_id`/`anio_id` [paso_27]). B3 es un **pase de scope en la capa de servicios**: filtrar por institución las consultas que **cruzan varios grupos** (donde sí puede haber fuga entre instituciones), usando `institucion_actual()` (frente C) + los joins existentes a `grupos`/`configuracion_anio`.

Las consultas que ya operan sobre una entidad concreta y ya scopeada (planilla/notas de UNA asignación, de UN grupo) NO necesitan cambio: heredan el scope del padre.

**Fuera de alcance:** asistencia (`control_diario`), convivencia/observaciones, horarios/salas = B4. username por institución = D.

## Tareas

### T1 — Asignaciones scopeadas por institución
- `FiltroAsignacionesDTO` gana `institucion_id: int | None`.
- `sqlite_asignacion_repo`: las listas (`listar`, `listar_info`, `listar_por_grupo`, `listar_por_docente`) aplican el scope por institución vía el **join a `grupos`** (`g.institucion_id = ?`) cuando se pasa `institucion_id`. Para `listar()` (que hoy es `SELECT * FROM asignaciones`), scopear con subconsulta/join a `grupos`. Actualizar el port.
- `asignacion_service`: los listados resuelven el scope desde `institucion_actual()` (None → admin ve todo; institución → filtra). Mantener filtros existentes (periodo, grupo, docente).

### T2 — Cierres institucionales scopeados
- `cierre_service`: los agregados que cruzan grupos/asignaciones — `estado_cierres_por_asignaciones`, `resumen_cierres_institucional` (y similares) — deben filtrar por `institucion_actual()` (join a `grupos`/`configuracion_anio`). Un director NO debe ver el estado de cierres de otra institución.

### T3 — Estadísticos institucionales scopeados
- `estadisticos_service`: `metricas_institucionales`, `ranking_grupo`, `estudiantes_en_riesgo_academico` y cualquier agregado que recorra **todos los grupos** de un periodo deben filtrar por `institucion_actual()`. (Esto corrige el dashboard de directivo en multi-tenant: hoy agregaría grupos de otras instituciones.)

### T4 — Auditoría de evaluación + categorías
- Revisar `evaluacion_service` (y plan_mejoramiento/nivelación/habilitación) por consultas que **listen a través de instituciones** sin pasar por un padre scopeado (p.ej. categorías institucionales por `anio_id`). Confirmar que quedan scopeadas transitivamente (el `anio` ya es por institución desde paso_27) o añadir el filtro por `institucion_actual()` donde haga falta. Documentar lo auditado.

### T5 — Tests + verificación
- Tests de aislamiento: con dos instituciones, `asignacion_service` listados, `cierre_service` agregados institucionales y `estadisticos_service.metricas_institucionales` de la institución A **no** incluyen datos de la B; con sesión admin (contextvar None) se ve todo / se filtra explícito.
- `python init.py` VERDE (baseline 1115 passed, 1 skipped; corregir fallout). check_imports + check_design en verde. Regla de capas intacta (repos no importan de services).
- `progress/impl_paso_31.md`.

## criterio_done
Las consultas que cruzan grupos (asignaciones, cierres institucionales, estadísticos institucionales) filtran por `institucion_actual()` → un director solo ve lo de su institución y el admin ve todo; evaluación auditada (scope transitivo confirmado o reforzado); sin migraciones; `python init.py` verde.
