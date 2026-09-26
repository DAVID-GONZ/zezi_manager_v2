# Requisitos: Migración de repositorios (backend_07_repos_migracion)

> Ámbito: migrar los 20 repositorios SQLite de SQL crudo a SQLAlchemy Core,
> uno a uno, manteniendo los puertos intactos. Es el paso más grande de la
> Fase 2 (~500 métodos, ~9,000 LOC).

---

## Queries SQLAlchemy Core

R1: CADA repositorio DEBE reescribir sus queries SQL de strings con `?` a
    expresiones SQLAlchemy Core (`select()`, `insert()`, `update()`,
    `delete()`) usando los objetos `Table` del `MetaData`.

R2: LOS placeholders `?` DEBEN reemplazarse por parámetros nombrados
    (bindparams de SQLAlchemy).

R3: `cursor.lastrowid` DEBE reemplazarse por
    `result.inserted_primary_key[0]`.

R4: `INSERT OR REPLACE` / `INSERT OR IGNORE` DEBEN reemplazarse por
    upserts portables: `insert().on_conflict_do_update()` para SQLite,
    con la puerta preparada para `on_conflict_do_update` de Postgres.

R5: LAS funciones de fecha de SQLite (`strftime`, `date()`, `julianday`)
    DEBEN reemplazarse por funciones neutras de SQLAlchemy (`func.date`,
    `func.current_date`, etc.) o lógica Python.

---

## Conexión SQLAlchemy

R6: CADA repositorio DEBE aceptar una conexión SQLAlchemy en su constructor
    además de (o en lugar de) `sqlite3.Connection`.

R7: LOS repositorios DEBEN usar la conexión de `Container.engine()` cuando
    no se inyecta una.

R8: LAS queries DEBEN ejecutarse con `conn.execute(statement)` de SQLAlchemy,
    no con `conn.execute(string)` de sqlite3.

---

## Renombrado

R9: LOS archivos DEBEN renombrarse de `sqlite_*_repo.py` a `sqla_*_repo.py`
    para reflejar que ya no son específicos de SQLite.

R10: LAS clases DEBEN renombrarse de `Sqlite*Repository` a `Sqla*Repository`.

R11: `container.py` DEBE actualizarse para instanciar los repos con los
     nuevos nombres.

---

## Puertos intactos

R12: LA interfaz pública de cada puerto (`I*Repository` en
     `src/domain/ports/`) NO DEBE cambiar.

R13: LOS servicios y la interfaz NO DEBEN requerir cambios como
     consecuencia de la migración.

---

## Migración incremental

R14: LA migración DEBE hacerse repositorio por repositorio, no en bloque.
     Tras migrar cada repo, la suite de tests DEBE estar verde.

R15: DURANTE la migración, repos migrados y repos sin migrar DEBEN
     coexistir sin conflicto.

---

## Transacciones (D6)

R16: LOS repositorios DEBEN usar transacciones explícitas de SQLAlchemy
     (`conn.begin()`) para operaciones compuestas, resolviendo D6 (0
     rollback, 0 BEGIN en 20 de 21 repos).

R17: LA auditoría y el cambio que describe DEBEN ser atómicos dentro
     de la misma transacción.

---

## Filtro de tenant (absorbe tenant_06)

R18: UN `RepositorioBase` DEBE aplicar filtro obligatorio de
     `institucion_id` en toda query sobre tablas con scope, resolviendo
     el requisito de `tenant_06` sin ORM.

R19: UN test de conformidad DEBE fallar si un `select()` sobre una tabla
     con `institucion_id` no lleva el filtro.
