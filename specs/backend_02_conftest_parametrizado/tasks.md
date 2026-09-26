# Tareas: backend_02_conftest_parametrizado

> SCOPE — archivos que pueden crearse o editarse:
> `tests/conftest.py`, `tests/db_engine.py` (nuevo), `pyproject.toml`.
>
> Fuera de scope: archivos de test individuales, código de producción,
> `src/infrastructure/db/`.
> Si una tarea exige tocar algo de ahí → **PARAR y reportar al leader.**

---

## T1 — Crear la factory de engine para tests  [ ]

**Artefacto:** `tests/db_engine.py` con `create_test_engine(backend="sqlite")`
según D1.

La función crea una conexión SQLite en memoria con `foreign_keys=ON` y
`row_factory=sqlite3.Row`. Si recibe un backend no soportado, lanza
`ValueError`.

**Verificación:**
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from tests.db_engine import create_test_engine; conn = create_test_engine(); print(conn.execute('SELECT 1').fetchone()[0])"
```
Debe imprimir `1`.

---

## T2 — Registrar la opción --backend en conftest.py  [ ]

Añadir `pytest_addoption` en `conftest.py` con la opción `--backend`
según D2. Solo `"sqlite"` como choice por ahora.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest --help | findstr backend
```
Debe mostrar la opción.

---

## T3 — Migrar _apply_schema a la factory  [ ]

Reescribir `_apply_schema` para que reciba la conexión de `create_test_engine`
en lugar de asumir `sqlite3.Connection` en la firma.

Eliminar `import sqlite3` del conftest. Las tres fixtures (`db_schema`,
`db_seed`, `db_dev`) pasan a llamar `create_test_engine(backend)` en lugar
de `sqlite3.connect(":memory:", ...)`.

**Restricciones:**
- `_apply_schema` sigue ejecutando `SCHEMA`, `INDICES` y `TRIGGERS` como
  strings DDL. No cambia la forma de aplicar el schema.
- Los pragmas (`foreign_keys`, `row_factory`) se configuran en la factory,
  no en las fixtures.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not e2e and not browser"
```
Mismo resultado que antes del cambio.

---

## T4 — Verificar que --backend=sqlite funciona explícitamente  [ ]

```
.venv/Scripts/python.exe -m pytest --backend=sqlite -q -m "not slow and not e2e and not browser"
.venv/Scripts/python.exe -m pytest --backend=sqlite -q -m integration
```

Ambos deben dar el mismo resultado que sin `--backend`.

---

## T5 — Verificar ausencia de sqlite3 en conftest  [ ]

```
.venv/Scripts/python.exe -c "import ast, pathlib; tree=ast.parse(pathlib.Path('tests/conftest.py').read_text()); imports=[n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]; assert 'sqlite3' not in imports, f'sqlite3 sigue importado: {imports}'"
```

Debe pasar sin AssertionError.

---

## T6 — Verificación de no regresión y cierre  [ ]

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. El paso no se declara `done` sin esto.

**Artefacto:** `progress/impl_backend_02.md` con lo aplicado.
