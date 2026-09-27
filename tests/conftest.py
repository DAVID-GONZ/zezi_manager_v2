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

import logging

import pytest

from tests.db_engine import create_test_engine

logging.disable(logging.CRITICAL)   # silenciar logs durante tests

# Plugin headless de NiceGUI (aporta el fixture `user` para los tests e2e). Debe
# declararse en el conftest RAÍZ (pytest prohíbe `pytest_plugins` en conftests
# anidados). Efectos globales inocuos: reubica el storage de NiceGUI a un temp y
# registra el marker `nicegui_main_file`. El fixture `user` solo se instancia
# donde se pide (tests/e2e/). Se usa `user_plugin` (no `plugin`) para no exigir
# selenium.
pytest_plugins = ["nicegui.testing.user_plugin"]


# ---------------------------------------------------------------------------
# Auto-marcado por ubicación y por fixture de BD
# ---------------------------------------------------------------------------
# Así `-m "not integration"` (modo `rapido` del runner / hook pre-push) excluye
# de verdad la carpeta integration/, sin tener que decorar cada test a mano.
# Los tests bajo unit/ reciben `unit`; los de integration/, `integration`.
#
# El marker `repo` identifica tests que dependen del backend de BD (SQLite/Postgres).
# Se aplica por dos vías:
#   1. Por carpeta: todo test en tests/integration/ recibe `repo` además de `integration`.
#   2. Por fixture: todo test que solicite db_conn, db_seed, seed_result o db_dev
#      recibe `repo` aunque esté fuera de integration/.

_BD_FIXTURES = frozenset({"db_conn", "db_seed", "seed_result", "db_dev"})


def pytest_addoption(parser):
    parser.addoption(
        "--backend",
        default="sqlite",
        choices=["sqlite"],
        help="Backend de BD para tests de repositorio",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        ruta = str(item.fspath).replace("\\", "/")
        if "/tests/integration/" in ruta:
            item.add_marker("integration")
            item.add_marker("repo")
        elif "/tests/unit/" in ruta:
            item.add_marker("unit")
        elif "/tests/e2e/" in ruta:
            item.add_marker("e2e")
        elif "/tests/browser/" in ruta:
            item.add_marker("browser")
        # Marcado por fixture para tests fuera de integration/
        if _BD_FIXTURES & set(item.fixturenames):
            item.add_marker("repo")


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _apply_schema(conn) -> None:
    """Aplica el MetaData de schema.py a la conexión entregada por create_test_engine."""
    # Import tardío para no romper si el módulo tiene errores durante discovery
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from src.infrastructure.db.schema import metadata

    engine = create_engine(
        "sqlite://",
        creator=lambda: conn,
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    conn.commit()


# ---------------------------------------------------------------------------
# Fixture: schema solamente (sin datos)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_schema(request):
    """
    BD en memoria con el schema aplicado y sin datos.
    Alcance de sesión: se crea una vez y se comparte (solo lectura útil).
    No usar directamente en tests que modifican datos.
    """
    conn = create_test_engine(request.config.getoption("--backend"))
    _apply_schema(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Fixture: schema + seed_test (un test = una BD nueva)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_seed(request):
    """
    BD en memoria con seed_test aplicado.
    Se recrea por cada test — aislamiento total.

    Yields:
        tuple[Connection, SeedResult]
    """
    from src.infrastructure.db.seed import _fast_hasher, seed_test

    conn = create_test_engine(request.config.getoption("--backend"))
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
def db_dev(request):
    """
    BD en memoria con seed_dev aplicado (dataset completo).
    Alcance de módulo — compartida entre tests del mismo archivo.
    Solo para tests de integración que necesitan datos realistas.

    Yields:
        tuple[Connection, SeedResult]
    """
    from src.infrastructure.db.seed import _fast_hasher, seed_dev

    conn = create_test_engine(request.config.getoption("--backend"))
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
