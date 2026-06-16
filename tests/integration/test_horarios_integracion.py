"""
Tests de integración — Conexión plan de estudios ↔ asignaciones ↔ horarios.

Verifican que toda la cadena queda consistente:
  • El generador usa las horas del PLAN DE ESTUDIOS por grado (no las globales).
  • Genera un horario COMPLETO a partir del seed (plan ↔ asignaciones alineados).
  • Los bloques generados usan el AULA PROPIA de cada grupo.
  • La carga docente y la cobertura del plan son coherentes.
  • Quitar una materia del plan PROPAGA la baja a las asignaciones del docente.
  • La validación de carga máxima bloquea sobrecupos.

Cada test recibe una BD en memoria fresca (seed_dev) con servicios cableados.
"""
from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from src.infrastructure.db.schema import SCHEMA, INDICES, TRIGGERS
from src.infrastructure.db.seed import seed_dev, _fast_hasher

from src.infrastructure.db.repositories.sqlite_infraestructura_repo import SqliteInfraestructuraRepository
from src.infrastructure.db.repositories.sqlite_asignacion_repo import SqliteAsignacionRepository
from src.infrastructure.db.repositories.sqlite_usuario_repo import SqliteUsuarioRepository
from src.infrastructure.db.repositories.sqlite_periodo_repo import SqlitePeriodoRepository
from src.infrastructure.db.repositories.sqlite_configuracion_repo import SqliteConfiguracionRepository

from src.services.plan_estudios_service import PlanEstudiosService
from src.services.infraestructura_service import InfraestructuraService, Asignatura
from src.services.usuario_service import UsuarioService
from src.services.asignacion_service import (
    AsignacionService, FiltroAsignacionesDTO, NuevaAsignacionDTO,
)
from src.services.horario_service import HorarioService
from src.services.generador_horario_service import GeneradorHorarioService
from src.services.preparacion_horario_service import PreparacionHorarioService


@pytest.fixture()
def env():
    """BD en memoria con seed_dev y todos los servicios cableados a la conexión."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    for sql in SCHEMA:
        conn.execute(sql)
    for sql in INDICES:
        conn.execute(sql)
    for sql in TRIGGERS:
        conn.execute(sql)
    conn.commit()
    seed_dev(conn, anio=2025, hasher=_fast_hasher, total_estudiantes=8, seed_random=7)
    conn.commit()

    infra_repo = SqliteInfraestructuraRepository(conn)
    asig_repo = SqliteAsignacionRepository(conn)
    usu_repo = SqliteUsuarioRepository(conn)
    per_repo = SqlitePeriodoRepository(conn)
    cfg_repo = SqliteConfiguracionRepository(conn)

    plan = PlanEstudiosService(repo=infra_repo)
    infra = InfraestructuraService(repo=infra_repo)
    usuario_svc = UsuarioService(repo=usu_repo)
    asig = AsignacionService(
        repo=asig_repo, periodo_repo=per_repo, usuario_repo=usu_repo,
        infra_repo=infra_repo, plan_svc=plan,
    )
    horario = HorarioService(
        infra_repo=infra_repo, asignacion_repo=asig_repo,
        usuario_repo=usuario_svc, plan_svc=plan,
    )
    gen = GeneradorHorarioService(
        infra_repo=infra_repo, asignacion_repo=asig_repo, usuario_repo=usuario_svc,
        horario_service=horario, infraestructura_service=infra, plan_svc=plan,
    )
    prep = PreparacionHorarioService(
        infra_repo=infra_repo, asignacion_repo=asig_repo, config_repo=cfg_repo,
        periodo_repo=per_repo, usuario_repo=usu_repo, plan_svc=plan,
    )

    cfg = conn.execute(
        "SELECT id, periodo_id, anio_id, plantilla_id FROM config_generacion LIMIT 1"
    ).fetchone()

    yield SimpleNamespace(
        conn=conn, infra_repo=infra_repo, asig_repo=asig_repo,
        plan=plan, infra=infra, usuario=usuario_svc, asig=asig, gen=gen, prep=prep,
        config_id=cfg["id"], periodo_id=cfg["periodo_id"],
        anio_id=cfg["anio_id"], plantilla_id=cfg["plantilla_id"],
    )
    conn.close()


# ───────────────────────────────────────────────────────────────────────────
# Generación completa y consistente
# ───────────────────────────────────────────────────────────────────────────

def test_generacion_completa_desde_seed(env):
    """El seed (plan ↔ asignaciones alineados) genera un horario COMPLETO."""
    res = env.gen.generar(env.config_id, crear_escenario=True, optimizar=True)
    assert res.total_requeridos > 0
    assert res.no_colocados == 0
    assert res.colocados == res.total_requeridos
    assert res.valido is True


def test_generador_usa_horas_del_plan(env):
    """total_requeridos == suma de horas del PLAN por grado (no las globales)."""
    grado_de = {g.id: g.grado for g in env.infra.listar_grupos()}
    asigns = env.asig_repo.listar(
        FiltroAsignacionesDTO(periodo_id=env.periodo_id, solo_activas=True, por_pagina=500)
    )
    esperado = sum(env.plan.horas_de(grado_de[a.grupo_id], a.asignatura_id) for a in asigns)

    res = env.gen.generar(env.config_id, crear_escenario=False, optimizar=False)
    assert res.total_requeridos == esperado


def test_cambiar_plan_cambia_demanda_del_generador(env):
    """Editar las horas de una materia en el plan altera la demanda del generador."""
    res0 = env.gen.generar(env.config_id, crear_escenario=False, optimizar=False)
    # Subir 2h una materia del grado 6 que esté asignada en algún grupo de 6º
    plan6 = env.plan.por_grado(6)
    aid = plan6[0].asignatura_id
    env.plan.set_horas(6, aid, plan6[0].horas_semanales + 2)
    res1 = env.gen.generar(env.config_id, crear_escenario=False, optimizar=False)
    # Hay 2 grupos de 6º (601, 602) → +2h cada uno con asignación de esa materia
    assert res1.total_requeridos > res0.total_requeridos


# ───────────────────────────────────────────────────────────────────────────
# Aulas propias en los bloques
# ───────────────────────────────────────────────────────────────────────────

def test_bloques_usan_aula_propia_del_grupo(env):
    """Cada bloque generado de una clase normal usa el aula propia del grupo."""
    res = env.gen.generar(env.config_id, crear_escenario=False, optimizar=False)
    codigo_de = {g.id: g.codigo for g in env.infra.listar_grupos()}
    assert res.bloques, "Debe haber bloques generados"
    for b in res.bloques:
        assert b.sala == f"Aula {codigo_de[b.grupo_id]}", (
            f"grupo {codigo_de.get(b.grupo_id)} debería estar en su aula propia, no {b.sala}"
        )


# ───────────────────────────────────────────────────────────────────────────
# Preparación (puertas) coherente con el plan
# ───────────────────────────────────────────────────────────────────────────

def test_preparacion_permite_generar(env):
    """Con el seed (plan ≤ cupos, plantilla lista) las puertas duras pasan."""
    reporte = env.prep.validar(env.anio_id, env.periodo_id, env.plantilla_id)
    capacidad = next(p for p in reporte if p.id == "horas_grupo_vs_slots")
    plantilla = next(p for p in reporte if p.id == "plantilla_suficiente")
    assert capacidad.ok, capacidad.detalle
    assert plantilla.ok, plantilla.detalle
    assert env.prep.puede_generar(reporte) is True


# ───────────────────────────────────────────────────────────────────────────
# Propagación plan → asignaciones
# ───────────────────────────────────────────────────────────────────────────

def test_quitar_del_plan_propaga_a_asignaciones(env):
    """Quitar una materia del plan desactiva las asignaciones de ese grado."""
    grupos6 = [g.id for g in env.infra.listar_grupos(grado=6)]
    plan6 = env.plan.por_grado(6)
    # Elegir una materia del plan de 6º con asignaciones activas
    objetivo = None
    for p in plan6:
        activas = sum(
            len(env.asig.listar_con_info(FiltroAsignacionesDTO(
                grupo_id=gid, asignatura_id=p.asignatura_id, solo_activas=True)))
            for gid in grupos6
        )
        if activas:
            objetivo = (p.asignatura_id, activas)
            break
    assert objetivo, "El seed debe tener asignaciones para el plan de 6º"
    aid, _ = objetivo

    env.plan.eliminar(6, aid)
    n = env.asig.desactivar_por_grado_asignatura(6, aid)

    assert n > 0
    restantes = sum(
        len(env.asig.listar_con_info(FiltroAsignacionesDTO(
            grupo_id=gid, asignatura_id=aid, solo_activas=True)))
        for gid in grupos6
    )
    assert restantes == 0
    assert all(p.asignatura_id != aid for p in env.plan.por_grado(6))


# ───────────────────────────────────────────────────────────────────────────
# Carga docente
# ───────────────────────────────────────────────────────────────────────────

def test_carga_docente_usa_horas_del_plan(env):
    """carga_docente suma las horas del plan de las asignaciones activas."""
    did = env.asig_repo.listar(
        FiltroAsignacionesDTO(periodo_id=env.periodo_id, solo_activas=True)
    )[0].usuario_id
    grado_de = {g.id: g.grado for g in env.infra.listar_grupos()}
    mis = env.asig_repo.listar(
        FiltroAsignacionesDTO(usuario_id=did, periodo_id=env.periodo_id,
                              solo_activas=True, por_pagina=500)
    )
    esperado = sum(env.plan.horas_de(grado_de[a.grupo_id], a.asignatura_id) for a in mis)
    assert env.asig.carga_docente(did, env.periodo_id) == esperado


def test_tope_de_carga_bloquea_sobrecupo(env):
    """Asignar por encima del tope efectivo del docente lanza ValueError."""
    did = env.asig_repo.listar(
        FiltroAsignacionesDTO(periodo_id=env.periodo_id, solo_activas=True)
    )[0].usuario_id
    # Reducir el tope por debajo de la carga actual
    env.usuario.configurar_carga(did, carga_horaria_max=1, horas_extra=0)
    # Materia nueva (no duplicada) para forzar el chequeo de carga
    nueva = env.infra.guardar_asignatura(Asignatura(nombre="Materia Test", codigo="MTST"))
    grupo_id = env.infra.listar_grupos(grado=6)[0].id
    with pytest.raises(ValueError):
        env.asig.crear_asignacion(NuevaAsignacionDTO(
            usuario_id=did, grupo_id=grupo_id,
            asignatura_id=nueva.id, periodo_id=env.periodo_id,
        ))
