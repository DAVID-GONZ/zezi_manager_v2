# Requisitos: Conftest parametrizado (backend_02_conftest_parametrizado)

> Ámbito: las fixtures de BD en `tests/conftest.py` y el módulo
> `src/infrastructure/db/connection.py`. El objetivo es que las fixtures
> funcionen sobre un engine inyectable, preparando la costura para un
> segundo backend sin introducirlo todavía.

---

## Abstracción del engine

R1: LAS fixtures de BD (`db_schema`, `db_seed`, `db_conn`, `seed_result`,
    `db_dev`) DEBEN funcionar sobre un engine proporcionado por una factory,
    no sobre `sqlite3.connect(":memory:")` hardcodeado.

R2: LA factory de engine DEBE ser reemplazable desde la línea de comandos
    o una variable de entorno, de modo que un backend futuro pueda enchufarse
    sin editar `conftest.py`.

R3: EN ESTE PASO la factory DEBE producir solo engines SQLite (en memoria).
    No se introduce ningún otro backend.

---

## Eliminación de sqlite3 directo en fixtures

R4: `conftest.py` NO DEBE importar `sqlite3` directamente tras este paso.

R5: LAS fixtures DEBEN usar la factory para obtener la conexión y aplicar
    el schema, en lugar de llamar a `sqlite3.connect` y ejecutar DDL en
    strings.

R6: `_apply_schema` DEBE funcionar contra el engine proporcionado por la
    factory, independientemente de que sea SQLite u otro backend futuro.

---

## Compatibilidad con el conftest parametrizado futuro

R7: LA factory DEBE aceptar un parámetro de backend (`"sqlite"` o futuro
    `"postgres"`) que determine qué engine crea.

R8: EL conftest parametrizado DEBE dejar preparada la infraestructura para
    que `backend_03` o `backend_09` puedan añadir `--backend=postgres` sin
    tocar las fixtures.

---

## Preservación

R9: LA suite completa DEBE mantener el mismo resultado: mismo número de
    passed, failed y skipped.

R10: LOS tests que hoy importan `sqlite3` directamente (fuera de conftest)
     NO se tocan en este paso — eso es trabajo de `backend_07`.

R11: EL seed (`seed_test`, `seed_dev`) DEBE seguir funcionando exactamente
     igual: recibe una conexión y siembra datos.
