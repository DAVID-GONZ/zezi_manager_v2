# Tareas: backend_08_recreacion_seed

> SCOPE — archivos que pueden editarse:
> `src/infrastructure/db/seed.py` (reescritura de seeds),
> `src/infrastructure/db/schema.py` (eliminar `init_db` si existe),
> `main.py` (adaptar arranque),
> `tests/conftest.py` (si necesita ajustes menores).
>
> Fuera de scope: repositorios (ya migrados), servicios, interfaz.

---

## T1 — Migrar seed_test a SQLAlchemy  [ ]

Reescribir `seed_test` para usar `insert()` de SQLAlchemy Core en lugar
de SQL crudo.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m "not slow and not e2e and not browser"
```
Tests rápidos verdes (usan `seed_test`).

---

## T2 — Migrar seed_dev a SQLAlchemy  [ ]

Reescribir `seed_dev` igual que T1.

**Verificación:**
```
.venv/Scripts/python.exe -m pytest -q -m integration
```
Tests de integración verdes (usan `seed_dev`).

---

## T3 — Migrar seed_base a SQLAlchemy  [ ]

Reescribir `seed_base` (el seed de producción/desarrollo).

---

## T4 — Eliminar _migrate_* (D9)  [ ]

Eliminar las 9 funciones `_migrate_*` y sus invocaciones dentro de los
seeds.

**Verificación:** grep por `_migrate_` en seed.py → 0 resultados.

---

## T5 — Adaptar arranque en main.py  [ ]

Reescribir la lógica de inicialización de BD:
1. Obtener engine de `Container.engine()`.
2. `metadata.create_all(engine)` (idempotente).
3. Si la BD está vacía de datos, ejecutar `seed_base`.

**Verificación:** la app arranca sin error.

---

## T6 — Verificación de no regresión y cierre  [ ]

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE.

Verificar que la app arranca, crea la BD si no existe, y sirve
correctamente.

**Artefacto:** `progress/impl_backend_08.md`.
