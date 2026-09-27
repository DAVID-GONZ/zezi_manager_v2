"""
Módulo de base de datos — src/infrastructure/db
================================================

Punto de entrada único para toda la capa de acceso a datos.
Los repositorios importan desde aquí; las capas superiores no importan
nada de este módulo directamente.

    from src.infrastructure.db import metadata, seed_base, seed_dev, seed_test

Submódulos:
  connection  — get_connection (shim), DB_PATH, verify_db_integrity
  queries     — fetch_df, fetch_one, fetch_all, get_scalar, execute (shim)
  schema      — metadata (create_all via metadata.create_all(engine))
  seed        — seed_base, seed_dev, seed_test, SeedResult
"""

from .connection import DB_PATH, get_connection, verify_db_integrity
from .queries import execute, fetch_all, fetch_df, fetch_one, get_scalar
from .schema import metadata
from .seed import SeedResult, seed_base, seed_dev, seed_test

__all__ = [
    "DB_PATH",
    "SeedResult",
    # Escritura (shim — usar Container.engine() directamente en repos nuevos)
    "execute",
    "fetch_all",
    # Lectura (shim)
    "fetch_df",
    "fetch_one",
    # Conexión (shim)
    "get_connection",
    "get_scalar",
    "metadata",
    # Seed
    "seed_base",
    "seed_dev",
    "seed_test",
    "verify_db_integrity",
]
