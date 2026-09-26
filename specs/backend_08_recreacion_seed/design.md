# Diseño: backend_08_recreacion_seed

## Punto de partida medido

| Componente | Estado tras backend_07 |
|---|---|
| `schema.py` | MetaData con 65+ tablas (tras backend_04) |
| `seed.py` | ~2,000 líneas, funciones `seed_base`, `seed_dev`, `seed_test` |
| `seed.py _migrate_*` | 9 funciones `ALTER TABLE ADD COLUMN` (D9) |
| `main.py init` | `init_db()` + `seed_base()` si BD vacía |
| conftest | `metadata.create_all()` (tras backend_04) |
| connection.py | Eliminado (tras backend_07) |

## D1 — create_all como punto único de creación

```python
from src.infrastructure.db.schema import metadata

def crear_esquema(engine):
    metadata.create_all(engine)
```

Reemplaza `init_db()` y las listas `SCHEMA/INDICES/TRIGGERS`.
`create_all()` es idempotente: no recrea tablas que ya existen.

## D2 — Seeds sobre SQLAlchemy

Los seeds pasan de `conn.execute("INSERT ...")` a:

```python
from src.infrastructure.db.schema import instituciones

conn.execute(instituciones.insert().values(
    nombre="ZECI Demo",
    activa=True,
    ...
))
```

Los seeds siguen recibiendo una conexión. La diferencia es que ahora
es una conexión SQLAlchemy en vez de sqlite3.

## D3 — Eliminación de _migrate_*

Las 9 funciones `_migrate_*` añaden columnas con `ALTER TABLE ADD COLUMN`.
Existían porque la base se creaba con strings DDL y la base de desarrollo
no se recreaba al añadir columnas.

Con `create_all()`, el esquema siempre está completo. Si la base de
desarrollo tiene un esquema viejo, se recrea.

Se eliminan las 9 funciones y sus invocaciones.

## D4 — Arranque en main.py

```python
def main():
    engine = Container.engine()
    # Crear esquema si la BD es nueva
    if _is_empty(engine):
        metadata.create_all(engine)
        with engine.connect() as conn:
            seed_base(conn, anio=current_year)
            conn.commit()
```

`_is_empty` comprueba si existe al menos una tabla en la BD.

## D5 — Conftest ya migrado

El conftest ya usa `metadata.create_all()` desde backend_04.
Los seeds de test (`seed_test`, `seed_dev`) se adaptan igual que los
de producción.

## Alternativa descartada

**Introducir Alembic para migraciones.** La decisión de arquitectura
permanente (CLAUDE.md) dice que no hay migraciones en este entorno. Se
recrea la base cuando cambia el esquema. Alembic llega antes del primer
despliegue con datos de producción.
