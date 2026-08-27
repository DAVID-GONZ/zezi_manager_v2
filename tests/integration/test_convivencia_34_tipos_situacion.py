"""
Tests de integración — Tipos de situación (convivencia_34).

Cubre: seed de 3 tipos por institución, CRUD del repo, validación de
tipo_situacion_obligatorio en el servicio y RBAC de escritura.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.domain.models.convivencia import NuevoTipoSituacionDTO, TipoSituacion
from src.infrastructure.db.repositories.sqlite_convivencia_repo import (
    SqliteConvivenciaRepository,
)
from src.infrastructure.db.schema import create_schema
from src.infrastructure.db.seed import _fast_hasher, seed_base
from src.services.convivencia_service import ConvivenciaService

# ---------------------------------------------------------------------------
# Fixture
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


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


def test_seed_inserta_tres_tipos_por_institucion(db):
    """seed_base debe insertar exactamente 3 tipos de situación para la institución 1."""
    filas = db.execute(
        "SELECT * FROM tipos_situacion WHERE institucion_id = 1"
    ).fetchall()
    assert len(filas) == 3
    niveles = {f["nivel"] for f in filas}
    assert niveles == {1, 2, 3}


def test_seed_es_idempotente(db):
    """Llamar seed_base dos veces no duplica tipos."""
    seed_base(db, anio=2025, hasher=_fast_hasher)
    db.commit()
    filas = db.execute(
        "SELECT * FROM tipos_situacion WHERE institucion_id = 1"
    ).fetchall()
    assert len(filas) == 3


# ---------------------------------------------------------------------------
# Repo: listar
# ---------------------------------------------------------------------------


def test_listar_tipos_activos_incluye_seed(repo):
    tipos = repo.listar_tipos_situacion(solo_activas=True, institucion_id=1)
    assert len(tipos) == 3
    nombres = {t.nombre for t in tipos}
    assert any("I" in n for n in nombres)


def test_listar_todos_incluye_inactivos(db, repo):
    db.execute("UPDATE tipos_situacion SET activa = 0 WHERE nivel = 1")
    db.commit()
    activos = repo.listar_tipos_situacion(solo_activas=True, institucion_id=1)
    todos = repo.listar_tipos_situacion(solo_activas=False, institucion_id=1)
    assert len(activos) == 2
    assert len(todos) == 3


# ---------------------------------------------------------------------------
# Repo: CRUD
# ---------------------------------------------------------------------------


def test_guardar_y_recuperar_tipo(repo, db):
    nuevo = TipoSituacion(nombre="Tipo Personalizado", nivel=2, institucion_id=1)
    guardado = repo.guardar_tipo_situacion(nuevo)
    db.commit()

    assert guardado.id is not None
    leido = repo.get_tipo_situacion(guardado.id)
    assert leido is not None
    assert leido.nombre == "Tipo Personalizado"
    assert leido.nivel == 2
    assert leido.activa is True


def test_actualizar_tipo(repo, db):
    tipos = repo.listar_tipos_situacion(solo_activas=True, institucion_id=1)
    tipo = tipos[0]
    modificado = tipo.model_copy(update={"nombre": "Nombre Nuevo", "protocolo": "Protocolo X"})
    repo.actualizar_tipo_situacion(modificado)
    db.commit()

    leido = repo.get_tipo_situacion(tipo.id)
    assert leido.nombre == "Nombre Nuevo"
    assert leido.protocolo == "Protocolo X"


def test_get_tipo_inexistente_retorna_none(repo):
    assert repo.get_tipo_situacion(99999) is None


# ---------------------------------------------------------------------------
# Service: CRUD + RBAC
# ---------------------------------------------------------------------------


def test_crear_tipo_como_director(svc, db):
    dto = NuevoTipoSituacionDTO(nombre="Tipo Nuevo Dir", nivel=1, descripcion="desc")
    tipo = svc.crear_tipo_situacion(dto, usuario_rol="director")
    db.commit()
    assert tipo.id is not None
    assert tipo.nombre == "Tipo Nuevo Dir"


def test_crear_tipo_como_coordinador(svc, db):
    dto = NuevoTipoSituacionDTO(nombre="Tipo Coordinador", nivel=2)
    tipo = svc.crear_tipo_situacion(dto, usuario_rol="coordinador")
    db.commit()
    assert tipo.id is not None


def test_crear_tipo_rol_no_autorizado_falla(svc):
    dto = NuevoTipoSituacionDTO(nombre="Prohibido", nivel=1)
    with pytest.raises(PermissionError):
        svc.crear_tipo_situacion(dto, usuario_rol="profesor")


def test_desactivar_tipo(svc, db):
    tipos = svc.listar_tipos_situacion(solo_activas=True)
    tipo_id = tipos[0].id
    svc.desactivar_tipo_situacion(tipo_id, usuario_rol="director")
    db.commit()

    activos = {t.id for t in svc.listar_tipos_situacion(solo_activas=True)}
    assert tipo_id not in activos


def test_desactivar_tipo_rol_no_autorizado_falla(svc):
    tipos = svc.listar_tipos_situacion(solo_activas=True)
    with pytest.raises(PermissionError):
        svc.desactivar_tipo_situacion(tipos[0].id, usuario_rol="profesor")


# ---------------------------------------------------------------------------
# Service: tipo_situacion_obligatorio en registrar_comportamiento
# ---------------------------------------------------------------------------


def _setup_registro_datos(db):
    """Inserta los registros mínimos para llamar registrar_comportamiento."""
    anio_id = db.execute("SELECT id FROM configuracion_anio LIMIT 1").fetchone()["id"]
    grupo_id = db.execute(
        "INSERT INTO grupos (codigo, institucion_id) VALUES ('GTS-01', 1)"
    ).lastrowid
    est_id = db.execute(
        "INSERT INTO estudiantes (tipo_documento, numero_documento, nombre, apellido, "
        "grupo_id, fecha_ingreso, institucion_id) VALUES ('TI', '77700001', 'Est', 'TS', ?, CURRENT_DATE, 1)",
        (grupo_id,),
    ).lastrowid
    periodo_id = db.execute(
        "INSERT INTO periodos (anio_id, nombre, numero, peso_porcentual) VALUES (?, 'P1', 1, 25.0)",
        (anio_id,),
    ).lastrowid
    db.commit()
    return est_id, grupo_id, periodo_id


def test_registrar_comportamiento_sin_tipo_cuando_no_obligatorio(svc, db):
    from src.domain.models.convivencia import NuevoRegistroComportamientoDTO

    est_id, grupo_id, periodo_id = _setup_registro_datos(db)
    dto = NuevoRegistroComportamientoDTO(
        estudiante_id=est_id,
        grupo_id=grupo_id,
        periodo_id=periodo_id,
        tipo="dificultad",
        descripcion="Comportamiento sin tipo",
    )
    registro = svc.registrar_comportamiento(dto)
    assert registro.id is not None
    assert registro.tipo_situacion_id is None


def test_registrar_comportamiento_tipo_obligatorio_sin_id_falla(repo, db):
    from unittest.mock import MagicMock

    from src.domain.models.convivencia import NuevoRegistroComportamientoDTO
    from src.domain.models.preferencia_institucion import PreferenciasDTO
    from src.services.contexto_tenant import usar_institucion
    from src.services.convivencia_service import ConvivenciaService

    prefs_dto = PreferenciasDTO(tipo_situacion_obligatorio=True)
    prefs_svc = MagicMock()
    prefs_svc.get_dto.return_value = prefs_dto

    svc_obligatorio = ConvivenciaService(
        repo=repo, preferencias_svc_provider=lambda: prefs_svc
    )

    est_id, grupo_id, periodo_id = _setup_registro_datos(db)
    dto = NuevoRegistroComportamientoDTO(
        estudiante_id=est_id,
        grupo_id=grupo_id,
        periodo_id=periodo_id,
        tipo="dificultad",
        descripcion="Sin clasificar, pero obligatorio",
    )
    with usar_institucion(1):
        with pytest.raises(ValueError, match="clasificacion"):
            svc_obligatorio.registrar_comportamiento(dto)


def test_registrar_comportamiento_con_tipo_situacion(svc, db):
    from src.domain.models.convivencia import NuevoRegistroComportamientoDTO

    tipos = svc.listar_tipos_situacion(solo_activas=True)
    est_id, grupo_id, periodo_id = _setup_registro_datos(db)
    dto = NuevoRegistroComportamientoDTO(
        estudiante_id=est_id,
        grupo_id=grupo_id,
        periodo_id=periodo_id,
        tipo="fortaleza",
        descripcion="Con clasificación",
        tipo_situacion_id=tipos[0].id,
    )
    registro = svc.registrar_comportamiento(dto)
    assert registro.tipo_situacion_id == tipos[0].id
