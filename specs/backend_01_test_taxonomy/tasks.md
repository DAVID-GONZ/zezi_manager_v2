# Tareas: backend_01_test_taxonomy

> SCOPE — únicos archivos que pueden editarse:
> `tests/conftest.py`, `pyproject.toml`.
>
> Fuera de scope: archivos de test individuales, código de producción.
> Si una tarea exige tocar algo de ahí → **PARAR y reportar al leader.**

---

## T1 — Inventario de tests con dependencia de BD  [ ]

Recorrer los 194 archivos de test e identificar cuáles:
- Importan `sqlite3` directamente.
- Usan las fixtures `db_conn`, `db_seed`, `seed_result` o `db_dev`.
- Instancian un `Sqlite*Repository`.

**Artefacto:** listado completo en `progress/impl_backend_01.md` con dos
secciones: archivos `repo` y archivos agnósticos, con conteo.

**Verificación:** el conteo de archivos `repo` + agnósticos suma 194.

---

## T2 — Registrar el marker `repo` en pyproject.toml  [ ]

Añadir `"repo: test que depende del backend de BD"` a la lista de markers
en `[tool.pytest.ini_options]`.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest --markers | findstr repo
```
Debe mostrar el marker sin warning.

---

## T3 — Marcado automático en conftest.py  [ ]

Extender `pytest_collection_modifyitems` para que:

1. Todo test en `tests/integration/` reciba el marker `repo` además de
   `integration`.
2. Todo test que solicite los fixtures `db_conn`, `db_seed`, `seed_result`
   o `db_dev` reciba el marker `repo`.

Implementación: inspeccionar `item.fixturenames` para detectar las fixtures
de BD. El marker `repo` se añade con `item.add_marker("repo")`.

**Restricciones:**
- No modificar la lógica de marcado existente (`unit`, `integration`, etc.).
- Los markers deben coexistir: un test puede tener `unit` + `repo`.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -m repo --collect-only -q | tail -5
.venv/Scripts/python.exe -m pytest -m "not repo" --collect-only -q | tail -5
```
La suma de ambos debe ser igual al total de tests.

---

## T4 — Validar que la selección es correcta  [ ]

Ejecutar:

```
.venv/Scripts/python.exe -m pytest -m repo -q
.venv/Scripts/python.exe -m pytest -m "not repo" -q
.venv/Scripts/python.exe -m pytest -q
```

**Criterio:**
- `pytest -m repo` selecciona solo tests que dependen de BD.
- `pytest -m "not repo"` produce el mismo resultado que la suite rápida actual.
- `pytest` (sin filtro) mantiene el mismo total de passed/failed.

---

## T5 — Verificación de no regresión y cierre  [ ]

**Verificación:**
```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. El paso no se declara `done` sin esto.
