"""Base para repositorios SQLAlchemy Core — ZECI Manager v2.0."""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


class RepositorioBase:
    """
    Base para repositorios SQLAlchemy Core.

    Constructor acepta una conexión SQLAlchemy inyectada (para tests o
    transacciones externas). Si es None, cada operación abre su propia
    conexión desde Container.engine().
    """

    def __init__(self, conn=None, tabla: Table | None = None):
        self._conn = conn
        self._tabla = tabla

    @contextmanager
    def _get_conn(self):
        """Yield una conexión SQLAlchemy. Si _conn es None, abre una nueva."""
        if self._conn is not None:
            yield self._conn
        else:
            from container import Container
            with Container.engine().connect() as conn:
                yield conn

    def _select(self, *cols):
        """Construye un SELECT sobre _tabla. Sin columnas = SELECT *."""
        if cols:
            return select(*cols)
        return select(self._tabla)

    def _execute_insert(self, conn, stmt) -> int:
        """Ejecuta INSERT y retorna la PK insertada."""
        result = conn.execute(stmt)
        return result.inserted_primary_key[0]

    def _upsert(self, tabla: Table, values: dict, conflict_cols: list[str], update_cols: list[str]):
        """
        Construye un upsert portable SQLite.
        Para Postgres (backend_09) se usará sqlalchemy.dialects.postgresql.insert.
        """
        stmt = sqlite_insert(tabla).values(**values)
        set_ = {col: getattr(stmt.excluded, col) for col in update_cols}
        return stmt.on_conflict_do_update(
            index_elements=conflict_cols,
            set_=set_,
        )
