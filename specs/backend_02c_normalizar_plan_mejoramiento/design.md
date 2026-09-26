# Diseño: backend_02c_normalizar_plan_mejoramiento

## Punto de partida medido

`sqlite_plan_mejoramiento_repo.py` es el **único** repositorio que no sigue
el patrón del resto. Diferencias:

| Aspecto | Los otros 19 repos | plan_mejoramiento |
|---|---|---|
| Constructor | `__init__(self, conn=None)` | Sin `conn` |
| Conexión | `get_connection()` de `connection.py` | `_get_conn()` propia |
| `sqlite3` directo | No (usa `connection.py`) | Sí: `sqlite3.connect(_db_path())` |
| `check_same_thread` | `False` (en `get_connection`) | No especificado |
| WAL | Sí (en `get_connection`) | No |
| Tests | Usan fixtures en memoria | Golpean `data/app.db` |

El repositorio tiene 21 funciones definidas (6 helpers + 15 métodos de clase)
y todas usan `_get_conn()`.

## D1 — Adoptar el patrón conn=None

Reescribir el constructor para aceptar `conn=None`:

```python
class SqlitePlanMejoramientoRepository(IPlanMejoramientoRepository):
    def __init__(self, conn=None):
        self._conn = conn
```

Cada método que hoy usa `with _get_conn() as conn:` pasa a usar
`self._conn` si existe, o `get_connection()` si no:

```python
def _get_conn(self):
    if self._conn:
        return contextlib.nullcontext(self._conn)
    return get_connection()
```

Este patrón ya existe en otros repos que necesitan funcionar tanto
inyectados (tests) como autónomos (producción).

## D2 — Eliminar _db_path y el sqlite3 directo

Borrar `_db_path()` y el `_get_conn()` global (funciones de módulo).
Convertir `_get_conn` en método de instancia con la lógica de D1.

Borrar `import sqlite3` y `from pathlib import Path` si ya no se usan.

## D3 — Helpers _row_to_*

Las funciones `_row_to_corte`, `_row_to_nota_corte`, `_row_to_actividad`,
`_row_to_nota_actividad` reciben `sqlite3.Row`. Con la normalización,
siguen recibiendo `sqlite3.Row` porque la conexión proviene de
`get_connection()` que ya configura `row_factory`. No cambian.

## D4 — Tests de integración

Los tests de plan_mejoramiento que hoy tocan `data/app.db` pasan a usar
las fixtures `db_conn` o `db_seed` del conftest.

Instanciar el repo con `SqlitePlanMejoramientoRepository(conn=db_conn)`.

## D5 — Container.py

`container.py` ya instancia este repo. Verificar que el call site no
necesita cambios — debería seguir siendo `SqlitePlanMejoramientoRepository()`
sin argumentos (usa `get_connection()` por defecto).

## Alternativa descartada

**Dejar el repo como está y adaptarlo directamente en `backend_07`.** El
problema es que sus tests de integración golpean la base real, lo que
corrompe el aislamiento de la suite. Normalizarlo ahora es requisito para
que `backend_02` (conftest parametrizado) no deje un repo fuera.
