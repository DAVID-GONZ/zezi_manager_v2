"""
Tests de integración para SqlaPlanMejoramientoRepository — backend_02c.

Verifica que el repositorio sigue el patrón conn=None del resto de repos:
  - Aceptar una conexión inyectada y operar sobre ella.
  - No abrir sqlite3.connect() propio.
  - Que data/app.db no se toca durante los tests.

Todos los tests usan db_conn (SQLite en memoria) del conftest.
"""
from __future__ import annotations

import pytest

from src.domain.models.plan_mejoramiento import (
    ActividadPlan,
    CortePlan,
    EstadoNotaCorte,
    NotaCortePlan,
)
from src.infrastructure.db.repositories.sqla_plan_mejoramiento_repo import (
    SqlaPlanMejoramientoRepository,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers de setup
# ---------------------------------------------------------------------------


def _hacer_corte(repo: SqlaPlanMejoramientoRepository, asignacion_id: int, periodo_id: int) -> CortePlan:
    """Crea y guarda un CortePlan mínimo."""
    return repo.guardar_corte(
        CortePlan(
            asignacion_id=asignacion_id,
            periodo_id=periodo_id,
            peso_registrado="0.30",
            nota_umbral="60.0",
            nota_minima_aprobacion="60.0",
            usuario_id=None,
        )
    )


# ---------------------------------------------------------------------------
# T2 — El repo acepta conn= inyectada (patrón normalizado)
# ---------------------------------------------------------------------------


def test_repo_acepta_conn_inyectada(db_conn):
    """SqlaPlanMejoramientoRepository(conn=db_conn) no lanza excepción."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    assert repo._conn is db_conn


def test_repo_sin_conn_no_lanza_al_instanciar():
    """SqlaPlanMejoramientoRepository() sin conn= instancia correctamente."""
    repo = SqlaPlanMejoramientoRepository()
    assert repo._conn is None


# ---------------------------------------------------------------------------
# Corte — guardar y recuperar
# ---------------------------------------------------------------------------


def test_guardar_y_obtener_corte(db_conn, seed_result):
    """guardar_corte persiste y get_corte recupera por (asignacion_id, periodo_id)."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    asig_id = seed_result.asignacion_ids[0]
    per_id = seed_result.periodo_ids[0]

    corte = _hacer_corte(repo, asig_id, per_id)

    assert corte.id is not None
    recuperado = repo.get_corte(asig_id, per_id)
    assert recuperado is not None
    assert recuperado.id == corte.id
    assert recuperado.asignacion_id == asig_id
    assert recuperado.periodo_id == per_id


def test_get_corte_by_id(db_conn, seed_result):
    """get_corte_by_id retorna el corte correcto por id."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    asig_id = seed_result.asignacion_ids[0]
    per_id = seed_result.periodo_ids[0]

    corte = _hacer_corte(repo, asig_id, per_id)
    recuperado = repo.get_corte_by_id(corte.id)

    assert recuperado is not None
    assert recuperado.id == corte.id


def test_get_corte_inexistente_retorna_none(db_conn):
    """get_corte retorna None cuando no existe el corte."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    assert repo.get_corte(9999, 9999) is None


# ---------------------------------------------------------------------------
# Nota de corte
# ---------------------------------------------------------------------------


def test_guardar_y_obtener_nota_corte(db_conn, seed_result):
    """guardar_nota_corte y get_nota_corte hacen roundtrip correcto."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    asig_id = seed_result.asignacion_ids[0]
    per_id = seed_result.periodo_ids[0]
    est_id = seed_result.estudiante_ids[0]

    corte = _hacer_corte(repo, asig_id, per_id)

    nota = repo.guardar_nota_corte(
        NotaCortePlan(
            corte_id=corte.id,
            estudiante_id=est_id,
            asignacion_id=asig_id,
            periodo_id=per_id,
            nota_al_corte="45.0",
            estado=EstadoNotaCorte.EN_PLAN,
        )
    )
    assert nota.id is not None

    recuperada = repo.get_nota_corte(corte.id, est_id)
    assert recuperada is not None
    assert recuperada.estudiante_id == est_id
    assert recuperada.estado == EstadoNotaCorte.EN_PLAN


def test_listar_notas_corte(db_conn, seed_result):
    """listar_notas_corte retorna todas las notas de un corte."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    asig_id = seed_result.asignacion_ids[0]
    per_id = seed_result.periodo_ids[0]

    corte = _hacer_corte(repo, asig_id, per_id)

    for est_id in seed_result.estudiante_ids:
        repo.guardar_nota_corte(
            NotaCortePlan(
                corte_id=corte.id,
                estudiante_id=est_id,
                asignacion_id=asig_id,
                periodo_id=per_id,
                nota_al_corte="40.0",
                estado=EstadoNotaCorte.EN_PLAN,
            )
        )

    notas = repo.listar_notas_corte(corte.id)
    assert len(notas) == len(seed_result.estudiante_ids)


def test_actualizar_nota_corte(db_conn, seed_result):
    """actualizar_nota_corte cambia estado y nota_definitiva_plan."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    asig_id = seed_result.asignacion_ids[0]
    per_id = seed_result.periodo_ids[0]
    est_id = seed_result.estudiante_ids[0]

    corte = _hacer_corte(repo, asig_id, per_id)
    nota = repo.guardar_nota_corte(
        NotaCortePlan(
            corte_id=corte.id,
            estudiante_id=est_id,
            asignacion_id=asig_id,
            periodo_id=per_id,
            nota_al_corte="45.0",
            estado=EstadoNotaCorte.EN_PLAN,
        )
    )

    nota_actualizada = nota.model_copy(
        update={"nota_definitiva_plan": "75.0", "estado": EstadoNotaCorte.APROBADO}
    )
    repo.actualizar_nota_corte(nota_actualizada)

    recuperada = repo.get_nota_corte(corte.id, est_id)
    assert recuperada is not None
    assert recuperada.estado == EstadoNotaCorte.APROBADO


# ---------------------------------------------------------------------------
# Actividades del plan
# ---------------------------------------------------------------------------


def test_guardar_y_obtener_actividad(db_conn, seed_result):
    """guardar_actividad y get_actividad hacen roundtrip correcto."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    asig_id = seed_result.asignacion_ids[0]
    per_id = seed_result.periodo_ids[0]

    corte = _hacer_corte(repo, asig_id, per_id)

    act = repo.guardar_actividad(
        ActividadPlan(
            corte_id=corte.id,
            asignacion_id=asig_id,
            periodo_id=per_id,
            nombre="Taller recuperación",
            peso="0.5",
        )
    )
    assert act.id is not None

    recuperada = repo.get_actividad(act.id)
    assert recuperada is not None
    assert recuperada.nombre == "Taller recuperación"


def test_listar_actividades(db_conn, seed_result):
    """listar_actividades retorna solo las del corte dado."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    asig_id = seed_result.asignacion_ids[0]
    per_id = seed_result.periodo_ids[0]

    corte = _hacer_corte(repo, asig_id, per_id)
    repo.guardar_actividad(
        ActividadPlan(corte_id=corte.id, asignacion_id=asig_id, periodo_id=per_id, nombre="A1", peso="0.3")
    )
    repo.guardar_actividad(
        ActividadPlan(corte_id=corte.id, asignacion_id=asig_id, periodo_id=per_id, nombre="A2", peso="0.4")
    )

    actividades = repo.listar_actividades(corte.id)
    assert len(actividades) == 2


def test_suma_pesos_actividades(db_conn, seed_result):
    """suma_pesos_actividades retorna la suma correcta; 0.0 para corte vacío."""
    repo = SqlaPlanMejoramientoRepository(conn=db_conn)
    asig_id = seed_result.asignacion_ids[0]
    per_id = seed_result.periodo_ids[0]

    corte = _hacer_corte(repo, asig_id, per_id)

    assert repo.suma_pesos_actividades(corte.id) == 0.0

    repo.guardar_actividad(
        ActividadPlan(corte_id=corte.id, asignacion_id=asig_id, periodo_id=per_id, nombre="A1", peso="0.3")
    )
    repo.guardar_actividad(
        ActividadPlan(corte_id=corte.id, asignacion_id=asig_id, periodo_id=per_id, nombre="A2", peso="0.4")
    )

    assert abs(repo.suma_pesos_actividades(corte.id) - 0.7) < 0.001
