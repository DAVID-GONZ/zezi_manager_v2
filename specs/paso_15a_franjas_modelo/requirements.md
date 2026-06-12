# paso_15a_franjas_modelo — requirements

Primer paso del épico **generador de horarios** (paso_15). Introduce la
**rejilla de franjas horarias fija** que hoy no existe: `horarios.hora_inicio/fin`
son texto libre, lo que hace imposible un solver. Este paso crea el modelo de
datos, los DTOs de dominio, el CRUD y el seed de una plantilla por defecto.

NO incluye el motor de generación (paso_15c) ni la vista de parrilla (paso_15e).
Solo la infraestructura de franjas. Decisión de diseño confirmada por David:
**rejilla fija** (todas las franjas de una jornada con sus horas definidas; cada
bloque ocupa exactamente una franja).

Notación EARS. Fuente de verdad: `src/infrastructure/db/schema.py`,
`src/domain/models/infraestructura.py`,
`src/domain/ports/infraestructura_repo.py`,
`src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`,
`src/services/infraestructura_service.py`, `src/infrastructure/db/seed.py`.

## Plantillas de franja

- **R1** — El sistema DEBERÁ persistir **plantillas de franja** en una tabla
  `plantillas_franja` con: `id`, `nombre` (único, no vacío), `jornada`
  (`AM` | `PM` | `UNICA`, coherente con `grupos.jornada`), `dias_activos`
  (texto CSV con subconjunto de `Lunes..Sábado`), `activa` (bool) y `created_at`.
- **R2** — El sistema DEBERÁ garantizar que **a lo sumo una** plantilla esté
  `activa` por `jornada` (índice único parcial `WHERE activa = 1`), al estilo del
  índice `idx_escenario_activo_unico` ya existente.

## Franjas

- **R3** — El sistema DEBERÁ persistir las **franjas** de una plantilla en una
  tabla `franjas` con: `id`, `plantilla_id` (FK ON DELETE CASCADE), `orden`
  (entero ≥ 1), `hora_inicio`, `hora_fin` (`hora_inicio < hora_fin`), `tipo`
  (`lectiva` | `descanso` | `almuerzo`) y `etiqueta` (texto opcional, p.ej.
  "Recreo").
- **R4** — El sistema DEBERÁ imponer unicidad de `orden` dentro de una plantilla
  (`UNIQUE(plantilla_id, orden)`), de modo que la rejilla sea determinista.
- **R5** — Las franjas con `tipo` distinto de `lectiva` (recreo, almuerzo)
  DEBERÁN poder existir en la rejilla pero quedar marcadas como **no lectivas**,
  para que pasos posteriores (generador) nunca coloquen clases en ellas.

## Dominio (modelos y DTOs)

- **R6** — El sistema DEBERÁ exponer modelos Pydantic `PlantillaFranja` y `Franja`
  en `src/domain/models/infraestructura.py`, con validación: `nombre` no vacío
  (strip), `jornada` y `tipo` restringidos a sus valores, `orden ≥ 1`,
  `hora_inicio < hora_fin`. Validar `dias_activos` como lista de días válidos.
- **R7** — El sistema DEBERÁ exponer DTOs de creación `NuevaPlantillaFranjaDTO` y
  `NuevaFranjaDTO` con sus métodos `to_modelo()`, siguiendo el patrón de
  `NuevoEscenarioDTO`/`NuevoHorarioDTO`. `__all__` DEBERÁ actualizarse.

## Puerto y repositorio

- **R8** — `IInfraestructuraRepository` DEBERÁ declarar el CRUD de plantillas y
  franjas: `crear_plantilla_franja`, `get_plantilla_franja`,
  `listar_plantillas_franja`, `get_plantilla_activa(jornada)`,
  `actualizar_plantilla_franja`, `activar_plantilla_franja`,
  `eliminar_plantilla_franja`; y para franjas: `crear_franja`,
  `listar_franjas(plantilla_id)`, `actualizar_franja`, `eliminar_franja`,
  `reemplazar_franjas(plantilla_id, franjas)` (reemplazo atómico del set).
- **R9** — `SqliteInfraestructuraRepository` DEBERÁ implementar esos métodos.
  `activar_plantilla_franja` DEBERÁ usar una transacción que ponga `activa=0` a
  las demás plantillas de la misma jornada y `activa=1` a la objetivo (mismo
  patrón que `activar_escenario`). `reemplazar_franjas` DEBERÁ borrar e insertar
  en una sola transacción.
- **R10** — El sistema NO DEBERÁ instanciar repositorios fuera de `container.py`
  ni importar `src.db` fuera de `src/infrastructure/`. Siempre `model_dump()`.

## Servicio (fachada)

- **R11** — `InfraestructuraService` DEBERÁ delegar el CRUD anterior con métodos
  fachada que reciban tipos simples (no exijan a la interfaz importar modelos de
  dominio), siguiendo el patrón `crear_escenario_simple`/`renombrar_escenario`
  del paso_14e. Como mínimo: `crear_plantilla_simple(nombre, jornada, dias)`,
  `listar_plantillas`, `plantilla_activa(jornada)`, `guardar_franjas(plantilla_id,
  filas)`, `activar_plantilla(plantilla_id)`, `eliminar_plantilla(plantilla_id)`.

## Seed

- **R12** — `seed.py` DEBERÁ crear una **plantilla por defecto** `UNICA`,
  `Lunes..Viernes`, `activa=1`, con 6 franjas lectivas de 55 min y un recreo
  intercalado (`tipo='descanso'`), de modo que el entorno de desarrollo tenga una
  rejilla utilizable. `seed_test` DEBERÁ incluir al menos una plantilla con ≥1
  franja lectiva para fixtures de integración.

## Migración no destructiva

- **R13** — Las nuevas tablas DEBERÁN declararse en `SCHEMA` (creación
  idempotente `IF NOT EXISTS`) y los índices en el bloque de índices; NO se
  requieren `ALTER TABLE` porque son tablas nuevas. La creación DEBERÁ respetar
  el orden de dependencias FK (módulo 2, Infraestructura académica).

## Verificación

- **R14** — DEBERÁ existir cobertura: unit del modelo (`PlantillaFranja`,
  `Franja`, DTOs y validadores) e integración del repo (crear plantilla + franjas,
  activar exclusividad por jornada, `reemplazar_franjas`, `get_plantilla_activa`).
- **R15** — `python init.py` DEBERÁ quedar verde y la suite no DEBERÁ presentar
  regresiones (baseline actual: 804 passed, 1 skipped).

## Fuera de alcance

- Motor de generación de horarios (paso_15c).
- Disponibilidad docente y `config_generacion` (paso_15b).
- Vista de parrilla, color-coding y filtros (paso_15e/15f).
- Vincular `horarios.hora_inicio/fin` a `franja_id` (se evaluará en paso_15c; este
  paso no modifica la tabla `horarios`).
