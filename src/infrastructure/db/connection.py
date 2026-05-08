"""
Gestión de conexiones SQLite — ZECI Manager v2.0
=================================================

Principios de diseño:
  - Sin efectos secundarios al importar (no hay logging ni I/O a nivel de módulo).
  - `get_connection` acepta un `db_path` opcional para facilitar tests.
  - La ruta de BD se resuelve en orden: argumento explícito → override de test
    → config.py → fallback relativo al proyecto.
  - WAL mode + foreign keys habilitados en cada conexión (son pragmas de sesión,
    no persisten entre conexiones).
"""

from __future__ import annotations

import os
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("DB.CONNECTION")


# ---------------------------------------------------------------------------
# Resolución de la ruta de la base de datos
# ---------------------------------------------------------------------------

def _resolve_db_path() -> Path:
    """
    Determina la ruta de la BD en tiempo de ejecución.

    Orden de prioridad:
      1. DB_PATH_OVERRIDE (variable de entorno) — solo activo durante tests
         (PYTEST_CURRENT_TEST la activa pytest automáticamente).
      2. DATABASE_PATH de config.py.
      3. Fallback: <raíz_del_proyecto>/data/app.db
    """
    in_test = os.getenv("PYTEST_CURRENT_TEST") is not None
    override = os.getenv("DB_PATH_OVERRIDE")

    if in_test and override:
        return Path(override)

    try:
        from config import DATABASE_PATH  # noqa: PLC0415
        return DATABASE_PATH
    except ImportError:
        # config.py todavía no existe o el proyecto se importa en aislamiento.
        # Se usa la ruta convencional relativa a la raíz del proyecto.
        project_root = Path(__file__).parents[3]
        return project_root / "data" / "app.db"


# Ruta activa. Se calcula una sola vez al cargar el módulo.
DB_PATH: Path = _resolve_db_path()


# ---------------------------------------------------------------------------
# Normalización de parámetros (compatibilidad con numpy/pandas)
# ---------------------------------------------------------------------------

def _normalize_param(value: object) -> object:
    """
    Convierte escalares numpy/pandas a tipos nativos de Python.
    SQLite no acepta np.int64, np.float32, etc. directamente.
    """
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    return value


def _normalize_params(params: tuple | list | None) -> tuple:
    """Normaliza una secuencia de parámetros para SQLite."""
    if not params:
        return ()
    if not isinstance(params, (tuple, list)):
        params = (params,)
    return tuple(_normalize_param(p) for p in params)


# ---------------------------------------------------------------------------
# Context manager de conexión
# ---------------------------------------------------------------------------

@contextmanager
def get_connection(
    db_path: Path | str | None = None,
    timeout: float = 5.0,
) -> Iterator[sqlite3.Connection]:
    """
    Context manager que abre, configura y cierra una conexión SQLite.

    Configuración aplicada en cada conexión:
      - WAL mode: permite lecturas concurrentes sin bloquear escrituras.
      - foreign_keys = ON: habilita integridad referencial (ON DELETE CASCADE, etc.).
      - row_factory = sqlite3.Row: acceso a columnas por nombre.
      - synchronous = NORMAL: balance razonable entre durabilidad y velocidad.
      - cache_size = -64000: 64 MB de caché en memoria.

    Args:
        db_path:  Ruta explícita a la BD. Si es None se usa DB_PATH.
                  Pasar ":memory:" para tests en memoria.
        timeout:  Segundos de espera antes de lanzar OperationalError
                  cuando la BD está bloqueada.

    Yields:
        sqlite3.Connection configurada y lista para usar.

    Example:
        >>> with get_connection() as conn:
        ...     conn.execute("SELECT 1")

        >>> # En tests
        >>> with get_connection(":memory:") as conn:
        ...     conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    """
    path = Path(db_path) if db_path and str(db_path) != ":memory:" else (
        Path(":memory:") if db_path == ":memory:" else DB_PATH
    )

    # Crear directorio de datos si no existe (solo para ficheros reales)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(
            str(path),
            check_same_thread=False,   # NiceGUI usa múltiples hilos
            timeout=timeout,
        )

        conn.execute(f"PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=-64000;")
        conn.row_factory = sqlite3.Row

        logger.debug("Conexión abierta: %s", path)
        yield conn

    except sqlite3.Error as exc:
        logger.error("Error de conexión SQLite [%s]: %s", path, exc)
        raise

    finally:
        if conn:
            try:
                conn.close()
                logger.debug("Conexión cerrada: %s", path)
            except Exception as exc:
                logger.warning("Error cerrando conexión: %s", exc)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def verify_db_integrity(db_path: Path | str | None = None) -> bool:
    """
    Ejecuta PRAGMA integrity_check sobre la BD.

    Returns:
        True si la BD está íntegra.
    """
    try:
        with get_connection(db_path) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()
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
    "get_connection",
    "DB_PATH",
    "verify_db_integrity",
    "_normalize_params",   # usado internamente por queries.py
]