# Tareas: backend_02c_normalizar_plan_mejoramiento

> SCOPE — archivos que pueden editarse:
> `src/infrastructure/db/repositories/sqlite_plan_mejoramiento_repo.py`,
> tests de plan_mejoramiento en `tests/integration/` y `tests/unit/`.
>
> Fuera de scope: otros repositorios, servicios, interfaz, container.py
> (verificar que no necesita cambios, pero no editarlo sin autorización).
> Si una tarea exige tocar algo de ahí → **PARAR y reportar al leader.**

---

## T1 — Auditar el estado actual  [ ]

Medir:
- Cuántos métodos usan `_get_conn()` (el context manager propio).
- Cuántos tests de plan_mejoramiento existen y dónde.
- Verificar que los tests actuales tocan `data/app.db` real.

**Artefacto:** inventario en `progress/impl_backend_02c.md`.

---

## T2 — Reescribir el constructor con conn=None  [ ]

Añadir `__init__(self, conn=None)` con `self._conn = conn`.

Convertir `_get_conn()` de función de módulo a método de instancia que
devuelve `contextlib.nullcontext(self._conn)` si hay conexión inyectada,
o `get_connection()` si no.

Eliminar las funciones de módulo `_db_path()` y `_get_conn()`.

**Restricciones:**
- La interfaz pública (métodos de `IPlanMejoramientoRepository`) no cambia.
- `import sqlite3` se elimina si ya no se usa directamente.
- Añadir `from src.infrastructure.db.connection import get_connection`.

**Verificación:**
```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from src.infrastructure.db.repositories.sqlite_plan_mejoramiento_repo import SqlitePlanMejoramientoRepository; print('OK')"
```

---

## T3 — Actualizar cada método para usar self._get_conn()  [ ]

Recorrer los ~15 métodos que hoy hacen `with _get_conn() as conn:` y
cambiarlos a `with self._get_conn() as conn:`.

**Verificación parcial:**
```
.venv/Scripts/python.exe -m ruff check src/infrastructure/db/repositories/sqlite_plan_mejoramiento_repo.py --select F821,F811
```
Cero errores (no hay referencias a funciones eliminadas).

---

## T4 — Migrar tests a fixtures en memoria  [ ]

Los tests de integración de plan_mejoramiento pasan a usar `db_conn` de
conftest en lugar de conectar a `data/app.db`.

Instanciar el repo con `SqlitePlanMejoramientoRepository(conn=db_conn)`.

Si los tests necesitan datos de seed específicos de plan_mejoramiento que
el `seed_test` no provee, crear los datos en el test mismo.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest tests/ -k plan_mejoramiento -v
```
Todos verdes, y verificar que `data/app.db` no se modifica durante la
ejecución.

---

## T5 — Verificar container.py  [ ]

Verificar que `container.py` instancia el repo sin argumentos y que el
comportamiento no cambia (usa `get_connection()` por defecto).

**NO editar container.py** sin autorización del leader.

---

## T6 — Verificación de no regresión y cierre  [ ]

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. El paso no se declara `done` sin esto.

Verificar que `grep -n "sqlite3.connect" src/infrastructure/db/repositories/sqlite_plan_mejoramiento_repo.py`
no devuelve resultados.
