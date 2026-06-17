"""
Test de estrés del generador de horarios.

Construye escenarios SINTÉTICOS aleatorios (variando nº de grados, grupos,
asignaturas, horas del plan, docentes, cupos de la plantilla y restricciones)
y verifica invariantes que deben cumplirse SIEMPRE, con pocas o con amplias
restricciones:

  • El generador nunca lanza una excepción.
  • Contabilidad: colocados + no_colocados == total_requeridos.
  • Sin choques: ningún grupo ni docente queda en dos lugares a la vez.
  • Todo bloque cae en una franja lectiva.
  • Se respeta la disponibilidad docente (nunca coloca en una franja vetada).

Además, en escenarios "holgados" (capacidad amplia, sin restricciones duras)
se exige que el horario salga COMPLETO (no_colocados == 0), validando que el
camino óptimo (König) resuelve cuando la instancia es factible.
"""
from __future__ import annotations

import random
import sqlite3

import pytest

from src.infrastructure.db.schema import SCHEMA, INDICES, TRIGGERS
from src.infrastructure.db.repositories.sqlite_infraestructura_repo import SqliteInfraestructuraRepository
from src.infrastructure.db.repositories.sqlite_asignacion_repo import SqliteAsignacionRepository
from src.infrastructure.db.repositories.sqlite_usuario_repo import SqliteUsuarioRepository
from src.services.infraestructura_service import InfraestructuraService
from src.services.usuario_service import UsuarioService
from src.services.plan_estudios_service import PlanEstudiosService
from src.services.horario_service import HorarioService
from src.services.generador_horario_service import GeneradorHorarioService

_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]


def _conn():
    c = sqlite3.connect(":memory:", check_same_thread=False)
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    for sql in SCHEMA:
        c.execute(sql)
    for sql in INDICES:
        c.execute(sql)
    for sql in TRIGGERS:
        c.execute(sql)
    c.commit()
    return c


def _construir(conn, rng, holgado: bool) -> dict:
    """Crea un escenario sintético aleatorio. Devuelve datos para los asserts."""
    cur = conn.cursor()
    cur.execute("INSERT INTO configuracion_anio (anio, activo) VALUES (2025, 1)")
    anio_id = cur.lastrowid
    cur.execute("INSERT INTO periodos (anio_id, nombre, numero, activo) VALUES (?, 'P1', 1, 1)", (anio_id,))
    per_id = cur.lastrowid
    cur.execute("INSERT INTO areas_conocimiento (nombre) VALUES ('General')")
    area_id = cur.lastrowid

    n_grados = rng.randint(1, 4)
    grupos_por_grado = rng.randint(1, 3)
    n_asig = rng.randint(4, 8)

    asig_ids = []
    for i in range(n_asig):
        cur.execute(
            "INSERT INTO asignaturas (nombre, codigo, area_id, horas_semanales) VALUES (?,?,?,1)",
            (f"Asignatura {i}", f"A{i}", area_id),
        )
        asig_ids.append(cur.lastrowid)

    grados = list(range(1, n_grados + 1))
    plan: dict[int, list[tuple[int, int]]] = {}
    for g in grados:
        k = rng.randint(3, n_asig)
        plan[g] = [(aid, rng.randint(1, 4)) for aid in rng.sample(asig_ids, k)]
    max_demanda = max(sum(h for _, h in plan[g]) for g in grados)

    # Cupos de la plantilla (franjas lectivas × días)
    if holgado:
        cupos_obj = max_demanda + rng.randint(5, 12)
    else:
        cupos_obj = max_demanda + rng.randint(0, 3)
    n_lectivas = max(1, -(-cupos_obj // len(_DIAS)))  # ceil
    cupos = n_lectivas * len(_DIAS)
    lectiva_ordenes = list(range(1, n_lectivas + 1))

    cur.execute(
        "INSERT INTO plantillas_franja (nombre, jornada, dias_activos, activa) VALUES ('PL','UNICA',?,1)",
        (",".join(_DIAS),),
    )
    pl_id = cur.lastrowid
    for o in lectiva_ordenes:
        cur.execute(
            "INSERT INTO franjas (plantilla_id, orden, hora_inicio, hora_fin, tipo) VALUES (?,?,?,?, 'lectiva')",
            (pl_id, o, f"{6 + o:02d}:00", f"{6 + o:02d}:50"),
        )

    for g in grados:
        tot = sum(h for _, h in plan[g])
        cur.execute(
            "INSERT INTO grados (numero, nombre, min_estudiantes, max_estudiantes, horas_semanales) "
            "VALUES (?,?,0,40,?)",
            (g, f"G{g}", tot),
        )
        for (aid, h) in plan[g]:
            cur.execute(
                "INSERT INTO plan_estudios (grado, asignatura_id, horas_semanales) VALUES (?,?,?)",
                (g, aid, h),
            )

    grupos: list[tuple[int, int]] = []
    for g in grados:
        for j in range(grupos_por_grado):
            cur.execute(
                "INSERT INTO grupos (codigo, nombre, grado, jornada, capacidad_maxima) "
                "VALUES (?,?,?, 'UNICA', 40)",
                (f"{g}{j}", f"G{g}-{j}", g),
            )
            grupos.append((cur.lastrowid, g))

    demanda_total = sum(sum(h for _, h in plan[g]) for (_gid, g) in grupos)
    # Capacidad docente: en holgado, cap ≤ cupos (factible por König) y de sobra.
    if holgado:
        cap = cupos
        n_doc = -(-demanda_total // cap) + rng.randint(2, 5)
    else:
        cap = rng.randint(max(4, cupos // 2), cupos)
        n_doc = max(1, -(-demanda_total // cap) + rng.randint(0, 2))

    docentes = []
    for i in range(n_doc):
        cur.execute(
            "INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol, carga_horaria_max) "
            "VALUES (?, 'x', ?, 'profesor', ?)",
            (f"doc{i}", f"Doc {i}", cap),
        )
        docentes.append(cur.lastrowid)

    carga = {d: 0 for d in docentes}
    for (gid, g) in grupos:
        for (aid, h) in plan[g]:
            cand = [d for d in docentes if carga[d] + h <= cap]
            if not cand:
                continue
            tid = max(cand, key=lambda d: cap - carga[d])
            carga[tid] += h
            cur.execute(
                "INSERT OR IGNORE INTO asignaciones "
                "(grupo_id, asignatura_id, usuario_id, periodo_id, activo) VALUES (?,?,?,?,1)",
                (gid, aid, tid, per_id),
            )

    if not holgado:
        # Restricciones amplias: disponibilidad vetada + límites diarios.
        for d in docentes:
            for dia in _DIAS:
                for o in lectiva_ordenes:
                    if rng.random() < 0.15:
                        cur.execute(
                            "INSERT OR IGNORE INTO disponibilidad_docente "
                            "(usuario_id, dia_semana, franja_orden, disponible) VALUES (?,?,?,0)",
                            (d, dia, o),
                        )
            if rng.random() < 0.4:
                cur.execute(
                    "INSERT OR IGNORE INTO limites_docente "
                    "(usuario_id, min_horas_dia, max_horas_dia) VALUES (?, 0, ?)",
                    (d, rng.randint(2, n_lectivas)),
                )

    cur.execute(
        "INSERT INTO config_generacion (nombre, periodo_id, anio_id, plantilla_id, grupos_json) "
        "VALUES ('cfg', ?, ?, ?, '[]')",
        (per_id, anio_id, pl_id),
    )
    cfg_id = cur.lastrowid
    conn.commit()
    return {
        "config_id": cfg_id,
        "lectivas": set(lectiva_ordenes),
        "holgado": holgado,
        "n_grados": n_grados,
        "grupos": len(grupos),
        "cupos": cupos,
        "max_demanda": max_demanda,
    }


def _wire(conn):
    ir = SqliteInfraestructuraRepository(conn)
    ar = SqliteAsignacionRepository(conn)
    ur = SqliteUsuarioRepository(conn)
    usv = UsuarioService(repo=ur)
    plan = PlanEstudiosService(repo=ir)
    infra = InfraestructuraService(repo=ir)
    hs = HorarioService(infra_repo=ir, asignacion_repo=ar, usuario_repo=usv, plan_svc=plan)
    gen = GeneradorHorarioService(
        infra_repo=ir, asignacion_repo=ar, usuario_repo=usv,
        horario_service=hs, infraestructura_service=infra, plan_svc=plan,
    )
    return ir, gen


@pytest.mark.parametrize("trial", range(30))
def test_estres_generacion(trial):
    rng = random.Random(1000 + trial)
    holgado = (trial % 2 == 0)
    conn = _conn()
    try:
        info = _construir(conn, rng, holgado)
        ir, gen = _wire(conn)

        # No debe lanzar nunca, con pocas o muchas restricciones.
        res = gen.generar(info["config_id"], crear_escenario=False, optimizar=True)

        # Contabilidad
        assert res.colocados + res.no_colocados == res.total_requeridos, (
            f"trial {trial}: contabilidad rota"
        )
        assert res.colocados == len(res.bloques)

        # Sin choques de grupo / docente y solo en franjas lectivas
        vistos_grupo: set = set()
        vistos_docente: set = set()
        for b in res.bloques:
            kg = (b.grupo_id, b.dia_semana, b.franja_orden)
            kd = (b.usuario_id, b.dia_semana, b.franja_orden)
            assert kg not in vistos_grupo, f"trial {trial}: choque de grupo {kg}"
            assert kd not in vistos_docente, f"trial {trial}: choque de docente {kd}"
            vistos_grupo.add(kg)
            vistos_docente.add(kd)
            assert b.franja_orden in info["lectivas"], (
                f"trial {trial}: bloque en franja no lectiva {b.franja_orden}"
            )
            # Disponibilidad docente respetada (nunca relajada por el motor)
            assert ir.es_disponible(b.usuario_id, b.dia_semana, b.franja_orden), (
                f"trial {trial}: bloque en franja vetada para docente {b.usuario_id}"
            )

        # Escenarios holgados: el horario debe salir COMPLETO.
        if info["holgado"]:
            assert res.no_colocados == 0, (
                f"trial {trial} (holgado): quedaron {res.no_colocados} sin colocar "
                f"(cupos={info['cupos']}, max_demanda={info['max_demanda']})"
            )
    finally:
        conn.close()
