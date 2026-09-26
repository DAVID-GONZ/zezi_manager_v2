# Requisitos: Queries SQLAlchemy (backend_06_queries_sqlalchemy)

> Ámbito: reescribir `queries.py` (`fetch_df`, `fetch_one`, `fetch_all`,
> `get_scalar`, `execute`) sobre SQLAlchemy Core, eliminando el uso
> directo de `sqlite3` en la capa de acceso a datos.

---

## API preservada

R1: LAS funciones `fetch_df`, `fetch_one`, `fetch_all`, `get_scalar` y
    `execute` DEBEN mantener la misma firma pública (nombres de parámetros,
    tipos de retorno).

R2: LOS repos que hoy llaman estas funciones NO DEBEN requerir cambios
    tras este paso.

---

## SQLAlchemy Core

R3: LAS funciones DEBEN usar una conexión SQLAlchemy (de `Container.engine()`
    o inyectada) en lugar de `get_connection()` de `connection.py`.

R4: LAS queries DEBEN aceptar tanto placeholders `?` (sqlite3 qmark) como
    `:nombre` (SQLAlchemy named) durante la migración. `text()` de SQLAlchemy
    maneja ambos con adaptación.

R5: `execute` DEBE usar transacciones explícitas de SQLAlchemy (`conn.begin()`)
    en lugar de `conn.commit()` manual.

---

## Manejo de errores

R6: LAS funciones NO DEBEN tragar excepciones silenciosamente (resolver D8).
    Una escritura fallida DEBE propagarse al llamador como excepción.

R7: LAS funciones de lectura (`fetch_*`, `get_scalar`) PUEDEN mantener el
    comportamiento actual de retornar valores vacíos en error, con logging,
    pero DEBEN distinguir entre error de consulta y resultado vacío legítimo.

---

## Compatibilidad con pandas

R8: `fetch_df` DEBE seguir devolviendo un `pd.DataFrame`, usando
    `pd.read_sql()` con la conexión SQLAlchemy.

---

## Eliminación de connection.py

R9: `queries.py` NO DEBE importar `connection.py` tras este paso.

R10: `connection.py` SIGUE existiendo — los repos que aún no migraron
     (`backend_07`) la usan directamente.
