# Tareas: backend_06_queries_sqlalchemy

> SCOPE — archivos que pueden editarse:
> `src/infrastructure/db/queries.py` (reescritura).
>
> Fuera de scope: repositorios, `connection.py`, servicios, interfaz.
> Si una tarea exige tocar algo de ahí → **PARAR y reportar al leader.**

---

## T1 — Adaptar _normalize_params a _adapt_params  [ ]

Renombrar y extender la función de normalización para que:
1. Siga convirtiendo escalares numpy/pandas a nativos.
2. Prepare los parámetros para `exec_driver_sql` (tupla) o `text()` (dict).

**Verificación:** import sin error.

---

## T2 — Migrar fetch_one y fetch_all  [ ]

Reescribir ambas funciones para usar `Container.engine().connect()` con
`exec_driver_sql(query, params)` (ver D2).

`row_factory` ya no aplica — SQLAlchemy devuelve `Row` con `.mappings()`.

Conservar la firma pública y el tipo de retorno (`dict | None` y
`list[dict]`).

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not e2e and not browser" -k "test_" --timeout=60
```
Tests que llaman fetch_one/fetch_all deben pasar.

---

## T3 — Migrar get_scalar  [ ]

Reescribir para usar `exec_driver_sql`. `result.scalar()` de SQLAlchemy
es el equivalente directo.

---

## T4 — Migrar fetch_df  [ ]

Reescribir usando `pd.read_sql(text(query), conn, params=...)`.
`pd.read_sql` acepta conexiones SQLAlchemy desde pandas 1.4+.

---

## T5 — Migrar execute (resolución de D8)  [ ]

Reescribir `execute` con propagación de errores:
- En caso de error, lanzar la excepción en lugar de devolver `False`.
- Usar `conn.begin()` para transacciones explícitas.
- `lastrowid` → `result.lastrowid` (funciona con SQLAlchemy sobre SQLite).

**REPORTAR al leader** si algún repo depende del retorno `False` de
`execute` para tomar decisiones — esos repos necesitarán try/except.

---

## T6 — Eliminar import de connection.py  [ ]

Verificar que `queries.py` ya no importa `get_connection` ni
`_normalize_params` de `connection.py`.

**Verificación:**
```
.venv/Scripts/python.exe -c "import ast, pathlib; t=ast.parse(pathlib.Path('src/infrastructure/db/queries.py').read_text()); imps=[n for n in ast.walk(t) if isinstance(n, (ast.Import, ast.ImportFrom))]; assert not any('connection' in (getattr(n,'module','') or '') for n in imps), 'Aún importa connection'"
```

---

## T7 — Verificación de no regresión y cierre  [ ]

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. Tests de repos verdes con el nuevo `queries.py`.

**Artefacto:** `progress/impl_backend_06.md`.
