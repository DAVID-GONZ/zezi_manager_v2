# Requisitos: Cierre dual (backend_09_cierre_dual)

> Ámbito: suite completa verde contra SQLite. Verificar que no quedan
> vestigios de acoplamiento directo a sqlite3 en código de producción.
> Preparar la infraestructura para que Postgres se conecte limpio
> cuando Docker esté disponible (backend_03 se ejecuta aquí).

---

## Suite completa en SQLite

R1: TODA la suite de tests (unit + integration + repo) DEBE estar verde
    con `--backend=sqlite`.

R2: EL total de tests DEBE ser al menos igual al que había al iniciar
    la Fase 2 (2,290 unit + 300 integration).

---

## Eliminación de vestigios sqlite3

R3: NINGÚN archivo en `src/` DEBE importar `sqlite3` directamente.

R4: `connection.py` DEBE estar eliminado (completado en backend_07).

R5: `queries.py` DEBE estar eliminado o vaciado (completado en backend_07).

R6: LAS funciones `_normalize_params` y similares específicas de sqlite3
    DEBEN estar eliminadas.

---

## Infraestructura Postgres (ex-backend_03)

R7: EL conftest DEBE soportar `--backend=postgres` como opción (además
    de `sqlite`).

R8: CUANDO se pasa `--backend=postgres`, las fixtures DEBEN crear un engine
    SQLAlchemy sobre Postgres (URL desde env var `DATABASE_URL`).

R9: SI Docker no está disponible o la base Postgres no es accesible, los
    tests de Postgres DEBEN skipearse con `pytest.skip()`, no fallar.

R10: `metadata.create_all()` DEBE generar un schema equivalente en Postgres
     (los tipos neutros de backend_04 lo garantizan).

---

## Verificación de portabilidad

R11: LOS tests que se ejecuten contra Postgres PUEDEN fallar por diferencias
     de dialecto — esos fallos se documentan y se reportan, pero NO bloquean
     el cierre de este paso.

R12: EL paso se declara done cuando SQLite está completamente verde y
     Postgres tiene una infraestructura funcional (aunque con fallos
     conocidos por dialecto que se resolverán al tener Docker).

---

## Limpieza

R13: TODO archivo temporal, de compatibilidad o de coexistencia creado
     durante la migración DEBE eliminarse.

R14: `init.py` DEBE ejecutarse completamente verde.
