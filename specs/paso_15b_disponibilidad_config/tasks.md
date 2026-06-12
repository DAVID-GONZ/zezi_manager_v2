# paso_15b_disponibilidad_config — tasks

Scope: `src/infrastructure/db/schema.py`,
`src/domain/models/infraestructura.py`,
`src/domain/ports/infraestructura_repo.py`,
`src/infrastructure/db/repositories/sqlite_infraestructura_repo.py`,
`src/services/infraestructura_service.py`,
`src/infrastructure/db/seed.py`,
`tests/unit/domain/test_disponibilidad_config_model.py` (nuevo),
`tests/integration/test_disponibilidad_config_repo.py` (nuevo),
y stubs en `FakeInfraRepo` existentes.

---

### T1 — Schema: tablas + índices

Añadir al final del SCHEMA (antes del bloque de índices) las dos tablas
`disponibilidad_docente` y `config_generacion` según el DDL exacto de `design.md`.
Añadir los dos índices al bloque de índices junto a los de paso_15a.

**Verif:**
```
python -X utf8 -c "from src.infrastructure.db.schema import SCHEMA; s=''.join(SCHEMA); print('disp' in s, 'config_generacion' in s)"
```
Debe imprimir `True True`.

---

### T2 — Dominio: modelos + DTOs

En `src/domain/models/infraestructura.py`, añadir (después de `NuevaFranjaDTO` del
paso_15a, en la sección "Rejilla de franjas horarias"):
`PesosGeneracion`, `PESOS_DEFAULT`, `DisponibilidadDocente`, `ConfigGeneracion`,
`ESTADOS_CONFIG`, `TRANSICIONES_CONFIG`, `NuevaDisponibilidadDTO`,
`NuevaConfigGeneracionDTO`.

Usar `import json` (módulo stdlib) para `grupos`/`pesos` si hace falta en algún
validador. Actualizar `__all__`.

**Verif:**
```
python -X utf8 -c "from src.domain.models.infraestructura import PesosGeneracion, DisponibilidadDocente, ConfigGeneracion, TRANSICIONES_CONFIG; print('OK')"
```

---

### T3 — Puerto: métodos abstractos + stubs en Fakes

Añadir los 12 métodos abstractos (5 de disponibilidad + 7 de config) a
`IInfraestructuraRepository`.

Buscar con grep `class FakeInfraRepo` en `tests/unit/services/` y añadir stubs en
TODOS los que hereden `IInfraestructuraRepository`. Los stubs devuelven el tipo
mínimo: `None`, `[]`, `0`, `True` o un objeto simple según la firma.

**Verif:**
```
python -X utf8 -m pytest tests/unit/services/test_horario_service.py tests/unit/services/test_horario_lote.py -q
```
Todos deben seguir pasando.

---

### T4 — Repositorio SQLite

Implementar los 12 métodos en `SqliteInfraestructuraRepository`:
- `upsert_disponibilidad`: `INSERT OR REPLACE`.
- `es_disponible`: `SELECT disponible`; fila no encontrada → `True`.
- `cargar_disponibilidad_lote`: loop de INSERT OR REPLACE con `disponible=0`.
- `limpiar_disponibilidad_docente`: DELETE por `usuario_id`.
- Helper privado `_row_to_config(row)` deserializando JSON.
- `cambiar_estado_config`: leer, validar `puede_transicionar_a`, UPDATE + `updated_at`.
- `duplicar_config_generacion`: INSERT copia con nombre `"<orig> (copia)"`,
  `estado='borrador'`, `escenario_destino_id=NULL`.

**Verif:** se valida en T7 (tests de integración).

---

### T5 — Servicio fachada

Añadir los 11 métodos fachada a `InfraestructuraService` según `design.md`.
`crear_config_generacion`: si `pesos` llega como `dict`, construir
`PesosGeneracion(**pesos)`; si es `None`, usar `PesosGeneracion()`.

**Verif:**
```
python -X utf8 scripts/check_imports.py
```
Sin nuevas violaciones de importación.

---

### T6 — Seed

`_seed_config_generacion(conn, periodo_id, anio_id, plantilla_id)` — idempotente.
Llamar desde `seed_test` y desde la función de seed principal, pasando los IDs
del contexto del seed. Descubrir los IDs reales (de plantilla activa y periodo)
leyendo `seed.py`.

**Verif:**
```
python -X utf8 -c "
import sqlite3
from src.infrastructure.db.schema import init_db
from src.infrastructure.db.seed import seed_test, _fast_hasher
c = sqlite3.connect(':memory:')
c.row_factory = sqlite3.Row
init_db(c)
seed_test(c, anio=2025, hasher=_fast_hasher)
print(c.execute('SELECT COUNT(*) FROM config_generacion').fetchone()[0])
"
```
Debe imprimir ≥1.

---

### T7 — Tests

**`tests/unit/domain/test_disponibilidad_config_model.py`** — al menos 12 tests:
- `PesosGeneracion`: defaults, límite inferior/superior inválido.
- `DisponibilidadDocente`: dia inválido, orden < 1.
- `ConfigGeneracion`: estado inválido, todos los arcos de `puede_transicionar_a`
  (borrador→generado ✓, borrador→aplicado ✗, generado→aplicado ✓,
  generado→borrador ✓, aplicado→cualquiera ✗).
- DTOs: `to_config()` y `to_modelo()` producen el tipo correcto.

**`tests/integration/test_disponibilidad_config_repo.py`** — al menos 7 tests:
- Upsert + leer disponibilidad; idempotencia.
- `es_disponible` para slot bloqueado / no registrado / explícitamente disponible.
- `cargar_disponibilidad_lote` + `limpiar_disponibilidad_docente`.
- CRUD config_generacion (crear, leer, listar, eliminar).
- Transición válida e inválida (`cambiar_estado_config`).
- `duplicar_config_generacion`.
- Seed dejó al menos una config en `borrador`.

**Verif:**
```
python -X utf8 -m pytest tests/unit/domain/test_disponibilidad_config_model.py tests/integration/test_disponibilidad_config_repo.py -v
```

---

### T8 — Verificación integral

```
python -X utf8 init.py
python -X utf8 -m pytest tests/ -q
```
`init.py` → `✅ ENTORNO OK`. Suite ≥ 832 + nuevos, sin regresiones.

Al terminar: reporte en `progress/impl_15b.md`; reviewer → `step_list.json` `done`.
