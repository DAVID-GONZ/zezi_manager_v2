# Tareas: backend_07_repos_migracion

> SCOPE — archivos que pueden editarse:
> `src/infrastructure/db/repositories/sqlite_*_repo.py` → `sqla_*_repo.py`,
> `src/domain/ports/*_repo.py` (solo si es necesario para tipos),
> `container.py` (renombrar imports),
> `tests/` (adaptar a nuevos nombres).
>
> Fuera de scope: servicios, interfaz.
> Si una tarea exige tocar algo de ahí → **PARAR y reportar al leader.**

Puerta obligatoria tras **cada** ola:

```
.venv/Scripts/python.exe scripts/init.py
```

---

## T1 — Crear RepositorioBase  [ ]

**Artefacto:** `src/infrastructure/db/repositories/base.py` con:
- Constructor que acepta conexión SQLAlchemy.
- Helper `_select()` que construye un `select` sobre la tabla.
- Helper `_upsert()` portable (detecta dialecto SQLite/Postgres).
- Helper `_execute_insert()` que devuelve `inserted_primary_key[0]`.

**Verificación:** import sin error.

---

## T2 — Ola 1: repos pequeños (preferencias, institucion, siee)  [ ]

Migrar los 3 repos más pequeños (7+10+12 = 29 métodos):

1. Reescribir queries a SQLAlchemy Core.
2. Renombrar archivo y clase (`sqlite_*` → `sqla_*`).
3. Actualizar `container.py` con los nuevos nombres.
4. Adaptar tests.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -k "preferencias or institucion or siee"
.venv/Scripts/python.exe scripts/init.py
```

---

## T3 — Ola 2a: repos medianos de negocio core (asignacion, periodo, configuracion)  [ ]

15+20+20 = 55 métodos.

---

## T4 — Ola 2b: repos de evaluación (habilitacion, nivelacion, cierre, plan_mejoramiento)  [ ]

16+16+17+21 = 70 métodos. Incluyen las notas con `Numeric(4,2)`.

---

## T5 — Ola 2c: repos de asistencia y alertas (asistencia, alerta, acudiente, estadisticos)  [ ]

18+17+18+20 = 73 métodos.

---

## T6 — Ola 3a: repos grandes de identidad (usuario, estudiante)  [ ]

22+25 = 47 métodos. Incluyen los 12 `INSERT OR REPLACE` más frecuentes.

---

## T7 — Ola 3b: repos de evaluación y auditoría (evaluacion, auditoria)  [ ]

30+34 = 64 métodos. Auditoría es especial: la cadena SHA-256, la
verificación incremental y los agregados SQL.

---

## T8 — Ola 3c: repos grandes restantes (convivencia, infraestructura)  [ ]

52+121 = 173 métodos. Infraestructura es el repo más grande del proyecto.

**REPORTAR al leader** antes de empezar infraestructura: puede requerir
partirlo en sub-olas.

---

## T9 — Test de conformidad: filtro de tenant  [ ]

Crear `tests/unit/infrastructure/test_tenant_filter_conformance.py`:

Verificar que toda query (`select`, `update`, `delete`) sobre una tabla
con columna `institucion_id` incluye un filtro `WHERE institucion_id = ...`.

Implementación: interceptar las queries ejecutadas durante los tests de
repo y verificar que el filtro está presente.

---

## T10 — Eliminar connection.py  [ ]

Una vez que todos los repos usan SQLAlchemy:
1. Eliminar `src/infrastructure/db/connection.py`.
2. Eliminar `src/infrastructure/db/queries.py` (ya no se usa).
3. Actualizar imports en cualquier lugar que los referencie.

**Verificación:**
```
.venv/Scripts/python.exe -c "import ast; [print(n) for n in ast.walk(ast.parse(open('src/infrastructure/db/__init__.py').read())) if isinstance(n, ast.ImportFrom) and 'connection' in (n.module or '')]"
```
Debe estar vacío.

---

## T11 — Verificación de no regresión y cierre  [ ]

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE.

**Artefacto:** `progress/impl_backend_07.md` con el detalle de cada ola.
