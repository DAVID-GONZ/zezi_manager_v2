"""
tests/integration/test_huella_cobertura.py
==========================================

T4 — Cobertura de huella: verifica que cada servicio ya cubierto (obs_01)
     escribe en audit_log con usuario_id e institucion_id no nulos cuando
     se invoca con contexto activo (usar_actor + usar_institucion).

Servicios cubiertos (7):
  1. usuario_service    → crear_usuario
  2. estudiante_service → matricular
  3. periodo_service    → crear_periodo
  4. asignacion_service → desactivar
  5. evaluacion_service → agregar_categoria
  6. habilitacion_service → programar_habilitacion
  7. cierre_service     → reabrir_asignacion
"""

from __future__ import annotations

import sqlite3

import pytest

from src.infrastructure.db.repositories.sqlite_asignacion_repo import (
    SqliteAsignacionRepository,
)
from src.infrastructure.db.repositories.sqlite_auditoria_repo import (
    SqliteAuditoriaRepository,
)
from src.infrastructure.db.repositories.sqlite_cierre_repo import (
    SqliteCierreRepository,
)
from src.infrastructure.db.repositories.sqlite_configuracion_repo import (
    SqliteConfiguracionRepository,
)
from src.infrastructure.db.repositories.sqlite_estudiante_repo import (
    SqliteEstudianteRepository,
)
from src.infrastructure.db.repositories.sqlite_evaluacion_repo import (
    SqliteEvaluacionRepository,
)
from src.infrastructure.db.repositories.sqlite_habilitacion_repo import (
    SqliteHabilitacionRepository,
)
from src.infrastructure.db.repositories.sqlite_periodo_repo import (
    SqlitePeriodoRepository,
)
from src.infrastructure.db.repositories.sqlite_usuario_repo import (
    SqliteUsuarioRepository,
)
from src.infrastructure.db.schema import create_schema
from src.infrastructure.db.seed import SeedResult, _fast_hasher, seed_test
from src.services.asignacion_service import AsignacionService
from src.services.cierre_service import CierreService
from src.services.contexto_actor import usar_actor
from src.services.contexto_tenant import usar_institucion
from src.services.estudiante_service import EstudianteService
from src.services.evaluacion_service import EvaluacionService
from src.services.habilitacion_service import HabilitacionService
from src.services.periodo_service import PeriodoService
from src.services.usuario_service import UsuarioService

pytestmark = pytest.mark.integration

# ============================================================
# Fixture compartida
# ============================================================


@pytest.fixture()
def db() -> sqlite3.Connection:
    """Conexion en memoria con seed_test. No hace commit — cada test es atomico."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    seed_test(conn, anio=2025, hasher=_fast_hasher)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def seed(db: sqlite3.Connection) -> SeedResult:
    """Ejecuta seed_test y devuelve el SeedResult para acceder a IDs."""
    # seed_test ya fue llamado en el fixture db; reconstruimos el resultado
    # leyendo los IDs de la base para no duplicar el seed.
    result = SeedResult()
    result.anio_id = db.execute("SELECT id FROM configuracion_anio ORDER BY id LIMIT 1").fetchone()["id"]
    result.usuario_ids = {
        row["usuario"]: row["id"]
        for row in db.execute("SELECT id, usuario FROM usuarios").fetchall()
    }
    result.asignacion_ids = [
        row["id"]
        for row in db.execute("SELECT id FROM asignaciones ORDER BY id").fetchall()
    ]
    result.periodo_ids = [
        row["id"]
        for row in db.execute("SELECT id FROM periodos ORDER BY id").fetchall()
    ]
    result.estudiante_ids = [
        row["id"]
        for row in db.execute("SELECT id FROM estudiantes ORDER BY id").fetchall()
    ]
    result.grupo_ids = [
        row["id"]
        for row in db.execute("SELECT id FROM grupos ORDER BY id").fetchall()
    ]
    return result


def _ultimo_audit(db: sqlite3.Connection) -> sqlite3.Row | None:
    """Retorna la fila mas reciente del audit_log."""
    return db.execute(
        "SELECT usuario_id, institucion_id FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()


# ============================================================
# Helpers de contexto
# ============================================================

def _ids(db: sqlite3.Connection):
    """Retorna (usuario_id, institucion_id) de los primeros registros del seed."""
    uid = db.execute("SELECT id FROM usuarios ORDER BY id LIMIT 1").fetchone()["id"]
    iid = db.execute("SELECT id FROM instituciones ORDER BY id LIMIT 1").fetchone()["id"]
    return uid, iid


# ============================================================
# 1. UsuarioService.crear_usuario
# ============================================================


def test_usuario_crear_huella(db: sqlite3.Connection) -> None:
    """crear_usuario graba audit_log con usuario_id e institucion_id no nulos."""
    from src.domain.models.usuario import NuevoUsuarioDTO

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteUsuarioRepository(conn=db)
    svc = UsuarioService(repo=repo, auditoria=auditoria)

    dto = NuevoUsuarioDTO(
        usuario="nuevo_test_usr",
        nombre_completo="Nuevo Usuario Test",
        password="SeguroTest2025*",
    )

    with usar_actor(uid), usar_institucion(iid):
        svc.crear_usuario(dto)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid, f"usuario_id esperado {uid}, got {row['usuario_id']}"
    assert row["institucion_id"] == iid, f"institucion_id esperado {iid}, got {row['institucion_id']}"


# ============================================================
# 2. EstudianteService.matricular
# ============================================================


def test_estudiante_matricular_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """matricular graba audit_log con usuario_id e institucion_id no nulos."""
    from src.domain.models.estudiante import NuevoEstudianteDTO

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteEstudianteRepository(conn=db)
    svc = EstudianteService(repo=repo, auditoria=auditoria)

    dto = NuevoEstudianteDTO(
        numero_documento="HUE999001",
        nombre="Pedro",
        apellido="Huella",
        grupo_id=seed.grupo_ids[0] if seed.grupo_ids else None,
    )

    with usar_actor(uid), usar_institucion(iid):
        svc.matricular(dto)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid


# ============================================================
# 3. PeriodoService.crear_periodo
# ============================================================


def test_periodo_cerrar_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """cerrar_periodo graba audit_log con usuario_id e institucion_id no nulos.

    seed_test crea 4 periodos con peso total 100%, por lo que no se puede
    crear un quinto. Se usa cerrar_periodo (tambien cubierto) en el periodo 2,
    que esta abierto pero no activo.
    """
    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqlitePeriodoRepository(conn=db)
    svc = PeriodoService(repo=repo, auditoria=auditoria)

    # periodo_ids[1] es el segundo periodo — abierto y no activo
    periodo_id = seed.periodo_ids[1]

    with usar_actor(uid), usar_institucion(iid):
        svc.cerrar_periodo(periodo_id)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid


# ============================================================
# 4. AsignacionService.desactivar
# ============================================================


def test_asignacion_desactivar_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """desactivar graba audit_log con usuario_id e institucion_id no nulos."""
    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteAsignacionRepository(conn=db)
    svc = AsignacionService(repo=repo, auditoria=auditoria)

    asignacion_id = seed.asignacion_ids[0]

    with usar_actor(uid), usar_institucion(iid):
        svc.desactivar(asignacion_id)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid


# ============================================================
# 5. EvaluacionService.agregar_categoria
# ============================================================


def test_evaluacion_agregar_categoria_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """agregar_categoria graba audit_log con usuario_id e institucion_id no nulos.

    Usa el segundo periodo (periodo_ids[1]) donde no hay categorias existentes
    para que el peso disponible sea 1.0.
    """
    from src.domain.models.dtos import ContextoAcademicoDTO
    from src.domain.models.evaluacion import NuevaCategoriaDTO

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteEvaluacionRepository(conn=db)
    # sin periodo_repo => _verificar_periodo_abierto no bloquea
    svc = EvaluacionService(repo=repo, auditoria=auditoria)

    asignacion_id = seed.asignacion_ids[0]
    # Usar el segundo periodo: seed_test no crea categorias para periodos > 0
    periodo_id = seed.periodo_ids[1] if len(seed.periodo_ids) > 1 else seed.periodo_ids[0]

    dto = NuevaCategoriaDTO(
        nombre="Participacion Huella",
        peso="0.50",
        asignacion_id=asignacion_id,
        periodo_id=periodo_id,
    )
    ctx = ContextoAcademicoDTO(
        usuario_id=uid,
        anio_id=seed.anio_id,
        periodo_id=periodo_id,
        asignacion_id=asignacion_id,
    )

    with usar_actor(uid), usar_institucion(iid):
        svc.agregar_categoria(dto, ctx)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid


# ============================================================
# 6. HabilitacionService.programar_habilitacion
# ============================================================


def test_habilitacion_programar_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """programar_habilitacion graba audit_log con usuario_id e institucion_id no nulos."""
    from src.domain.models.habilitacion import NuevaHabilitacionDTO, TipoHabilitacion

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteHabilitacionRepository(conn=db)
    svc = HabilitacionService(repo=repo, auditoria=auditoria)

    dto = NuevaHabilitacionDTO(
        estudiante_id=seed.estudiante_ids[0],
        asignacion_id=seed.asignacion_ids[0],
        tipo=TipoHabilitacion.PERIODO,
        periodo_id=seed.periodo_ids[0],
    )

    with usar_actor(uid), usar_institucion(iid):
        svc.programar_habilitacion(dto)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid


# ============================================================
# 7. CierreService.reabrir_asignacion
# ============================================================


def test_cierre_reabrir_asignacion_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """reabrir_asignacion graba audit_log con usuario_id e institucion_id no nulos.

    CierreService.reabrir_asignacion llama a auditar_cambio incondicionalmente
    (incluso cuando borra 0 registros), por lo que no necesita cierres previos.
    """
    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    cierre_repo = SqliteCierreRepository(conn=db)
    eval_repo = SqliteEvaluacionRepository(conn=db)
    periodo_repo = SqlitePeriodoRepository(conn=db)
    config_repo = SqliteConfiguracionRepository(conn=db)
    est_repo = SqliteEstudianteRepository(conn=db)
    svc = CierreService(
        cierre_repo=cierre_repo,
        evaluacion_repo=eval_repo,
        periodo_repo=periodo_repo,
        config_repo=config_repo,
        estudiante_repo=est_repo,
        auditoria=auditoria,
    )

    with usar_actor(uid), usar_institucion(iid):
        svc.reabrir_asignacion(
            asignacion_id=seed.asignacion_ids[0],
            periodo_id=seed.periodo_ids[0],
        )
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid
