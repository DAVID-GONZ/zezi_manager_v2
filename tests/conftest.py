"""
conftest.py — Fixtures de base de datos para ZECI Manager v2.0
===============================================================

Fixtures disponibles y su alcance:

  db_schema   (session)   — BD SQLite en memoria con el schema aplicado.
                            No contiene datos. Base para fixtures más específicos.

  db_seed     (function)  — BD con seed_test aplicado. Se recrea por test.
                            Garantiza aislamiento total entre tests.

  db_conn     (function)  — Conexión lista a usar (con db_seed aplicado).
                            El shortcut más común para tests de repositorios.

  seed_result (function)  — SeedResult del seed_test. Da acceso a IDs
                            sin necesidad de hacer queries.

Uso típico en un test de repositorio:

    def test_listar_estudiantes(db_conn, seed_result):
        repo = SqliteEstudianteRepository(conn=db_conn)
        estudiantes = repo.listar_activos()
        assert len(estudiantes) == len(seed_result.estudiante_ids)

Uso en un test de servicio (con FakeRepository, sin BD):

    def test_matricular(estudiante_service):
        # No necesita ningún fixture de BD — usa FakeRepository
        est = estudiante_service.matricular(NuevoEstudianteDTO(...))
        assert est.es_activo

Aislamiento:
  - Todos los fixtures de BD usan SQLite en memoria (':memory:').
  - Cada test con alcance 'function' recibe una BD nueva (no comparte estado).
  - Los fixtures de alcance 'session' no modifican datos — solo crean el schema.
"""

from __future__ import annotations

import sqlite3
import logging
import pytest

logging.disable(logging.CRITICAL)   # silenciar logs durante tests


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _apply_schema(conn: sqlite3.Connection) -> None:
    """Aplica SCHEMA, INDICES y TRIGGERS a una conexión en memoria."""
    # Import tardío para no romper si el módulo tiene errores durante discovery
    from src.infrastructure.db.schema import SCHEMA, INDICES, TRIGGERS

    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    for sql in SCHEMA:
        conn.execute(sql)
    for sql in INDICES:
        conn.execute(sql)
    for sql in TRIGGERS:
        conn.execute(sql)

    conn.commit()


# ---------------------------------------------------------------------------
# Fixture: schema solamente (sin datos)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_schema() -> sqlite3.Connection:
    """
    BD en memoria con el schema aplicado y sin datos.
    Alcance de sesión: se crea una vez y se comparte (solo lectura útil).
    No usar directamente en tests que modifican datos.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    _apply_schema(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Fixture: schema + seed_test (un test = una BD nueva)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_seed():
    """
    BD en memoria con seed_test aplicado.
    Se recrea por cada test — aislamiento total.

    Yields:
        tuple[sqlite3.Connection, SeedResult]
    """
    from src.infrastructure.db.seed import seed_test, _fast_hasher

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    _apply_schema(conn)
    result = seed_test(conn, anio=2025, hasher=_fast_hasher)
    conn.commit()

    yield conn, result

    conn.close()


@pytest.fixture(scope="function")
def db_conn(db_seed):
    """
    Shortcut: retorna solo la conexión de db_seed.
    Útil cuando el test no necesita acceder a SeedResult.
    """
    conn, _ = db_seed
    return conn


@pytest.fixture(scope="function")
def seed_result(db_seed):
    """
    Shortcut: retorna solo el SeedResult de db_seed.
    Útil cuando el test necesita IDs pero delega la conexión al repositorio.
    """
    _, result = db_seed
    return result


# ---------------------------------------------------------------------------
# Fixture: BD de integración con seed_dev (más datos, más lento)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_dev():
    """
    BD en memoria con seed_dev aplicado (dataset completo).
    Alcance de módulo — compartida entre tests del mismo archivo.
    Solo para tests de integración que necesitan datos realistas.

    Yields:
        tuple[sqlite3.Connection, SeedResult]
    """
    from src.infrastructure.db.seed import seed_dev, _fast_hasher

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    _apply_schema(conn)
    result = seed_dev(
        conn,
        anio=2025,
        hasher=_fast_hasher,
        total_estudiantes=12,
        seed_random=42,
    )
    conn.commit()

    yield conn, result

    conn.close()