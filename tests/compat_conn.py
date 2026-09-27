"""Compatibility connection wrapper for migrating tests from sqlite3 to SQLAlchemy.

Provides :class:`CompatConnection`, a thin wrapper around a SQLAlchemy ``Connection``
that also understands the sqlite3-style calling conventions used in many existing
test files:

* ``conn.execute("SQL with ? placeholders", (p1, p2))`` – automatically converts
  positional ``?`` markers to SQLAlchemy named params (``:_p0``, ``:_p1``, …).
* ``conn.execute(SA construct)``                         – passed straight through.
* ``conn.cursor()``                                      – returns the raw
  ``sqlite3.Cursor`` for test helpers that use the native cursor API.
* ``conn.commit() / rollback() / close()``               – delegates to SA.
* ``row["col"]`` access on results                       – works natively because
  SQLAlchemy 2.x ``Row`` objects support column-name indexing.

Usage in a fixture::

    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    metadata.create_all(engine)
    sa_conn = engine.connect()
    raw = sa_conn.connection.driver_connection
    raw.row_factory = sqlite3.Row      # needed by seed_test / seed_dev
    seed_test(raw, ...)
    raw.commit()                       # commit before handing to tests
    yield CompatConnection(sa_conn)
    sa_conn.close()
    engine.dispose()
"""
from __future__ import annotations


class CompatConnection:
    """SQLAlchemy Connection wrapper with sqlite3-compatible execute API."""

    # Consola UTF-8 — bloque copiado de check_design.py para robustez en cp1252
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

    def __init__(self, sa_conn) -> None:
        self._sa = sa_conn
        # Raw sqlite3.Connection – shared underlying DBAPI connection
        self._raw = sa_conn.connection.driver_connection

    # ------------------------------------------------------------------
    # Core execute – handles both string SQL (sqlite3-style) and SA constructs
    # ------------------------------------------------------------------

    def execute(self, sql, params=None):
        """Execute SQL.

        * If *sql* is a plain string: routes through the raw sqlite3 connection
          so that ``sqlite3.Row`` factory applies and ``row["col"]`` string
          subscript works. Raw and SA share the same underlying DBAPI connection
          (StaticPool), so uncommitted SA writes are immediately visible.
          sqlite3 uses ``?`` placeholders natively — no conversion needed.
        * If *sql* is a SQLAlchemy construct (``Select``, ``Insert``, etc.):
          delegates directly to the underlying SA connection.
        """
        if isinstance(sql, str):
            return self._raw.execute(sql, params if params is not None else [])

        # SQLAlchemy construct
        if params is not None:
            return self._sa.execute(sql, params)
        return self._sa.execute(sql)

    # ------------------------------------------------------------------
    # Bulk insert – for seed functions that use executemany
    # ------------------------------------------------------------------

    def executemany(self, sql: str, params_seq) -> None:
        """Bulk insert with sqlite3-style positional ``?`` placeholders.

        Converts to named params and delegates to SA's bulk execute so that
        SA's autobegin is triggered (required for ``commit()`` to work).
        """
        from sqlalchemy import text as sa_text

        params_list = list(params_seq)
        if not params_list:
            return
        n = len(params_list[0])
        keys = [f"_p{i}" for i in range(n)]
        # Replace each ? with :_p0, :_p1, …
        parts = sql.split("?")
        named_sql = parts[0]
        for i, part in enumerate(parts[1:]):
            named_sql += f":{keys[i]}" + part
        named_params = [{keys[i]: row[i] for i in range(n)} for row in params_list]
        self._sa.execute(sa_text(named_sql), named_params)

    # ------------------------------------------------------------------
    # Raw cursor – for test helpers that use the native sqlite3 API
    # ------------------------------------------------------------------

    def cursor(self):
        """Return the raw sqlite3 cursor.

        Used by test helpers (e.g. ``test_generacion_estres.py``) that use
        ``cur.execute("INSERT ...", ?)`` and ``cur.lastrowid`` directly.
        Changes made via this cursor are committed by ``compat_conn.commit()``.
        """
        return self._raw.cursor()

    # ------------------------------------------------------------------
    # Transaction control
    # ------------------------------------------------------------------

    def commit(self) -> None:
        """Commit the current transaction.

        Falls back to raw ``sqlite3.Connection.commit()`` when SA has no active
        autobegin transaction (e.g. after raw cursor operations without any SA
        execute to trigger autobegin).
        """
        from sqlalchemy.exc import InvalidRequestError

        try:
            self._sa.commit()
        except InvalidRequestError:
            self._raw.commit()

    def rollback(self) -> None:
        self._sa.rollback()

    def close(self) -> None:
        self._sa.close()

    # ------------------------------------------------------------------
    # Context manager (pass-through)
    # ------------------------------------------------------------------

    def __enter__(self) -> CompatConnection:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Attribute delegation – exposes SA Connection attributes (e.g. .connection)
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> object:
        return getattr(self._sa, name)
