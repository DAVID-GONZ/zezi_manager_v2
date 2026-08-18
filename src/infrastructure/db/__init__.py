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

from .connection import DB_PATH, get_connection, verify_db_integrity
from .queries import execute, fetch_all, fetch_df, fetch_one, get_scalar
from .schema import INDICES, SCHEMA, TRIGGERS, get_db_stats, init_db
from .seed import SeedResult, seed_base, seed_dev, seed_test

__all__ = [
    "DB_PATH",
    "INDICES",
    "SCHEMA",
    "TRIGGERS",
    "SeedResult",
    # Escritura
    "execute",
    "fetch_all",
    # Lectura
    "fetch_df",
    "fetch_one",
    # Conexión
    "get_connection",
    "get_db_stats",
    "get_scalar",
    # Esquema
    "init_db",
    # Seed
    "seed_base",
    "seed_dev",
    "seed_test",
    "verify_db_integrity",
]
