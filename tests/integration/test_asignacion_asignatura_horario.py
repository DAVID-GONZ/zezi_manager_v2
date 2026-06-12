"""
Tests de integración: encadenamiento asignatura → asignación → horario.
"""
import pytest
from src.infrastructure.db.repositories.sqlite_infraestructura_repo import SqliteInfraestructuraRepository
from src.infrastructure.db.repositories.sqlite_asignacion_repo import SqliteAsignacionRepository
from src.domain.models.asignacion import FiltroAsignacionesDTO
from src.domain.models.infraestructura import NuevoHorarioDTO


def test_sin_asignaciones_huerfanas(db_conn, seed_result):
    """Toda asignación referencia asignatura y grupo existentes (sin huérfanos)."""
    repo = SqliteAsignacionRepository(db_conn)
    asigs = repo.listar_info(FiltroAsignacionesDTO())
    assert len(asigs) > 0
    # Si listar_info resolvió nombres, no hay huérfanos — solo verificar campos no vacíos
    for a in asigs:
        assert a.asignatura_nombre, f"asignacion_id={a.asignacion_id} sin asignatura_nombre"
        assert a.grupo_codigo, f"asignacion_id={a.asignacion_id} sin grupo_codigo"


def test_crear_bloque_coherente(db_conn, seed_result):
    """Bloque creado hereda grupo_id/asignatura_id/usuario_id de su asignación."""
    infra = SqliteInfraestructuraRepository(db_conn)
    asig_repo = SqliteAsignacionRepository(db_conn)

    anio_id = seed_result.anio_id
    escenario = infra.get_escenario_activo(anio_id)
    assert escenario is not None, "Debe haber un escenario activo en el seed"

    # Obtener primera asignación
    asigs = asig_repo.listar_info(FiltroAsignacionesDTO())
    assert asigs, "Debe haber asignaciones en el seed"
    ai = asigs[0]

    asig_completa = asig_repo.get_by_id(ai.asignacion_id)
    assert asig_completa is not None

    dto = NuevoHorarioDTO(
        escenario_id=escenario.id,
        asignacion_id=ai.asignacion_id,
        grupo_id=asig_completa.grupo_id,
        asignatura_id=asig_completa.asignatura_id,
        usuario_id=asig_completa.usuario_id,
        dia_semana="Viernes",
        hora_inicio="14:00",
        hora_fin="15:00",
        sala="Sala Test",
    )
    bloque = infra.guardar_horario(dto.to_horario())

    assert bloque.grupo_id == asig_completa.grupo_id
    assert bloque.asignatura_id == asig_completa.asignatura_id
    assert bloque.usuario_id == asig_completa.usuario_id
    assert bloque.escenario_id == escenario.id


def test_listar_horario_escenario_nombres_resueltos(db_conn, seed_result):
    """listar_horario_escenario incluye nombres de asignatura y docente."""
    infra = SqliteInfraestructuraRepository(db_conn)
    asig_repo = SqliteAsignacionRepository(db_conn)

    anio_id = seed_result.anio_id
    escenario = infra.get_escenario_activo(anio_id)
    assert escenario is not None

    # Crear un bloque para que haya algo en listar
    asigs = asig_repo.listar_info(FiltroAsignacionesDTO())
    if not asigs:
        pytest.skip("No hay asignaciones en el seed")

    ai = asigs[0]
    asig_completa = asig_repo.get_by_id(ai.asignacion_id)
    dto = NuevoHorarioDTO(
        escenario_id=escenario.id,
        asignacion_id=ai.asignacion_id,
        grupo_id=asig_completa.grupo_id,
        asignatura_id=asig_completa.asignatura_id,
        usuario_id=asig_completa.usuario_id,
        dia_semana="Jueves",
        hora_inicio="16:00",
        hora_fin="17:00",
        sala="Aula",
    )
    infra.guardar_horario(dto.to_horario())

    bloques = infra.listar_horario_escenario(escenario.id)
    assert len(bloques) > 0
    for b in bloques:
        assert b.asignatura_nombre, "asignatura_nombre vacío"
        assert b.docente_nombre, "docente_nombre vacío"
