# Requisitos: Recreación y seed (backend_08_recreacion_seed)

> Ámbito: crear y recrear el esquema desde `metadata.create_all()` + seed
> en SQLite (y preparar para Postgres). Reemplaza los strings DDL de
> `init_db` por el MetaData de SQLAlchemy como fuente de creación.

---

## Creación de esquema

R1: EL SISTEMA DEBE crear el esquema completo usando `metadata.create_all(engine)`
    en lugar de ejecutar strings DDL.

R2: LA creación DEBE funcionar contra un engine SQLite local y contra un
    engine Postgres (cuando esté disponible).

R3: `init_db()` de `schema.py` (si existe) DEBE reescribirse para usar el
    MetaData.

---

## Seed

R4: `seed_base` y `seed_dev` DEBEN funcionar sobre una conexión SQLAlchemy
    en lugar de `sqlite3.Connection`.

R5: LOS seeds DEBEN usar `insert()` de SQLAlchemy Core en lugar de
    SQL crudo con `?`.

R6: LAS 9 funciones `_migrate_*` de `seed.py` (D9) DEBEN eliminarse.
    Con `create_all()` el esquema siempre está completo.

---

## Arranque de la app

R7: `main.py` DEBE usar `metadata.create_all()` para inicializar la BD
    al arrancar, en lugar del mecanismo actual.

R8: EL arranque DEBE detectar si la base existe y tiene datos, para no
    sobreescribir una base de desarrollo existente.

---

## init.py

R9: `python init.py` (la puerta de calidad) DEBE funcionar con el nuevo
    mecanismo de creación de esquema.

---

## Preservación

R10: LA app DEBE arrancar y funcionar exactamente igual tras este paso.

R11: LOS datos existentes en `data/app.db` de desarrollo NO DEBEN perderse
     sin aviso — si el esquema cambió, la app debe avisar o recrear
     explícitamente.
