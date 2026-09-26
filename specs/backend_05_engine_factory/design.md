# Diseño: backend_05_engine_factory

## Punto de partida medido

| Componente | Estado actual |
|---|---|
| `connection.py` | `sqlite3.connect()` directo, `get_connection()` context manager |
| `container.py` | Singleton cache, no gestiona conexiones de BD |
| `config.py` | `DATABASE_PATH` (Path), sin `DB_BACKEND` |
| `.env.example` | Sin variables de BD |
| `queries.py` | Usa `get_connection()` de `connection.py` |
| Repos | `__init__(self, conn=None)`, conn es `sqlite3.Connection` |

## D1 — Engine factory en container.py

```python
from sqlalchemy import create_engine, event

class Container:
    @classmethod
    def engine(cls):
        if "engine" not in cls._cache:
            cls._cache["engine"] = _create_engine()
        return cls._cache["engine"]

    @classmethod
    @contextmanager
    def connection(cls):
        with cls.engine().connect() as conn:
            yield conn

def _create_engine():
    backend = os.getenv("DB_BACKEND", "sqlite")
    if backend == "sqlite":
        url = f"sqlite:///{_resolve_db_path()}"
        engine = create_engine(url, echo=False)
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.close()
        return engine
    elif backend == "postgres":
        url = os.getenv("DATABASE_URL")
        return create_engine(url, echo=False, pool_pre_ping=True)
    raise ValueError(f"DB_BACKEND no soportado: {backend}")
```

## D2 — Coexistencia con connection.py

Durante la migración (backend_06 y backend_07), ambos sistemas coexisten:
- `get_connection()` → usado por repos que aún no migraron.
- `Container.connection()` → usado por repos migrados a SQLAlchemy.

`connection.py` no se elimina hasta que `backend_07` termine de migrar
todos los repos. En ese momento, `backend_09` lo retira.

## D3 — Pragmas de SQLite via event.listen

El evento `"connect"` se dispara cada vez que el pool crea una nueva
conexión DBAPI. Los pragmas de sesión (`WAL`, `foreign_keys`) se aplican
ahí, no en el engine (son de sesión, no de base).

Esto reemplaza los `PRAGMA` de `get_connection()` para las conexiones
que pasen por el engine.

## D4 — Config

`config.py` añade:
```python
DB_BACKEND = os.getenv("DB_BACKEND", "sqlite")
DATABASE_URL = os.getenv("DATABASE_URL", "")
```

`.env.example` documenta:
```
DB_BACKEND=sqlite
# DATABASE_URL=postgresql+psycopg://user:pass@host:5432/zeci
```

## Alternativa descartada

**Crear un módulo `src/infrastructure/db/engine.py` separado.** El engine
es un singleton que `Container` ya gestiona. Crear otro módulo sería
duplicar la responsabilidad del composition root.
