"""
Tests de integración — Entradas de seguimiento (convivencia_35).

Cubre: tabla creada en schema, modelos de dominio, repo (guardar/listar),
servicio (agregar_entrada_seguimiento, listar, agregar_seguimiento legacy),
migración de datos existentes.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.domain.models.convivencia import EntradaSeguimiento, NuevaEntradaSeguimientoDTO
from src.infrastructure.db.repositories.sqlite_convivencia_repo import (
    SqliteConvivenciaRepository,
)
from src.infrastructure.db.schema import create_schema
from src.infrastructure.db.seed import _fast_hasher, seed_base
from src.services.convivencia_service import ConvivenciaService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    seed_base(conn, anio=2025, hasher=_fast_hasher)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def repo(db):
    return SqliteConvivenciaRepository(conn=db)


@pytest.fixture()
def svc(repo):
    return ConvivenciaService(repo=repo)


def _insertar_registro(db) -> int:
    """Crea los registros mínimos y retorna el id de un registro de comportamiento."""
    anio_id = db.execute("SELECT id FROM configuracion_anio LIMIT 1").fetchone()["id"]
    grupo_id = db.execute(
        "INSERT INTO grupos (codigo, institucion_id) VALUES ('SEG-01', 1)"
    ).lastrowid
    est_id = db.execute(
        "INSERT INTO estudiantes (tipo_documento, numero_documento, nombre, apellido, "
        "grupo_id, fecha_ingreso, institucion_id) VALUES ('TI', '55500001', 'Est', 'Seg', ?, CURRENT_DATE, 1)",
        (grupo_id,),
    ).lastrowid
    periodo_id = db.execute(
        "INSERT INTO periodos (anio_id, nombre, numero, peso_porcentual) VALUES (?, 'P1', 1, 25.0)",
        (anio_id,),
    ).lastrowid
    reg_id = db.execute(
        "INSERT INTO registro_comportamiento "
        "(estudiante_id, grupo_id, periodo_id, tipo, descripcion) "
        "VALUES (?, ?, ?, 'dificultad', 'Incidente inicial')",
        (est_id, grupo_id, periodo_id),
    ).lastrowid
    db.commit()
    return reg_id


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_tabla_entradas_seguimiento_existe(db):
    filas = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entradas_seguimiento'"
    ).fetchall()
    assert len(filas) == 1


# ---------------------------------------------------------------------------
# Modelos de dominio
# ---------------------------------------------------------------------------


class TestEntradaSeguimiento:
    def test_defaults(self):
        e = EntradaSeguimiento(registro_id=1, texto="Primer seguimiento")
        assert e.id is None
        assert e.usuario_id is None
        assert e.usuario_nombre is None
        assert e.fecha is not None

    def test_texto_vacio_rechazado(self):
        with pytest.raises(Exception):
            EntradaSeguimiento(registro_id=1, texto="")

    def test_texto_demasiado_largo_rechazado(self):
        with pytest.raises(Exception):
            EntradaSeguimiento(registro_id=1, texto="x" * 2001)


class TestNuevaEntradaSeguimientoDTO:
    def test_valido(self):
        dto = NuevaEntradaSeguimientoDTO(registro_id=1, texto="  texto  ")
        assert dto.texto == "texto"

    def test_texto_vacio_rechazado(self):
        with pytest.raises(Exception):
            NuevaEntradaSeguimientoDTO(registro_id=1, texto="   ")


# ---------------------------------------------------------------------------
# Repositorio: guardar + listar
# ---------------------------------------------------------------------------


def test_guardar_entrada_asigna_id(repo, db):
    reg_id = _insertar_registro(db)
    entrada = EntradaSeguimiento(registro_id=reg_id, texto="Primer seguimiento")
    guardada = repo.guardar_entrada_seguimiento(entrada)
    db.commit()
    assert guardada.id is not None


def test_listar_entradas_orden_cronologico(repo, db):
    reg_id = _insertar_registro(db)
    repo.guardar_entrada_seguimiento(EntradaSeguimiento(registro_id=reg_id, texto="A"))
    repo.guardar_entrada_seguimiento(EntradaSeguimiento(registro_id=reg_id, texto="B"))
    repo.guardar_entrada_seguimiento(EntradaSeguimiento(registro_id=reg_id, texto="C"))
    db.commit()

    entradas = repo.listar_entradas_seguimiento(reg_id)
    assert len(entradas) == 3
    textos = [e.texto for e in entradas]
    assert textos == ["A", "B", "C"]


def test_listar_no_mezcla_registros(repo, db):
    reg_a = _insertar_registro(db)
    # Insertar segundo registro directamente
    grupo_id = db.execute("SELECT grupo_id FROM registro_comportamiento WHERE id = ?", (reg_a,)).fetchone()["grupo_id"]
    est_id = db.execute("SELECT estudiante_id FROM registro_comportamiento WHERE id = ?", (reg_a,)).fetchone()["estudiante_id"]
    periodo_id = db.execute("SELECT periodo_id FROM registro_comportamiento WHERE id = ?", (reg_a,)).fetchone()["periodo_id"]
    reg_b = db.execute(
        "INSERT INTO registro_comportamiento "
        "(estudiante_id, grupo_id, periodo_id, tipo, descripcion) VALUES (?, ?, ?, 'fortaleza', 'Otro')",
        (est_id, grupo_id, periodo_id),
    ).lastrowid
    db.commit()

    repo.guardar_entrada_seguimiento(EntradaSeguimiento(registro_id=reg_a, texto="Para A"))
    repo.guardar_entrada_seguimiento(EntradaSeguimiento(registro_id=reg_b, texto="Para B"))
    db.commit()

    assert len(repo.listar_entradas_seguimiento(reg_a)) == 1
    assert len(repo.listar_entradas_seguimiento(reg_b)) == 1


def test_listar_entradas_vacío_si_sin_entradas(repo, db):
    reg_id = _insertar_registro(db)
    assert repo.listar_entradas_seguimiento(reg_id) == []


# ---------------------------------------------------------------------------
# Servicio: agregar_entrada_seguimiento
# ---------------------------------------------------------------------------


def test_agregar_entrada_crea_historial(svc, db):
    reg_id = _insertar_registro(db)
    dto = NuevaEntradaSeguimientoDTO(registro_id=reg_id, texto="Primer avance")
    entrada = svc.agregar_entrada_seguimiento(dto)
    db.commit()

    assert entrada.id is not None
    entradas = svc.listar_entradas_seguimiento(reg_id)
    assert len(entradas) == 1
    assert entradas[0].texto == "Primer avance"


def test_agregar_multiples_entradas_no_borra_anteriores(svc, db):
    reg_id = _insertar_registro(db)
    for texto in ["Día 1", "Día 3", "Día 5"]:
        dto = NuevaEntradaSeguimientoDTO(registro_id=reg_id, texto=texto)
        svc.agregar_entrada_seguimiento(dto)
    db.commit()

    entradas = svc.listar_entradas_seguimiento(reg_id)
    assert len(entradas) == 3


def test_denormalizacion_actualiza_campo_legacy(svc, db):
    """R3: el campo seguimiento del registro queda con el texto de la última entrada."""
    reg_id = _insertar_registro(db)
    svc.agregar_entrada_seguimiento(NuevaEntradaSeguimientoDTO(registro_id=reg_id, texto="Primera"))
    db.commit()
    svc.agregar_entrada_seguimiento(NuevaEntradaSeguimientoDTO(registro_id=reg_id, texto="Última"))
    db.commit()

    fila = db.execute(
        "SELECT seguimiento FROM registro_comportamiento WHERE id = ?", (reg_id,)
    ).fetchone()
    assert fila["seguimiento"] == "Última"


# ---------------------------------------------------------------------------
# Servicio: agregar_seguimiento legacy (R8)
# ---------------------------------------------------------------------------


def test_agregar_seguimiento_legacy_crea_entrada(svc, db):
    reg_id = _insertar_registro(db)
    svc.agregar_seguimiento(reg_id, "Texto legacy")
    db.commit()

    entradas = svc.listar_entradas_seguimiento(reg_id)
    assert len(entradas) == 1
    assert entradas[0].texto == "Texto legacy"


def test_agregar_seguimiento_legacy_retorna_registro(svc, db):
    from src.domain.models.convivencia import RegistroComportamiento

    reg_id = _insertar_registro(db)
    resultado = svc.agregar_seguimiento(reg_id, "Legacy call")
    db.commit()

    assert isinstance(resultado, RegistroComportamiento)
    assert resultado.seguimiento == "Legacy call"


# ---------------------------------------------------------------------------
# Migración de datos existentes (R7)
# ---------------------------------------------------------------------------


def test_migracion_registros_con_seguimiento_legacy(db):
    """seed_base llama _migrate_entradas_seguimiento: registros con seguimiento != NULL
    deben tener una entrada correspondiente."""
    # Insertar un registro con seguimiento directamente en la BD
    anio_id = db.execute("SELECT id FROM configuracion_anio LIMIT 1").fetchone()["id"]
    grupo_id = db.execute(
        "INSERT INTO grupos (codigo, institucion_id) VALUES ('MIG-01', 1)"
    ).lastrowid
    est_id = db.execute(
        "INSERT INTO estudiantes (tipo_documento, numero_documento, nombre, apellido, "
        "grupo_id, fecha_ingreso, institucion_id) VALUES ('TI', '99911111', 'E', 'M', ?, CURRENT_DATE, 1)",
        (grupo_id,),
    ).lastrowid
    periodo_id = db.execute(
        "INSERT INTO periodos (anio_id, nombre, numero, peso_porcentual) VALUES (?, 'PM', 1, 25.0)",
        (anio_id,),
    ).lastrowid
    reg_id = db.execute(
        "INSERT INTO registro_comportamiento "
        "(estudiante_id, grupo_id, periodo_id, tipo, descripcion, seguimiento) "
        "VALUES (?, ?, ?, 'dificultad', 'Desc', 'Seguimiento previo')",
        (est_id, grupo_id, periodo_id),
    ).lastrowid
    db.commit()

    # Ejecutar la migración
    from src.infrastructure.db.seed import _migrate_entradas_seguimiento

    _migrate_entradas_seguimiento(db)
    db.commit()

    entradas = db.execute(
        "SELECT * FROM entradas_seguimiento WHERE registro_id = ?", (reg_id,)
    ).fetchall()
    assert len(entradas) == 1
    assert entradas[0]["texto"] == "Seguimiento previo"


def test_migracion_idempotente(db):
    """Llamar _migrate_entradas_seguimiento dos veces no duplica entradas."""
    from src.infrastructure.db.seed import _migrate_entradas_seguimiento

    anio_id = db.execute("SELECT id FROM configuracion_anio LIMIT 1").fetchone()["id"]
    grupo_id = db.execute(
        "INSERT INTO grupos (codigo, institucion_id) VALUES ('MIG-02', 1)"
    ).lastrowid
    est_id = db.execute(
        "INSERT INTO estudiantes (tipo_documento, numero_documento, nombre, apellido, "
        "grupo_id, fecha_ingreso, institucion_id) VALUES ('TI', '99922222', 'E', 'M2', ?, CURRENT_DATE, 1)",
        (grupo_id,),
    ).lastrowid
    periodo_id = db.execute(
        "INSERT INTO periodos (anio_id, nombre, numero, peso_porcentual) VALUES (?, 'PM2', 1, 25.0)",
        (anio_id,),
    ).lastrowid
    reg_id = db.execute(
        "INSERT INTO registro_comportamiento "
        "(estudiante_id, grupo_id, periodo_id, tipo, descripcion, seguimiento) "
        "VALUES (?, ?, ?, 'compromiso', 'Desc', 'Ya existe')",
        (est_id, grupo_id, periodo_id),
    ).lastrowid
    db.commit()

    _migrate_entradas_seguimiento(db)
    _migrate_entradas_seguimiento(db)
    db.commit()

    entradas = db.execute(
        "SELECT * FROM entradas_seguimiento WHERE registro_id = ?", (reg_id,)
    ).fetchall()
    assert len(entradas) == 1
