"""
Tests de integración para obs_01_huella_actor.

Verifica que la huella del actor y de la institución se graben correctamente
en audit_log, y que la cadena de integridad permanezca íntegra.
"""

from __future__ import annotations

import pytest

from src.infrastructure.db.repositories.sqla_auditoria_repo import (
    SqlaAuditoriaRepository,
)
from src.infrastructure.db.seed import _fast_hasher, seed_base
from src.services.contexto_actor import usar_actor
from src.services.contexto_tenant import usar_institucion


@pytest.fixture()
def db():
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
    seed_base(sa_conn, anio=2025, hasher=_fast_hasher)
    sa_conn.commit()
    yield CompatConnection(sa_conn)
    sa_conn.close()
    engine.dispose()


def test_audit_log_tiene_usuario_e_institucion(db):
    """Un cambio auditado con contexto activo debe registrar usuario_id e institucion_id."""
    from src.domain.models.auditoria import AccionCambio
    from src.services.auditoria_helpers import auditar_cambio

    repo = SqlaAuditoriaRepository(conn=db)

    # Obtener IDs reales del seed para satisfacer las FKs
    usuario_row = db.execute("SELECT id FROM usuarios ORDER BY id LIMIT 1").fetchone()
    institucion_row = db.execute("SELECT id FROM instituciones ORDER BY id LIMIT 1").fetchone()
    assert usuario_row is not None, "No hay usuarios en la BD de prueba"
    assert institucion_row is not None, "No hay instituciones en la BD de prueba"
    usuario_id = usuario_row["id"]
    institucion_id = institucion_row["id"]

    with usar_actor(usuario_id), usar_institucion(institucion_id):
        auditar_cambio(
            repo,
            accion=AccionCambio.CREATE,
            tabla="test_tabla",
            registro_id=1,
            nuevo={"campo": "valor"},
        )
    db.commit()

    row = db.execute(
        "SELECT usuario_id, institucion_id FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == usuario_id
    assert row["institucion_id"] == institucion_id


def test_cadena_integridad_preexistente_intacta(db):
    """Despues de escribir una fila, verificar_cadena_cambios() no detecta roturas."""
    from src.domain.models.auditoria import AccionCambio
    from src.services.auditoria_helpers import auditar_cambio

    repo = SqlaAuditoriaRepository(conn=db)

    # Usar actor y institucion NULL para evitar FK constraints
    with usar_actor(None), usar_institucion(None):
        auditar_cambio(
            repo,
            accion=AccionCambio.CREATE,
            tabla="t",
            registro_id=1,
            nuevo={"x": 1},
        )
    db.commit()

    id_roto = repo.verificar_cadena_cambios()
    assert id_roto is None, f"Cadena rota en id={id_roto}"


def test_sin_contexto_actor_usuario_id_es_none(db):
    """Sin contexto de actor, usuario_id en audit_log debe ser None."""
    from src.domain.models.auditoria import AccionCambio
    from src.services.auditoria_helpers import auditar_cambio
    from src.services.contexto_actor import limpiar_actor

    repo = SqlaAuditoriaRepository(conn=db)

    limpiar_actor()  # asegurar que no hay actor activo
    auditar_cambio(
        repo,
        accion=AccionCambio.CREATE,
        tabla="test_sin_actor",
        registro_id=5,
        nuevo={"y": 2},
    )
    db.commit()

    row = db.execute(
        "SELECT usuario_id FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    assert row["usuario_id"] is None
