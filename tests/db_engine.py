"""Factory de engine para tests de BD — agnóstica del backend."""

from __future__ import annotations

import sqlite3


def create_test_engine(backend: str = "sqlite") -> sqlite3.Connection:
    """Crea y devuelve una conexión de test configurada para el backend indicado.

    Configura `foreign_keys=ON` y `row_factory=sqlite3.Row` para que los repos
    los reciban listos. Lanza `ValueError` si el backend no está soportado.
    """
    if backend == "sqlite":
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn
    raise ValueError(f"Backend no soportado: {backend!r}. Backends disponibles: sqlite")
