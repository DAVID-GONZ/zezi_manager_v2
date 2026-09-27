"""Factory de engine para tests de BD — agnóstica del backend."""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool


def create_test_engine(backend: str = "sqlite"):
    """Crea y devuelve un SQLAlchemy Engine de test configurado.

    Usa StaticPool para que todas las conexiones del pool apunten a la misma
    conexión DBAPI subyacente — imprescindible con SQLite ``":memory:"``.
    Habilita ``PRAGMA foreign_keys = ON`` en cada nueva conexión DBAPI.

    Lanza ``ValueError`` si el backend no está soportado.
    """
    if backend == "sqlite":
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys = ON")

        return engine

    if backend == "postgres":
        import os

        import pytest
        from sqlalchemy import text as _text

        url = os.getenv("DATABASE_URL")
        if not url:
            pytest.skip("DATABASE_URL no definida — Postgres no disponible")
        engine = create_engine(url, echo=False, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                conn.execute(_text("SELECT 1"))
        except Exception:
            pytest.skip("Postgres no accesible (¿Docker corriendo?)")
        return engine

    raise ValueError(
        f"Backend no soportado: {backend!r}. Backends disponibles: sqlite, postgres"
    )
