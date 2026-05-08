"""
Módulo de base de datos — src/infrastructure/db
================================================

Punto de entrada único para toda la capa de acceso a datos.
Los repositorios importan desde aquí; las capas superiores no importan
nada de este módulo directamente.

    from src.infrastructure.db import fetch_all, execute, get_scalar
    from src.infrastructure.db import init_db, seed_base, seed_dev, seed_test

Submódulos:
  connection  — get_connection, DB_PATH, verify_db_integrity
  queries     — fetch_df, fetch_one, fetch_all, get_scalar, execute
  schema      — init_db, get_db_stats, SCHEMA, INDICES, TRIGGERS
  seed        — seed_base, seed_dev, seed_test, SeedResult
"""

from .connection import get_connection, DB_PATH, verify_db_integrity
from .queries import fetch_df, fetch_one, fetch_all, get_scalar, execute
from .schema import init_db, get_db_stats, SCHEMA, INDICES, TRIGGERS
from .seed import seed_base, seed_dev, seed_test, SeedResult

__all__ = [
    # Conexión
    "get_connection",
    "DB_PATH",
    "verify_db_integrity",
    # Lectura
    "fetch_df",
    "fetch_one",
    "fetch_all",
    "get_scalar",
    # Escritura
    "execute",
    # Esquema
    "init_db",
    "get_db_stats",
    "SCHEMA",
    "INDICES",
    "TRIGGERS",
    # Seed
    "seed_base",
    "seed_dev",
    "seed_test",
    "SeedResult",
]