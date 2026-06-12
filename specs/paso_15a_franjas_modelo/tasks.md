# paso_15a_franjas_modelo — tasks

Scope: `src/infrastructure/db/schema.py`,
`src/domain/models/infraestructura.py`,
`src/domain/ports/infraestructura_repo.py`,
`src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`,
`src/services/infraestructura_service.py`,
`src/infrastructure/db/seed.py`,
`tests/unit/domain/test_franja_model.py` (nuevo),
`tests/integration/test_franjas_repo.py` (nuevo),
y stubs en los `FakeInfraRepo` existentes.

---

### T1 — Esquema: tablas `plantillas_franja` + `franjas` + índices
Añadir las dos tablas en `SCHEMA` (módulo 2, tras `escenarios_horario`) y los tres
índices en el bloque de índices (junto a `idx_escenario_activo_unico`), según
`design.md`. Sin `ALTER TABLE` (tablas nuevas).
**Verif:** `python -X utf8 -c "from src.infrastructure.db.schema import SCHEMA; print('plantillas_franja' in ''.join(SCHEMA), 'franjas' in ''.join(SCHEMA))"`

### T2 — Dominio: modelos + DTOs + DIAS_VALIDOS
`PlantillaFranja`, `Franja`, `NuevaPlantillaFranjaDTO`, `NuevaFranjaDTO`,
constante `DIAS_VALIDOS`, propiedad `Franja.es_lectiva`, validadores (nombre,
jornada, tipo, orden, hora_inicio<hora_fin, dias_activos). Actualizar `__all__`.
**Verif:** `python -X utf8 -c "from src.domain.models.infraestructura import PlantillaFranja, Franja, NuevaPlantillaFranjaDTO, NuevaFranjaDTO, DIAS_VALIDOS; print('OK')"`

### T3 — Puerto: métodos abstractos + stubs en Fakes
Añadir los 12 métodos a `IInfraestructuraRepository`. **Añadir stubs** a TODOS los
`FakeInfraRepo` de los tests existentes (`test_horario_service.py`,
`test_horario_lote.py`) devolviendo `None`/`[]`/`0`/`True` para que sigan
instanciables (regresión esperada — ver nota en design.md).
**Verif:** `python -X utf8 -m pytest tests/unit/services/test_horario_service.py tests/unit/services/test_horario_lote.py -q`

### T4 — Repositorio SQLite
Implementar los 12 métodos en `SqliteInfraestructuraRepository`: mapeo CSV de
`dias_activos`, `get_plantilla_activa`, `activar_plantilla_franja` (transacción de
exclusividad por jornada), `reemplazar_franjas` (DELETE + executemany en una
transacción), `listar_franjas ORDER BY orden`.
**Verif:** importable; se valida en T7.

### T5 — Servicio fachada
`crear_plantilla_simple`, `listar_plantillas`, `plantilla_activa`,
`guardar_franjas(plantilla_id, filas: list[dict])`, `activar_plantilla`,
`eliminar_plantilla` en `InfraestructuraService`. La interfaz no importa modelos
de dominio (patrón paso_14e); los DTOs se construyen dentro del servicio.
**Verif:** `python -X utf8 scripts/check_imports.py` sin nuevas violaciones.

### T6 — Seed
`_seed_plantilla_franjas(conn)`: plantilla UNICA activa Lun–Vie + 7 franjas
(6 lectivas + recreo) según la tabla de `design.md`. Invocar desde el seed
principal y desde `seed_test` (plantilla mínima con ≥1 franja lectiva).
**Verif:** `python -X utf8 -c "import sqlite3; from src.infrastructure.db.schema import init_db; from src.infrastructure.db.seed import seed_demo; c=sqlite3.connect(':memory:'); c.row_factory=sqlite3.Row; init_db(c); seed_demo(c); print(c.execute('SELECT COUNT(*) FROM franjas').fetchone()[0])"` (ajustar nombre real de la función de seed)

### T7 — Tests
`tests/unit/domain/test_franja_model.py` (validadores + DTOs + es_lectiva) y
`tests/integration/test_franjas_repo.py` (crear + reemplazar_franjas, exclusividad
por jornada, AM+PM ambas activas, cascada de borrado, seed dejó plantilla activa).
**Verif:** `python -X utf8 -m pytest tests/unit/domain/test_franja_model.py tests/integration/test_franjas_repo.py -v`

### T8 — Verificación integral
**Verif:** `python -X utf8 init.py` exit 0; `python -X utf8 -m pytest tests/ -q`
sin regresiones (≥804 passed).

Al terminar: reporte en `progress/impl_15a.md`; reviewer → `step_list.json` `done`.
