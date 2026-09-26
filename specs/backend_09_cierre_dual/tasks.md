# Tareas: backend_09_cierre_dual

> SCOPE — archivos que pueden editarse:
> `tests/conftest.py`, `tests/db_engine.py`, `pyproject.toml`,
> archivos remanentes de la migración en `src/infrastructure/db/`.
>
> Fuera de scope: servicios, interfaz (no deben necesitar cambios).

---

## T1 — Auditoría de vestigios sqlite3  [ ]

Ejecutar grep exhaustivo y documentar:

```
grep -rn "import sqlite3" src/
grep -rn "sqlite3\." src/
```

**Artefacto:** lista en `progress/impl_backend_09.md`. Todo resultado
debe eliminarse o justificarse.

---

## T2 — Eliminar vestigios  [ ]

Para cada resultado de T1, eliminar el import y reemplazar por el
equivalente SQLAlchemy. Si un vestigio está en código que no debería
tocarse → **REPORTAR al leader**.

**Verificación:**
```
grep -rn "import sqlite3" src/ | wc -l
```
Debe ser 0.

---

## T3 — Implementar --backend=postgres en conftest  [ ]

Extender `tests/db_engine.py` y conftest para soportar
`--backend=postgres`:
- `DATABASE_URL` desde env var.
- Skip automático si la base no es accesible.
- `metadata.create_all(engine)` para Postgres.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest --backend=postgres --co -q 2>&1 | head -5
```
Debe mostrar skip por `DATABASE_URL no definida` (sin Docker).

---

## T4 — Triggers condicionales por dialecto  [ ]

Adaptar los triggers declarados como `DDL` para que funcionen en ambos
dialectos (SQLite y Postgres).

Si la sintaxis difiere mucho, usar `DDL` condicional:
```python
if engine.dialect.name == "sqlite":
    DDL("CREATE TRIGGER ...")
elif engine.dialect.name == "postgresql":
    DDL("CREATE FUNCTION ...")
```

---

## T5 — Suite completa verde en SQLite  [ ]

```
.venv/Scripts/python.exe -m pytest --backend=sqlite -q
```

Todos los tests verdes. Verificar que el total es ≥ 2,590.

---

## T6 — Limpieza final  [ ]

Verificar y eliminar:
- `src/infrastructure/db/connection.py` (si no se eliminó en backend_07).
- `src/infrastructure/db/queries.py` (si no se eliminó en backend_07).
- Cualquier `sqlite_*_repo.py` remanente.
- Archivos de coexistencia temporal.
- Imports muertos.

**Verificación:**
```
.venv/Scripts/python.exe -m ruff check . --select F811,F401 --output-format concise
```
Cero imports sin usar.

---

## T7 — Verificación de no regresión y cierre  [ ]

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE.

Verificar que la app arranca y funciona normalmente con `DB_BACKEND=sqlite`.

**Artefacto:** `progress/impl_backend_09.md` con el cierre de la Fase 2
y los fallos conocidos de Postgres pendientes para cuando Docker esté
disponible.
