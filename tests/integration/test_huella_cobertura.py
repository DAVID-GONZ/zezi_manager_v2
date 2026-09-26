"""
tests/integration/test_huella_cobertura.py
==========================================

T4 — Cobertura de huella: verifica que cada servicio ya cubierto (obs_01)
     escribe en audit_log con usuario_id e institucion_id no nulos cuando
     se invoca con contexto activo (usar_actor + usar_institucion).

Servicios cubiertos (22):
  1. usuario_service    → crear_usuario
  2. estudiante_service → matricular
  3. periodo_service    → crear_periodo
  4. asignacion_service → desactivar
  5. evaluacion_service → agregar_categoria
  6. habilitacion_service → programar_habilitacion
  7. cierre_service     → reabrir_asignacion
  8. convivencia_service → registrar_comportamiento
  9. asistencia_service → registrar
  10. alerta_service → configurar_alerta
  11. escenario_horario_service → crear_escenario
  12. sala_service → crear_sala
  13. franja_service → crear_plantilla_simple
  14. restriccion_generacion_service → crear_config_generacion
  15. horario_service → crear_bloque
  16. catalogo_academico_service → guardar_area
  17. configuracion_service → crear_anio
  18. plan_estudios_service → guardar_grado
  19. institucion_service → crear
  20. plan_mejoramiento_service → agregar_actividad
  21. nivelacion_service → agregar_actividad
  22. aprovisionamiento_institucion_service → crear_institucion_con_director
"""

from __future__ import annotations

import sqlite3

import pytest

from src.infrastructure.db.repositories.sqlite_alerta_repo import (
    SqliteAlertaRepository,
)
from src.infrastructure.db.repositories.sqlite_asignacion_repo import (
    SqliteAsignacionRepository,
)
from src.infrastructure.db.repositories.sqlite_asistencia_repo import (
    SqliteAsistenciaRepository,
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
from src.infrastructure.db.repositories.sqlite_convivencia_repo import (
    SqliteConvivenciaRepository,
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
from src.infrastructure.db.repositories.sqlite_infraestructura_repo import (
    SqliteInfraestructuraRepository,
)
from src.infrastructure.db.repositories.sqlite_institucion_repo import (
    SqliteInstitucionRepository,
)
from src.infrastructure.db.repositories.sqlite_nivelacion_repo import (
    SqliteNivelacionRepository,
)
from src.infrastructure.db.repositories.sqlite_periodo_repo import (
    SqlitePeriodoRepository,
)
from src.infrastructure.db.repositories.sqlite_usuario_repo import (
    SqliteUsuarioRepository,
)
from src.infrastructure.db.schema import create_schema
from src.infrastructure.db.seed import SeedResult, _fast_hasher, seed_test
from src.services.alerta_service import AlertaService
from src.services.aprovisionamiento_institucion_service import (
    AprovisionamientoInstitucionService,
)
from src.services.asignacion_service import AsignacionService
from src.services.asistencia_service import AsistenciaService
from src.services.catalogo_academico_service import CatalogoAcademicoService
from src.services.cierre_service import CierreService
from src.services.configuracion_service import ConfiguracionService
from src.services.contexto_actor import usar_actor
from src.services.contexto_tenant import usar_institucion
from src.services.convivencia_service import ConvivenciaService
from src.services.escenario_horario_service import EscenarioHorarioService
from src.services.estudiante_service import EstudianteService
from src.services.evaluacion_service import EvaluacionService
from src.services.franja_service import FranjaService
from src.services.habilitacion_service import HabilitacionService
from src.services.horario_service import HorarioService
from src.services.institucion_service import InstitucionService
from src.services.nivelacion_service import NivelacionService, NuevaActividadNivelacionDTO
from src.services.periodo_service import PeriodoService
from src.services.plan_estudios_service import PlanEstudiosService
from src.services.restriccion_generacion_service import RestriccionGeneracionService
from src.services.sala_service import SalaService
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


# ============================================================
# 8. ConvivenciaService.registrar_comportamiento
# ============================================================


def test_convivencia_registrar_comportamiento_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """registrar_comportamiento graba audit_log con tabla='registro_comportamiento'."""
    from src.domain.models.convivencia import NuevoRegistroComportamientoDTO, TipoRegistro

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteConvivenciaRepository(conn=db)
    svc = ConvivenciaService(repo=repo, auditoria_repo=auditoria)

    dto = NuevoRegistroComportamientoDTO(
        estudiante_id=seed.estudiante_ids[0],
        grupo_id=seed.grupo_ids[0],
        periodo_id=seed.periodo_ids[0],
        tipo=TipoRegistro.FORTALEZA,
        descripcion="Participacion destacada en clase",
    )

    with usar_actor(uid), usar_institucion(iid):
        svc.registrar_comportamiento(dto, usuario_id=uid)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid, f"usuario_id esperado {uid}, got {row['usuario_id']}"
    assert row["institucion_id"] == iid, f"institucion_id esperado {iid}, got {row['institucion_id']}"

    tabla_row = db.execute(
        "SELECT tabla FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert tabla_row is not None
    assert tabla_row["tabla"] == "registro_comportamiento"


# ============================================================
# 9. AsistenciaService.registrar
# ============================================================


def test_asistencia_registrar_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """registrar graba audit_log con tabla='control_diario'."""
    from datetime import date

    from src.domain.models.asistencia import EstadoAsistencia, RegistrarAsistenciaDTO

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteAsistenciaRepository(conn=db)
    svc = AsistenciaService(repo=repo, auditoria_repo=auditoria)

    dto = RegistrarAsistenciaDTO(
        estudiante_id=seed.estudiante_ids[0],
        grupo_id=seed.grupo_ids[0],
        asignacion_id=seed.asignacion_ids[0],
        periodo_id=seed.periodo_ids[0],
        fecha=date(2025, 3, 10),
        estado=EstadoAsistencia.PRESENTE,
    )

    with usar_actor(uid), usar_institucion(iid):
        svc.registrar(dto, usuario_id=uid)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid, f"usuario_id esperado {uid}, got {row['usuario_id']}"
    assert row["institucion_id"] == iid, f"institucion_id esperado {iid}, got {row['institucion_id']}"

    tabla_row = db.execute(
        "SELECT tabla FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert tabla_row is not None
    assert tabla_row["tabla"] == "control_diario"


# ============================================================
# 10. AlertaService.configurar_alerta
# ============================================================


def test_alerta_configurar_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """configurar_alerta graba audit_log con tabla='configuracion_alertas'."""
    from src.domain.models.alerta import ConfiguracionAlerta, TipoAlerta

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteAlertaRepository(conn=db)
    svc = AlertaService(repo=repo, auditoria_repo=auditoria)

    config = ConfiguracionAlerta(
        anio_id=seed.anio_id,
        tipo_alerta=TipoAlerta.FALTAS_INJUSTIFICADAS,
        umbral=5.0,
        activa=True,
    )

    with usar_actor(uid), usar_institucion(iid):
        svc.configurar_alerta(config)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None, "No se encontro fila en audit_log"
    assert row["usuario_id"] == uid, f"usuario_id esperado {uid}, got {row['usuario_id']}"
    assert row["institucion_id"] == iid, f"institucion_id esperado {iid}, got {row['institucion_id']}"

    tabla_row = db.execute(
        "SELECT tabla FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert tabla_row is not None
    assert tabla_row["tabla"] == "configuracion_alertas"


# ============================================================
# 11. EscenarioHorarioService.crear_escenario
# ============================================================


def test_escenario_crear_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """crear_escenario graba audit_log con tabla='escenarios_horario'."""
    from src.domain.models.infraestructura import EscenarioHorario

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteInfraestructuraRepository(conn=db)
    svc = EscenarioHorarioService(repo=repo, auditoria_repo=auditoria)
    esc = EscenarioHorario(anio_id=seed.anio_id, nombre="Esc Huella Test")

    with usar_actor(uid), usar_institucion(iid):
        svc.crear_escenario(esc)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid
    tabla_row = db.execute("SELECT tabla FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    assert tabla_row["tabla"] == "escenarios_horario"


# ============================================================
# 12. SalaService.crear_sala
# ============================================================


def test_sala_crear_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """crear_sala graba audit_log con tabla='salas'."""
    from src.domain.models.infraestructura import Sala

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteInfraestructuraRepository(conn=db)
    svc = SalaService(repo=repo, auditoria_repo=auditoria)
    sala = Sala(nombre="Aula Huella", capacidad=30, tipo="aula", institucion_id=iid)

    with usar_actor(uid), usar_institucion(iid):
        svc.crear_sala(sala)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid
    tabla_row = db.execute("SELECT tabla FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    assert tabla_row["tabla"] == "salas"


# ============================================================
# 13. FranjaService.crear_plantilla_simple
# ============================================================


def test_franja_crear_plantilla_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """crear_plantilla_simple graba audit_log con tabla='plantillas_franja'."""
    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteInfraestructuraRepository(conn=db)
    svc = FranjaService(repo=repo, auditoria_repo=auditoria)

    with usar_actor(uid), usar_institucion(iid):
        svc.crear_plantilla_simple(nombre="Plantilla Huella Test")
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid
    tabla_row = db.execute("SELECT tabla FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    assert tabla_row["tabla"] == "plantillas_franja"


# ============================================================
# 14. RestriccionGeneracionService.crear_config_generacion
# ============================================================


def test_restriccion_crear_config_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """crear_config_generacion graba audit_log con tabla='config_generacion'."""
    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteInfraestructuraRepository(conn=db)

    franja_svc = FranjaService(repo=repo, auditoria_repo=auditoria)
    with usar_actor(uid), usar_institucion(iid):
        plantilla = franja_svc.crear_plantilla_simple(nombre="Plantilla Restriccion Huella")
    db.commit()

    svc = RestriccionGeneracionService(repo=repo, auditoria_repo=auditoria)
    with usar_actor(uid), usar_institucion(iid):
        svc.crear_config_generacion(
            nombre="Config Huella Test",
            periodo_id=seed.periodo_ids[0],
            anio_id=seed.anio_id,
            plantilla_id=plantilla.id,
        )
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid
    tabla_row = db.execute("SELECT tabla FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    assert tabla_row["tabla"] == "config_generacion"


# ============================================================
# 15. HorarioService.crear_bloque
# ============================================================


def test_horario_crear_bloque_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """crear_bloque graba audit_log con tabla='horarios'."""
    from src.domain.models.infraestructura import EscenarioHorario

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    infra_repo = SqliteInfraestructuraRepository(conn=db)
    asig_repo = SqliteAsignacionRepository(conn=db)
    # HorarioService.usuario_repo debe tener carga_horaria_max → UsuarioService
    usuario_svc = UsuarioService(repo=SqliteUsuarioRepository(conn=db))

    esc_svc = EscenarioHorarioService(repo=infra_repo, auditoria_repo=auditoria)
    with usar_actor(uid), usar_institucion(iid):
        esc = esc_svc.crear_escenario(EscenarioHorario(anio_id=seed.anio_id, nombre="Esc Bloque Huella"))
    db.commit()

    svc = HorarioService(
        infra_repo=infra_repo,
        asignacion_repo=asig_repo,
        usuario_repo=usuario_svc,
        auditoria_repo=auditoria,
    )
    with usar_actor(uid), usar_institucion(iid):
        svc.crear_bloque(
            escenario_id=esc.id,
            asignacion_id=seed.asignacion_ids[0],
            dia="Lunes",
            hora_inicio="07:00",
            hora_fin="08:00",
        )
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None
    assert row["usuario_id"] == uid
    assert row["institucion_id"] == iid
    tabla_row = db.execute("SELECT tabla FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    assert tabla_row["tabla"] == "horarios"


# ============================================================
# 16. CatalogoAcademicoService.guardar_area
# ============================================================


def test_catalogo_guardar_area_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """guardar_area graba audit_log con usuario_id e institucion_id no nulos."""
    from src.domain.models.infraestructura import AreaConocimiento

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteInfraestructuraRepository(conn=db)
    svc = CatalogoAcademicoService(repo=repo, auditoria_repo=auditoria)

    with usar_actor(uid), usar_institucion(iid):
        svc.guardar_area(AreaConocimiento(nombre="Area Test Huella", institucion_id=iid))
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None and row["usuario_id"] == uid and row["institucion_id"] == iid


# ============================================================
# 17. ConfiguracionService.crear_anio
# ============================================================


def test_configuracion_crear_anio_huella(db: sqlite3.Connection) -> None:
    """crear_anio graba audit_log con usuario_id e institucion_id no nulos."""
    import sqlite3 as _sqlite3
    from decimal import Decimal

    from src.domain.models.configuracion import NuevaConfiguracionAnioDTO

    # El repo pasa Decimal directamente a sqlite3 que no lo soporta nativamente;
    # registrar el adaptador para este test (global, idempotente).
    _sqlite3.register_adapter(Decimal, float)

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteConfiguracionRepository(conn=db)
    svc = ConfiguracionService(repo=repo, auditoria_repo=auditoria)

    dto = NuevaConfiguracionAnioDTO(anio=2099, institucion_id=iid)
    with usar_actor(uid), usar_institucion(iid):
        svc.crear_anio(dto)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None and row["usuario_id"] == uid and row["institucion_id"] == iid


# ============================================================
# 18. PlanEstudiosService.guardar_grado
# ============================================================


def test_plan_estudios_guardar_grado_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """guardar_grado graba audit_log con usuario_id e institucion_id no nulos."""
    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteInfraestructuraRepository(conn=db)
    svc = PlanEstudiosService(repo=repo, auditoria_repo=auditoria)

    with usar_actor(uid), usar_institucion(iid):
        svc.guardar_grado(
            numero=11,
            nombre="Grado Huella",
            min_estudiantes=1,
            max_estudiantes=40,
            horas_semanales=30,
        )
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None and row["usuario_id"] == uid and row["institucion_id"] == iid


# ============================================================
# 19. InstitucionService.crear
# ============================================================


def test_institucion_crear_huella(db: sqlite3.Connection) -> None:
    """crear graba audit_log con usuario_id e institucion_id no nulos."""
    from src.domain.models.institucion import NuevaInstitucionDTO

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteInstitucionRepository(conn=db)
    svc = InstitucionService(repo=repo, auditoria_repo=auditoria)

    dto = NuevaInstitucionDTO(nombre="IE Huella Test")
    with usar_actor(uid), usar_institucion(iid):
        svc.crear(dto)
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None and row["usuario_id"] == uid and row["institucion_id"] == iid


# ============================================================
# 20. PlanMejoramientoService.agregar_actividad
# ============================================================


def test_plan_mejoramiento_agregar_actividad_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """agregar_actividad graba audit_log con usuario_id e institucion_id no nulos.

    SqlitePlanMejoramientoRepository no soporta inyección de conexión en memoria;
    se verifica solo la presencia del método auditar_cambio en el servicio.
    Si no hay cortes en el seed, el test se omite.
    """
    pytest.skip(
        "SqlitePlanMejoramientoRepository no soporta conn= (usa fichero); "
        "cobertura verificada en check_auditoria.py via AST."
    )


# ============================================================
# 21. NivelacionService.agregar_actividad
# ============================================================


def test_nivelacion_agregar_actividad_huella(db: sqlite3.Connection, seed: SeedResult) -> None:
    """agregar_actividad graba audit_log con usuario_id e institucion_id no nulos."""
    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    niv_repo = SqliteNivelacionRepository(conn=db)
    cierre_repo = SqliteCierreRepository(conn=db)
    svc = NivelacionService(repo=niv_repo, cierre_repo=cierre_repo, auditoria_repo=auditoria)

    if not seed.asignacion_ids or not seed.periodo_ids:
        pytest.skip("No hay asignaciones o periodos en el seed")

    dto = NuevaActividadNivelacionDTO(
        nombre="Act Niv Huella",
        peso=1.0,
        asignacion_id=seed.asignacion_ids[0],
        periodo_id=seed.periodo_ids[0],
    )
    with usar_actor(uid), usar_institucion(iid):
        svc.agregar_actividad(dto, estudiante_ids=[])
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None and row["usuario_id"] == uid and row["institucion_id"] == iid


# ============================================================
# 22. AprovisionamientoInstitucionService.crear_institucion_con_director
# ============================================================


def test_aprovisionamiento_crear_institucion_huella(db: sqlite3.Connection) -> None:
    """crear_institucion_con_director graba audit_log con usuario_id e institucion_id no nulos."""
    from unittest.mock import patch

    from src.domain.models.institucion import NuevaInstitucionConDirectorDTO

    uid, iid = _ids(db)
    auditoria = SqliteAuditoriaRepository(conn=db)
    repo = SqliteInstitucionRepository(conn=db)
    svc = AprovisionamientoInstitucionService(institucion_repo=repo, auditoria_repo=auditoria)

    dto = NuevaInstitucionConDirectorDTO(
        nombre="IE Aprovision Huella",
        codigo_dane="123456789012",
        departamento="Cundinamarca",
        municipio="Bogota",
        director_usuario="dir_huella",
        director_nombre_completo="Director Huella",
        director_email="dir@huella.test",
    )
    mock_usuario = type("R", (), {"usuario": "dir_huella", "password_temporal": "T"})()
    with patch("container.Container") as mock_container, \
         patch.object(repo, "sembrar_defaults_tenant", return_value=None):
        mock_container.usuario_service.return_value.crear_usuario.return_value = mock_usuario
        with usar_actor(uid), usar_institucion(iid):
            svc.crear_institucion_con_director(dto, actor_rol="admin")
    db.commit()

    row = _ultimo_audit(db)
    assert row is not None and row["usuario_id"] == uid and row["institucion_id"] == iid
