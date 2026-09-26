# Diseño: backend_02_conftest_parametrizado

## Punto de partida medido

`tests/conftest.py` tiene 6 puntos de acoplamiento directo a `sqlite3`:

| Línea | Uso |
|---|---|
| 42 | `import sqlite3` |
| 81 | `def _apply_schema(conn: sqlite3.Connection)` |
| 87 | `conn.row_factory = sqlite3.Row` |
| 104-110 | `db_schema`: `sqlite3.connect(":memory:")` |
| 127-131 | `db_seed`: `sqlite3.connect(":memory:")` |
| 173-177 | `db_dev`: `sqlite3.connect(":memory:")` |

Además, `_apply_schema` ejecuta las listas `SCHEMA`, `INDICES` y `TRIGGERS`
como strings DDL directos sobre la conexión.

## D1 — Factory de engine para tests

Crear `tests/db_engine.py` con una función `create_test_engine(backend: str)`
que devuelve una conexión configurada:

```python
def create_test_engine(backend: str = "sqlite") -> sqlite3.Connection:
    if backend == "sqlite":
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn
    raise ValueError(f"Backend no soportado: {backend}")
```

En `backend_03`/`backend_09` se añadirá la rama `"postgres"` que devuelva
una conexión SQLAlchemy. Por ahora solo `sqlite`.

La factory centraliza la creación de conexiones de test en un solo lugar,
de modo que el día que se introduzca SQLAlchemy, el cambio sea en un solo
archivo.

## D2 — Parametrización por addoption

En `conftest.py`, registrar `--backend` como opción de pytest:

```python
def pytest_addoption(parser):
    parser.addoption(
        "--backend", default="sqlite", choices=["sqlite"],
        help="Backend de BD para tests de repositorio"
    )
```

Las fixtures leen `request.config.getoption("--backend")` y se lo pasan
a `create_test_engine`. En este paso solo existe `"sqlite"` como choice;
`backend_03` añade `"postgres"`.

## D3 — _apply_schema abstraído

`_apply_schema` deja de asumir sqlite3 en su firma. Recibe la conexión
que devuelve la factory (que en este paso sigue siendo `sqlite3.Connection`).
El cuerpo no cambia: sigue ejecutando `SCHEMA`, `INDICES` y `TRIGGERS`
como strings.

Cuando `backend_04` reemplace los strings DDL por `MetaData`, `_apply_schema`
pasará a llamar `metadata.create_all(engine)`. Pero eso no es de este paso.

## D4 — Scope de las fixtures sin cambio

Los scopes (`session`, `function`, `module`) no cambian. La parametrización
no implica re-crear la BD por cada combinación: hay un solo backend activo
por ejecución de pytest, determinado por `--backend`.

## Alternativa descartada

**Usar SQLAlchemy `create_engine` ya en este paso.** Es la solución final,
pero introduce una dependencia nueva sin que el código de producción la
consuma todavía. Mejor mantener la costura preparada y que `backend_04` la
cierre cuando las dos partes (schema + conftest) estén listas.
