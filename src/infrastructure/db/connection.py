"""
Shim de compatibilidad con la API de conexión — ZECI Manager v2.0
==================================================================

Desde backend_07 la capa de acceso a datos usa SQLAlchemy Core directamente
(Container.engine() / Container.connection()). Este módulo provee compatibilidad
para los pocos llamadores que quedan fuera de esa migración:

  verify_db_integrity() — /health, ObservabilidadService
  get_connection()       — shim para tests e2e y tests de contenedor
  DB_PATH                — ruta de la BD; leída por e2e_app.py

No importa sqlite3: las operaciones de BD pasan por Container.engine().
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("DB.CONNECTION")


# ---------------------------------------------------------------------------
# Resolución de la ruta de la base de datos
# ---------------------------------------------------------------------------


def _resolve_db_path() -> Path:
    """
    Determina la ruta de la BD en tiempo de ejecución.

    Orden de prioridad:
      1. DB_PATH_OVERRIDE (variable de entorno) — solo activo durante tests.
      2. DATABASE_PATH de config.py.
      3. Fallback: <raíz_del_proyecto>/data/app.db
    """
    in_test = os.getenv("PYTEST_CURRENT_TEST") is not None
    override = os.getenv("DB_PATH_OVERRIDE")

    if in_test and override:
        return Path(override)

    try:
        from config import DATABASE_PATH

        return DATABASE_PATH
    except ImportError:
        project_root = Path(__file__).parents[3]
        return project_root / "data" / "app.db"


# Ruta activa. Se calcula una sola vez al cargar el módulo.
DB_PATH: Path = _resolve_db_path()


# ---------------------------------------------------------------------------
# Context manager de conexión (shim sobre Container.engine())
# ---------------------------------------------------------------------------


@contextmanager
def get_connection(
    db_path: Path | str | None = None,
    timeout: float = 5.0,
) -> Iterator:
    """
    Shim de compatibilidad: cede la conexión DBAPI del engine de Container.

    Para el backend SQLite devuelve un sqlite3.Connection real, de modo que
    los llamadores que usen .cursor(), .execute() o row_factory siguen
    funcionando sin cambios. El parámetro db_path ya no se usa; los tests
    deben configurar el engine vía DB_PATH_OVERRIDE o DATABASE_PATH en el
    entorno antes de que Container.engine() se inicialice.

    Yields:
        Conexión DBAPI del engine activo (sqlite3.Connection para SQLite).
    """
    from container import Container

    conn = Container.engine().raw_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def verify_db_integrity(db_path: Path | str | None = None) -> bool:
    """
    Ejecuta PRAGMA integrity_check sobre la BD vía SQLAlchemy.

    El parámetro db_path no se usa; la comprobación se realiza sobre el
    engine activo del Container.

    Returns:
        True si la BD está íntegra.
    """
    try:
        from container import Container

        with Container.engine().connect() as conn:
            result = conn.exec_driver_sql("PRAGMA integrity_check").fetchone()
            ok = result[0] == "ok"
            if ok:
                logger.info("Integridad de BD verificada: ok")
            else:
                logger.error("BD corrupta: %s", result[0])
            return ok
    except Exception as exc:
        logger.error("Error verificando integridad: %s", exc)
        return False


__all__ = [
    "DB_PATH",
    "get_connection",
    "verify_db_integrity",
]
