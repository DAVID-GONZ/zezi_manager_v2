# Diseño: backend_09_cierre_dual

## Punto de partida esperado (tras backend_08)

| Componente | Estado |
|---|---|
| Schema | MetaData SQLAlchemy, `create_all()` funciona en SQLite |
| Repos | 20 repos `sqla_*`, SQLAlchemy Core |
| Seeds | SQLAlchemy Core |
| connection.py | Eliminado |
| queries.py | Eliminado |
| conftest | `--backend=sqlite` funciona, `--backend=postgres` registrado pero no implementado |
| Suite | ~2,590 tests verdes en SQLite |

## D1 — Auditoría de vestigios sqlite3

Grep exhaustivo por `import sqlite3` en `src/`:

```bash
grep -rn "import sqlite3" src/
```

Si aparecen resultados → eliminar y reemplazar. Los únicos usos
legítimos serían en `tests/` (helpers de introspección de schema).

## D2 — Infraestructura Postgres en conftest

Extender `tests/db_engine.py` (creado en backend_02) para soportar
`--backend=postgres`:

```python
def create_test_engine(backend: str = "sqlite"):
    if backend == "sqlite":
        return create_engine("sqlite:///:memory:")
    elif backend == "postgres":
        url = os.getenv("DATABASE_URL")
        if not url:
            pytest.skip("DATABASE_URL no definida")
        engine = create_engine(url)
        # Verificar conexión
        try:
            engine.connect().close()
        except Exception:
            pytest.skip("Postgres no accesible")
        return engine
```

En conftest, extender `--backend` choices a `["sqlite", "postgres"]`.

## D3 — create_all en Postgres

`metadata.create_all(engine)` con un engine Postgres. Los tipos neutros
de backend_04 (`Integer`, `String`, `Numeric`, etc.) se traducen
automáticamente al dialecto Postgres.

Los triggers (declarados como `DDL`) necesitan adaptación:
- SQLite: `CREATE TRIGGER ... BEGIN ... END;`
- Postgres: `CREATE FUNCTION ... RETURNS TRIGGER` + `CREATE TRIGGER`.

Se resuelve con `DDL` condicional por dialecto o con `event.listen`
condicional.

## D4 — Upserts por dialecto

Los upserts de backend_07 usan `sqlite_insert().on_conflict_do_update()`.
Para Postgres, se usa `postgresql_insert().on_conflict_do_update()`.

El helper `_upsert()` del `RepositorioBase` ya detecta el dialecto.

## D5 — Tests skipeables

Tests que no pueden pasar en Postgres sin ajustes:
- Tests que usan `PRAGMA` (específicos de SQLite).
- Tests de triggers con sintaxis SQLite.
- Tests de funciones de fecha que difieren entre dialectos.

Se marcan con `@pytest.mark.skipif(backend == "postgres", reason="...")`.

## D6 — Limpieza final

Archivos a verificar/eliminar:
- `src/infrastructure/db/connection.py` — ya eliminado en backend_07.
- `src/infrastructure/db/queries.py` — ya eliminado en backend_07.
- Cualquier `sqlite_*_repo.py` remanente.
- `_normalize_params` sueltos.
- Tests que importan `sqlite3` sin necesidad.

## Alternativa descartada

**Posponer toda la infraestructura Postgres al momento de instalar Docker.**
La infraestructura de conftest se puede preparar ahora (con skip) y así
cuando Docker esté disponible, solo hay que descomentar.
