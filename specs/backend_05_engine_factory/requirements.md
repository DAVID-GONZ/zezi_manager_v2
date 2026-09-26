# Requisitos: Engine factory (backend_05_engine_factory)

> Ámbito: factory de engine SQLAlchemy en `container.py` conmutable por
> configuración entre SQLite y Postgres. Reemplaza `connection.py` como
> punto de entrada a la BD.
>
> ⚠️ PUERTA DE APROBACIÓN: toca `container.py` → requiere aprobación de David.

---

## Conmutación de backend

R1: EL SISTEMA DEBE crear el engine de SQLAlchemy según la variable de
    entorno `DB_BACKEND` (valores: `"sqlite"`, `"postgres"`).

R2: CUANDO `DB_BACKEND=sqlite`, EL engine DEBE apuntar a la ruta de la
    base de datos local (`sqlite:///data/app.db` o configurable).

R3: CUANDO `DB_BACKEND=postgres`, EL engine DEBE usar la URL de conexión
    definida en `DATABASE_URL` (`postgresql+psycopg://...`).

R4: SI `DB_BACKEND` no está definido, EL SISTEMA DEBE usar `sqlite` como
    default.

---

## Configuración de SQLite

R5: CUANDO el engine es SQLite, EL SISTEMA DEBE aplicar los pragmas de
    sesión (`journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`,
    `cache_size=-64000`) mediante eventos SQLAlchemy (`event.listen`).

R6: LOS pragmas DEBEN aplicarse a cada conexión nueva del pool, no una
    sola vez.

---

## Integración con Container

R7: `Container` DEBE exponer un método `engine()` que devuelve el engine
    singleton.

R8: `Container` DEBE exponer un método `connection()` que devuelve una
    conexión del engine (context manager).

R9: LOS repositorios DEBEN poder recibir una conexión SQLAlchemy en su
    constructor, además de la conexión sqlite3 actual (compatibilidad
    durante la migración).

---

## Coexistencia

R10: `connection.py` y `get_connection()` DEBEN seguir funcionando durante
     la migración de repos. No se eliminan en este paso.

R11: LA app DEBE arrancar con `DB_BACKEND=sqlite` sin cambios visibles
     en la funcionalidad.

---

## Configuración

R12: `config.py` y `.env.example` DEBEN documentar las variables
     `DB_BACKEND` y `DATABASE_URL`.
