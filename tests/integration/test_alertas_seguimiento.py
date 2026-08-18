"""
Tests de integración — convivencia_15: alerta de seguimiento requerido.

Cubre:
  - test_crear_alerta_seguimiento_requerido  → INSERT con el nuevo tipo y
    usuario_destino_id se guarda y se lee correctamente via el repo.
  - test_migracion_check_idempotente         → llamar create_schema dos veces
    sobre la misma BD en memoria no lanza excepción.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.domain.models.alerta import Alerta, NivelAlerta, TipoAlerta
from src.infrastructure.db.repositories.sqlite_alerta_repo import SqliteAlertaRepository
from src.infrastructure.db.schema import create_schema
from src.infrastructure.db.seed import seed_test

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn_con_schema():
    """Conexión SQLite en memoria con schema completo + seed de test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    seed_test(conn)
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_crear_alerta_seguimiento_requerido(conn_con_schema):
    """
    Inserta una alerta de tipo SEGUIMIENTO_REQUERIDO apuntando a un usuario
    destino y verifica que el repositorio la devuelva con todos los campos.
    """
    conn = conn_con_schema
    repo = SqliteAlertaRepository(conn)

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
    Llamar create_schema dos veces sobre la misma BD en memoria no debe
    lanzar ninguna excepción (idempotencia garantizada por IF NOT EXISTS).
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        create_schema(conn)
        create_schema(conn)
    finally:
        conn.close()
