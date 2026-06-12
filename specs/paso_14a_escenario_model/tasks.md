# paso_14a_escenario_model — tasks

Scope: `src/domain/models/infraestructura.py`, `src/domain/models/usuario.py`,
`src/domain/ports/infraestructura_repo.py`, `src/services/infraestructura_service.py`,
`src/services/usuario_service.py`,
`src/infrastructure/db/schema.py`, `src/infrastructure/db/seed.py`,
`src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`,
`tests/unit/...`, `tests/integration/...`.

> Sin script de transformación de datos. El esquema declara la estructura final;
> el seed provee los datos. La BD se recrea con `init.py`.

---

### T1 — Esquema: tabla `escenarios_horario` + índice parcial
Añadir el `CREATE TABLE escenarios_horario` y el `CREATE UNIQUE INDEX
idx_escenario_activo_unico ... WHERE activo = 1` en `schema.py`.
**Verif:** `python -c "from src.infrastructure.db.schema import SCHEMA_STATEMENTS, INDEX_STATEMENTS; assert any('escenarios_horario' in s for s in SCHEMA_STATEMENTS)"`

### T2 — Esquema: columnas en `horarios` y `usuarios`
En `horarios`: añadir `escenario_id INTEGER NOT NULL` + FK CASCADE, sustituir la
UNIQUE por `UNIQUE(escenario_id, grupo_id, dia_semana, hora_inicio)`, hacer
`periodo_id` NULL-able, añadir `idx_horarios_escenario`. En `usuarios`: añadir
`carga_horaria_max INTEGER`.
**Verif:** `python init.py --quick` reconstruye el esquema sin error.

### T3 — Modelo `EscenarioHorario` + `NuevoEscenarioDTO`
Crear ambos en `infraestructura.py` con validators (nombre no vacío, anio_id
positivo). Actualizar `__all__`.
**Verif:** `python -c "from src.domain.models.infraestructura import EscenarioHorario, NuevoEscenarioDTO; EscenarioHorario(anio_id=1, nombre='x')"`

### T4 — `Horario` / `NuevoHorarioDTO` / `HorarioInfo` con `escenario_id`
Añadir `escenario_id` (positivo) a las tres; `periodo_id` opcional en `Horario`
y `NuevoHorarioDTO`.
**Verif:** `python -m pytest tests/unit/domain/ -q -k horario`

### T5 — `usuario.py`: `carga_horaria_max`
Añadir el campo opcional con validator de no-negativo.
**Verif:** `python -m pytest tests/unit/domain/ -q -k usuario`

### T6 — Puerto: métodos de escenario y consultas por escenario
Declarar en `IInfraestructuraRepository` los métodos abstractos listados en el
design (get/list/activar/eliminar/duplicar escenario + listar por escenario).
**Verif:** `python scripts/check_imports.py --layer domain`

### T7 — Repo SQLite: CRUD de escenario + activación atómica + duplicado
Implementar en `sqlite_infraestructura_repo.py`. `activar_escenario` desactiva
los demás del año. `duplicar_escenario` copia bloques.
**Verif:** `python -m pytest tests/integration/ -q -k escenario`

### T8 — Repo SQLite: horarios con `escenario_id` + resolución de escenario activo
`guardar_horario`/`actualizar_horario` incluyen `escenario_id` (y `periodo_id`
NULL si ausente). `listar_horario_grupo`/`listar_horario_docente` resuelven
periodo→año→escenario activo. Añadir `listar_horario_grupo_escenario`,
`listar_horario_escenario`.
**Verif:** `python -m pytest tests/integration/ -q -k horario`

### T9 — Servicios: delegaciones nuevas
`InfraestructuraService`: métodos de escenario + consultas por escenario.
`UsuarioService`: `carga_horaria_max(usuario_id) -> int | None`.
**Verif:** `python scripts/check_imports.py --layer services`

### T10 — `seed.py`: escenarios + carga horaria
`_seed_escenarios` (base activo + alterno inactivo); `_seed_horarios` inserta con
`escenario_id`; docentes dev con `carga_horaria_max=22`; `seed_test` con
escenario activo + 1 bloque.
**Verif:** `python -m pytest tests/integration/ -q -k seed`

### T11 — Tests unitarios del modelo de escenario
Casos: nominal, nombre vacío (error), anio_id no positivo (error), duplicado de
escenario produce inactivo con nombre distinto (a nivel servicio con FakeRepo).
**Verif:** `python -m pytest tests/unit/ -q -k escenario`

### T12 — Verificación integral
**Verif:** `python init.py` exit 0 y `python -m pytest tests/ -q` sin regresiones.

Al terminar: `step_list.json` → `paso_14a_escenario_model` = `spec_ready` → tras
implementación y reviewer, `done`.
