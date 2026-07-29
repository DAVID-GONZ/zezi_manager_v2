"""
tests/unit/interface/test_inicio_seguimientos.py
=================================================
Tests para el panel de seguimientos pendientes del dashboard (convivencia_19).

Cubre:
  - AlertaService.listar_alertas_para_usuario filtra por destinatario y tipo
  - Resultado vacío cuando no hay alertas para ese usuario
  - SqliteAlertaRepository.listar_alertas_por_destinatario filtra correctamente
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.domain.models.alerta import Alerta, NivelAlerta, TipoAlerta
from src.infrastructure.db.repositories.sqlite_alerta_repo import SqliteAlertaRepository
from src.services.alerta_service import AlertaService


# =============================================================================
# Fixtures
# =============================================================================


def _alerta_seguimiento(id: int, usuario_destino_id: int) -> Alerta:
    return Alerta(
        id=id,
        estudiante_id=1,
        tipo_alerta=TipoAlerta.SEGUIMIENTO_REQUERIDO,
        nivel=NivelAlerta.ADVERTENCIA,
        descripcion="Estudiante requiere seguimiento de convivencia",
        fecha_generacion=datetime(2026, 7, 1, 10, 0),
        resuelta=False,
        usuario_destino_id=usuario_destino_id,
    )


def _alerta_otro_tipo(id: int, usuario_destino_id: int) -> Alerta:
    return Alerta(
        id=id,
        estudiante_id=2,
        tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
        nivel=NivelAlerta.ADVERTENCIA,
        descripcion="Exceso de faltas injustificadas",
        fecha_generacion=datetime(2026, 7, 2, 10, 0),
        resuelta=False,
        usuario_destino_id=usuario_destino_id,
    )


# =============================================================================
# Tests de AlertaService
# =============================================================================


class TestAlertaServiceListarParaUsuario:

    def test_filtra_por_destinatario_y_tipo_seguimiento(self):
        """listar_alertas_para_usuario llama al repo con el usuario_id y tipo correcto."""
        alertas = [_alerta_seguimiento(1, 42)]
        repo_mock = MagicMock()
        repo_mock.listar_alertas_por_destinatario.return_value = alertas

        service = AlertaService(repo=repo_mock)
        resultado = service.listar_alertas_para_usuario(usuario_id=42)

        repo_mock.listar_alertas_por_destinatario.assert_called_once_with(
            usuario_destino_id=42,
            tipo="seguimiento_requerido",
            solo_pendientes=True,
        )
        assert resultado == alertas

    def test_retorna_lista_vacia_cuando_no_hay_alertas(self):
        """listar_alertas_para_usuario retorna lista vacía si no hay alertas."""
        repo_mock = MagicMock()
        repo_mock.listar_alertas_por_destinatario.return_value = []

        service = AlertaService(repo=repo_mock)
        resultado = service.listar_alertas_para_usuario(usuario_id=99)

        assert resultado == []

    def test_pasa_solo_pendientes_false_al_repo(self):
        """Con solo_pendientes=False el parámetro llega correctamente al repo."""
        repo_mock = MagicMock()
        repo_mock.listar_alertas_por_destinatario.return_value = []

        service = AlertaService(repo=repo_mock)
        service.listar_alertas_para_usuario(usuario_id=10, solo_pendientes=False)

        repo_mock.listar_alertas_por_destinatario.assert_called_once_with(
            usuario_destino_id=10,
            tipo="seguimiento_requerido",
            solo_pendientes=False,
        )


# =============================================================================
# Tests de SqliteAlertaRepository
# =============================================================================


def _crear_bd_en_memoria() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE alertas (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id           INTEGER NOT NULL DEFAULT 0,
            tipo_alerta             TEXT    NOT NULL,
            nivel                   TEXT    NOT NULL DEFAULT 'advertencia',
            descripcion             TEXT    NOT NULL,
            fecha_generacion        TEXT    NOT NULL,
            resuelta                INTEGER NOT NULL DEFAULT 0,
            fecha_resolucion        TEXT,
            usuario_resolucion_id   INTEGER,
            observacion_resolucion  TEXT,
            usuario_destino_id      INTEGER
        )
    """)
    conn.commit()
    return conn


def _insertar_alerta(conn: sqlite3.Connection, tipo: str, usuario_destino_id: int,
                     resuelta: int = 0) -> None:
    fecha_res = datetime.now().isoformat() if resuelta else None
    usuario_res = 1 if resuelta else None
    conn.execute(
        """
        INSERT INTO alertas
            (estudiante_id, tipo_alerta, nivel, descripcion,
             fecha_generacion, resuelta, fecha_resolucion,
             usuario_resolucion_id, usuario_destino_id)
        VALUES (1, ?, 'advertencia', 'desc', ?, ?, ?, ?, ?)
        """,
        (tipo, datetime.now().isoformat(), resuelta,
         fecha_res, usuario_res, usuario_destino_id),
    )
    conn.commit()


class TestSqliteAlertaRepoListarPorDestinatario:

    def test_filtra_por_usuario_destino(self):
        conn = _crear_bd_en_memoria()
        _insertar_alerta(conn, "seguimiento_requerido", usuario_destino_id=10)
        _insertar_alerta(conn, "seguimiento_requerido", usuario_destino_id=20)

        repo = SqliteAlertaRepository(conn=conn)
        resultado = repo.listar_alertas_por_destinatario(usuario_destino_id=10)

        assert len(resultado) == 1
        assert resultado[0].usuario_destino_id == 10

    def test_filtra_por_tipo(self):
        conn = _crear_bd_en_memoria()
        _insertar_alerta(conn, "seguimiento_requerido", usuario_destino_id=5)
        _insertar_alerta(conn, "faltas_injustificadas", usuario_destino_id=5)

        repo = SqliteAlertaRepository(conn=conn)
        resultado = repo.listar_alertas_por_destinatario(
            usuario_destino_id=5,
            tipo="seguimiento_requerido",
        )

        assert len(resultado) == 1
        assert resultado[0].tipo_alerta == TipoAlerta.SEGUIMIENTO_REQUERIDO

    def test_vacio_cuando_no_hay_alertas_para_ese_usuario(self):
        conn = _crear_bd_en_memoria()
        _insertar_alerta(conn, "seguimiento_requerido", usuario_destino_id=99)

        repo = SqliteAlertaRepository(conn=conn)
        resultado = repo.listar_alertas_por_destinatario(usuario_destino_id=1)

        assert resultado == []

    def test_solo_pendientes_true_excluye_resueltas(self):
        conn = _crear_bd_en_memoria()
        _insertar_alerta(conn, "seguimiento_requerido", usuario_destino_id=7, resuelta=0)
        _insertar_alerta(conn, "seguimiento_requerido", usuario_destino_id=7, resuelta=1)

        repo = SqliteAlertaRepository(conn=conn)
        resultado = repo.listar_alertas_por_destinatario(
            usuario_destino_id=7,
            solo_pendientes=True,
        )

        assert len(resultado) == 1
        assert not resultado[0].resuelta

    def test_solo_pendientes_false_incluye_resueltas(self):
        conn = _crear_bd_en_memoria()
        _insertar_alerta(conn, "seguimiento_requerido", usuario_destino_id=7, resuelta=0)
        _insertar_alerta(conn, "seguimiento_requerido", usuario_destino_id=7, resuelta=1)

        repo = SqliteAlertaRepository(conn=conn)
        resultado = repo.listar_alertas_por_destinatario(
            usuario_destino_id=7,
            solo_pendientes=False,
        )

        assert len(resultado) == 2
