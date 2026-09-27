"""
Tests de integración — convivencia_15: alerta de seguimiento requerido.

Cubre:
  - test_crear_alerta_seguimiento_requerido  → INSERT con el nuevo tipo y
    usuario_destino_id se guarda y se lee correctamente via el repo.
  - test_migracion_check_idempotente         → llamar create_schema dos veces
    sobre la misma BD en memoria no lanza excepción.
"""
from __future__ import annotations

import pytest

from src.domain.models.alerta import Alerta, NivelAlerta, TipoAlerta
from src.infrastructure.db.repositories.sqla_alerta_repo import SqlaAlertaRepository
from src.infrastructure.db.schema import metadata
from src.infrastructure.db.seed import seed_test

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn_con_schema():
    """Conexión SQLite en memoria con schema completo + seed de test."""
    import sqlite3 as _sqlite3

    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import StaticPool

    from src.infrastructure.db.schema import metadata
    from tests.compat_conn import CompatConnection

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    metadata.create_all(engine)
    sa_conn = engine.connect()
    raw = sa_conn.connection.driver_connection
    raw.row_factory = _sqlite3.Row
    seed_test(sa_conn)
    sa_conn.commit()
    yield CompatConnection(sa_conn)
    sa_conn.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_crear_alerta_seguimiento_requerido(conn_con_schema):
    """
    Inserta una alerta de tipo SEGUIMIENTO_REQUERIDO apuntando a un usuario
    destino y verifica que el repositorio la devuelva con todos los campos.
    """
    conn = conn_con_schema
    repo = SqlaAlertaRepository(conn)

    # usuario_destino_id = 1 (admin_test, sembrado por seed_test)
    alerta = Alerta(
        estudiante_id=1,
        tipo_alerta=TipoAlerta.SEGUIMIENTO_REQUERIDO,
        nivel=NivelAlerta.ADVERTENCIA,
        descripcion="Requiere seguimiento por parte del director de grupo.",
        usuario_destino_id=1,
    )

    guardada = repo.guardar_alerta(alerta)
    assert guardada.id is not None, "El repositorio debe asignar un id al guardar"

    recuperada = repo.get_alerta(guardada.id)
    assert recuperada is not None, "La alerta debe poder recuperarse por id"
    assert recuperada.tipo_alerta == TipoAlerta.SEGUIMIENTO_REQUERIDO
    assert recuperada.usuario_destino_id == 1
    assert recuperada.descripcion == alerta.descripcion


def test_migracion_check_idempotente():
    """
    Llamar metadata.create_all dos veces sobre el mismo engine no debe
    lanzar ninguna excepción (idempotencia garantizada por checkfirst=True).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    metadata.create_all(engine)
    engine.dispose()
