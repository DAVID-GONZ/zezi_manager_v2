# convivencia_09_categorias_schema_seed — Tasks
> ⚠️ TOCA BD — puerta de aprobación de David antes del implementer.

## Objetivo
Crear la tabla `categorias_observacion`, el modelo de dominio, el puerto,
el repo SQLite y el seed de categorías predefinidas. Este paso es el cimiento
de las fases 4 completa (categorías en observaciones, catálogo de plantillas,
promoción a comportamiento).

## Scope
```
src/infrastructure/db/schema.py
src/domain/models/convivencia.py
src/domain/ports/convivencia_repo.py
src/infrastructure/db/repositories/sqlite_convivencia_repo.py
src/infrastructure/db/seed.py
tests/unit/domain/test_convivencia_models.py
tests/integration/test_convivencia_categorias.py   ← crear
```

## Diseño

### Tabla nueva
```sql
CREATE TABLE IF NOT EXISTS categorias_observacion (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre            TEXT    NOT NULL UNIQUE,
    es_comportamental BOOLEAN NOT NULL DEFAULT 0,
    activa            BOOLEAN NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_categorias_obs_activa
    ON categorias_observacion(activa);
```

### Modelo de dominio (en `convivencia.py`)
```python
class CategoriaObservacion(BaseModel):
    id:                int | None = None
    nombre:            str
    es_comportamental: bool       = False
    activa:            bool       = True
```
DTO de creación/edición:
```python
class NuevaCategoriaDTO(BaseModel):
    nombre:            str
    es_comportamental: bool = False
```

### Métodos nuevos en `IConvivenciaRepository`
```python
def listar_categorias(self, solo_activas: bool = True) -> list[CategoriaObservacion]
def get_categoria(self, categoria_id: int) -> CategoriaObservacion | None
def guardar_categoria(self, categoria: CategoriaObservacion) -> CategoriaObservacion
def actualizar_categoria(self, categoria: CategoriaObservacion) -> CategoriaObservacion
```

### Seed predefinido
Categorías a incluir en `seed_base()` (y por ende en `seed_dev()` y `seed_test()`):

| nombre                       | es_comportamental |
|------------------------------|-------------------|
| Académico                    | False             |
| Convivencia y normas         | True              |
| Responsabilidad              | False             |
| Participación                | False             |
| Comportamiento positivo      | True              |
| Comportamiento negativo      | True              |
| Seguimiento familiar         | False             |

Usar el patrón `_get_or_insert` ya existente (idempotente por `nombre`).

## Tareas

### T1 — `schema.py`: añadir tabla e índice
**Archivo**: `src/infrastructure/db/schema.py`

Añadir la definición `CREATE TABLE IF NOT EXISTS categorias_observacion (...)` y el índice
al bloque `SCHEMA` del archivo, junto a las otras tablas de convivencia.

**Verificación**:
```
.venv/Scripts/python.exe -c "
from src.infrastructure.db.schema import create_schema
import sqlite3; conn = sqlite3.connect(':memory:')
create_schema(conn)
rows = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='categorias_observacion'\").fetchall()
assert rows, 'tabla no existe'
print('OK')
"
```

### T2 — `convivencia.py`: modelos `CategoriaObservacion` y `NuevaCategoriaDTO`
**Archivo**: `src/domain/models/convivencia.py`

Añadir las dos clases al módulo.

**Verificación**:
```
.venv/Scripts/python.exe -c "
from src.domain.models.convivencia import CategoriaObservacion, NuevaCategoriaDTO
c = CategoriaObservacion(nombre='Test', es_comportamental=True)
assert c.activa is True
print('OK')
"
```

### T3 — `convivencia_repo.py`: añadir 4 métodos al puerto
**Archivo**: `src/domain/ports/convivencia_repo.py`

Añadir los 4 métodos abstractos a `IConvivenciaRepository`.

### T4 — `sqlite_convivencia_repo.py`: implementar los 4 métodos
**Archivo**: `src/infrastructure/db/repositories/sqlite_convivencia_repo.py`

- `listar_categorias`: `SELECT * FROM categorias_observacion [WHERE activa=1] ORDER BY nombre`.
- `get_categoria`: `SELECT * FROM categorias_observacion WHERE id=?`.
- `guardar_categoria`: `INSERT INTO categorias_observacion (nombre, es_comportamental, activa) VALUES (?,?,?)`, retorna con `id` asignado.
- `actualizar_categoria`: `UPDATE categorias_observacion SET nombre=?, es_comportamental=?, activa=? WHERE id=?`.
- Mapper `_row_to_categoria(row)`: convierte `INTEGER` → `bool` en `es_comportamental` y `activa`.

**Verificación**:
```
.venv/Scripts/python.exe -c "
from src.domain.ports.convivencia_repo import IConvivenciaRepository
from src.infrastructure.db.repositories.sqlite_convivencia_repo import SqliteConvivenciaRepository
assert issubclass(SqliteConvivenciaRepository, IConvivenciaRepository)
print('OK')
"
```

### T5 — `seed.py`: añadir seed de categorías
**Archivo**: `src/infrastructure/db/seed.py`

Añadir lista `_CATEGORIAS_DEFAULT` con las 7 tuplas `(nombre, es_comportamental)`.
Añadir función `_seed_categorias(conn)` que usa `_get_or_insert` buscando por `nombre`.
Llamar `_seed_categorias(conn)` desde `seed_base()`.

### T6 — Tests de integración
**Archivo**: `tests/integration/test_convivencia_categorias.py` (crear)

Tests con `sqlite3.connect(':memory:')` + `create_schema` + `seed_base`:
- `test_listar_categorias_activas_incluye_seed` — al menos 7 categorías después del seed.
- `test_guardar_y_leer_categoria` — crear categoría nueva, leer por id.
- `test_actualizar_categoria_desactivar` — desactivar una, `listar(solo_activas=True)` no la incluye.
- `test_get_categoria_inexistente` — retorna None.

**Verificación**:
```
.venv/Scripts/python.exe -m pytest tests/integration/test_convivencia_categorias.py -v
```

## criterio_done
- [ ] Tabla `categorias_observacion` existe en schema (idempotente con `IF NOT EXISTS`).
- [ ] `CategoriaObservacion` y `NuevaCategoriaDTO` importables desde `src.domain.models.convivencia`.
- [ ] 4 métodos nuevos en puerto implementados en repo.
- [ ] 7 categorías predefinidas en seed_base (idempotentes).
- [ ] 4 tests de integración verdes.
- [ ] `python scripts/check_imports.py --layer infrastructure` verde.
- [ ] `init.py --quick` → ENTORNO OK.
