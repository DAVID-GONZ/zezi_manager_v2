"""
Tests de integración — multi-tenant frente B3 (paso_31).

Cubre el pase de scope en la capa de servicios (SIN migraciones nuevas):

  - AsignacionService.listar_con_info / listar_por_docente / listar_por_grupo:
    con dos instituciones, un director (contextvar fijado) ve solo las
    asignaciones cuyos grupos son de su institución; admin (None) ve todo.
    El scope se hereda del JOIN a `grupos` (g.institucion_id).
  - CierreService.resumen_cierres_institucional: el agregado que cruza todas
    las asignaciones del periodo se scopea por institución (un director no ve
    el estado de cierres de otra institución).
  - EstadisticosService.metricas_institucionales: el agregado que recorre
    TODOS los grupos del periodo se scopea por institución (corrige el
    dashboard del directivo en multi-tenant).

Las consultas sobre UNA asignación/UN grupo ya scopeado no se prueban aquí:
heredan el scope de su padre (decisión del spec B3).
"""
from __future__ import annotations

import sqlite3

from src.domain.models.asignacion import (
    FiltroAsignacionesDTO,
    NuevaAsignacionDTO,
)
from src.infrastructure.db.repositories.sqlite_asignacion_repo import (
    SqliteAsignacionRepository,
)
from src.infrastructure.db.repositories.sqlite_infraestructura_repo import (
    SqliteInfraestructuraRepository,
)
from src.services.asignacion_service import AsignacionService
from src.services.contexto_tenant import usar_institucion


# =============================================================================
# Helpers de montaje (dos instituciones con grupos + asignaciones)
# =============================================================================

def _crear_institucion(conn: sqlite3.Connection, nombre: str) -> int:
    cur = conn.execute(
        "INSERT INTO instituciones (nombre, activa) VALUES (?, 1)", (nombre,)
    )
    return int(cur.lastrowid)


def _crear_grupo(conn: sqlite3.Connection, codigo: str, institucion_id: int) -> int:
    cur = conn.execute(
        "INSERT INTO grupos (codigo, grado, jornada, institucion_id) "
        "VALUES (?, 6, 'UNICA', ?)",
        (codigo, institucion_id),
    )
    return int(cur.lastrowid)


def _montar_dos_instituciones(db_conn, seed_result):
    """Devuelve (asig_svc, ctx) con UNA asignación por institución en el periodo.

    El seed ya crea exactamente una asignación por periodo sobre el grupo del
    seed (grupo_a). Backfilleamos ese grupo a institución #1, así que la
    asignación del seed representa el dato de la institución #1. Creamos un
    grupo nuevo en la institución #2 con una asignación propia en el mismo
    periodo. Resultado: 1 asignación por institución en `periodo_id`.
    """
    inst_b = _crear_institucion(db_conn, "Colegio B3")

    # Backfill del grupo del seed a institución #1 (seed_test lo deja en NULL).
    grupo_a = seed_result.grupo_ids[0]
    db_conn.execute(
        "UPDATE grupos SET institucion_id = 1 WHERE id = ?", (grupo_a,)
    )
    grupo_b = _crear_grupo(db_conn, "B3-602", inst_b)

    periodo_id = seed_result.periodo_ids[1]   # periodo 2 (abierto, 1 asig seed)
    docente_id = seed_result.usuario_ids["prof_test"]
    asignatura_id = seed_result.asignatura_ids["MAT_T"]
    db_conn.commit()

    repo = SqliteAsignacionRepository(conn=db_conn)
    svc = AsignacionService(repo)

    # Asignación en la institución #2 (grupo nuevo). La de inst #1 ya la creó
    # el seed sobre grupo_a en este periodo.
    with usar_institucion(inst_b):
        svc.crear_asignacion(NuevaAsignacionDTO(
            grupo_id=grupo_b, asignatura_id=asignatura_id,
            usuario_id=docente_id, periodo_id=periodo_id,
        ))

    return svc, {
        "inst_b": inst_b,
        "grupo_a": grupo_a,
        "grupo_b": grupo_b,
        "periodo_id": periodo_id,
        "docente_id": docente_id,
    }


# =============================================================================
# T1 — Asignaciones scopeadas
# =============================================================================

class TestScopeAsignaciones:

    def test_listar_con_info_director_ve_solo_su_institucion(self, db_conn, seed_result):
        svc, ctx = _montar_dos_instituciones(db_conn, seed_result)
        periodo_id = ctx["periodo_id"]

        with usar_institucion(1):
            grupos_1 = {
                a.grupo_id
                for a in svc.listar_con_info(FiltroAsignacionesDTO(periodo_id=periodo_id))
            }
        assert ctx["grupo_a"] in grupos_1
        assert ctx["grupo_b"] not in grupos_1

        with usar_institucion(ctx["inst_b"]):
            grupos_b = {
                a.grupo_id
                for a in svc.listar_con_info(FiltroAsignacionesDTO(periodo_id=periodo_id))
            }
        assert ctx["grupo_b"] in grupos_b
        assert ctx["grupo_a"] not in grupos_b

        # Admin (sin scope) ve ambas.
        grupos_admin = {
            a.grupo_id
            for a in svc.listar_con_info(FiltroAsignacionesDTO(periodo_id=periodo_id))
        }
        assert {ctx["grupo_a"], ctx["grupo_b"]}.issubset(grupos_admin)

    def test_listar_por_docente_scopeado(self, db_conn, seed_result):
        svc, ctx = _montar_dos_instituciones(db_conn, seed_result)
        docente_id = ctx["docente_id"]
        periodo_id = ctx["periodo_id"]

        with usar_institucion(1):
            grupos_1 = {a.grupo_id for a in svc.listar_por_docente(docente_id, periodo_id)}
        assert grupos_1 == {ctx["grupo_a"]}

        with usar_institucion(ctx["inst_b"]):
            grupos_b = {a.grupo_id for a in svc.listar_por_docente(docente_id, periodo_id)}
        assert grupos_b == {ctx["grupo_b"]}

        # Admin ve las dos.
        grupos_admin = {a.grupo_id for a in svc.listar_por_docente(docente_id, periodo_id)}
        assert {ctx["grupo_a"], ctx["grupo_b"]}.issubset(grupos_admin)

    def test_filtro_institucion_explicito_respeta_caller(self, db_conn, seed_result):
        """Un institucion_id explícito en el filtro no es sobreescrito por el scope."""
        svc, ctx = _montar_dos_instituciones(db_conn, seed_result)
        periodo_id = ctx["periodo_id"]

        # Sin sesión (admin), pero filtro explícito a la institución B.
        grupos = {
            a.grupo_id
            for a in svc.listar_con_info(
                FiltroAsignacionesDTO(periodo_id=periodo_id, institucion_id=ctx["inst_b"])
            )
        }
        assert grupos == {ctx["grupo_b"]}

    def test_repo_listar_plano_scopeado(self, db_conn, seed_result):
        """listar() (SELECT plano, sin JOIN) también scopea vía subconsulta."""
        _svc, ctx = _montar_dos_instituciones(db_conn, seed_result)
        repo = SqliteAsignacionRepository(conn=db_conn)

        plano_1 = repo.listar(FiltroAsignacionesDTO(
            periodo_id=ctx["periodo_id"], institucion_id=1
        ))
        assert {a.grupo_id for a in plano_1} == {ctx["grupo_a"]}

        plano_b = repo.listar(FiltroAsignacionesDTO(
            periodo_id=ctx["periodo_id"], institucion_id=ctx["inst_b"]
        ))
        assert {a.grupo_id for a in plano_b} == {ctx["grupo_b"]}


# =============================================================================
# T2 — Cierres institucionales scopeados
# =============================================================================

class TestScopeCierres:

    def _cierre_svc(self, db_conn):
        from src.infrastructure.db.repositories.sqlite_cierre_repo import (
            SqliteCierreRepository,
        )
        from src.infrastructure.db.repositories.sqlite_evaluacion_repo import (
            SqliteEvaluacionRepository,
        )
        from src.infrastructure.db.repositories.sqlite_periodo_repo import (
            SqlitePeriodoRepository,
        )
        from src.infrastructure.db.repositories.sqlite_configuracion_repo import (
            SqliteConfiguracionRepository,
        )
        from src.infrastructure.db.repositories.sqlite_estudiante_repo import (
            SqliteEstudianteRepository,
        )
        from src.services.cierre_service import CierreService

        return CierreService(
            cierre_repo=SqliteCierreRepository(conn=db_conn),
            evaluacion_repo=SqliteEvaluacionRepository(conn=db_conn),
            periodo_repo=SqlitePeriodoRepository(conn=db_conn),
            config_repo=SqliteConfiguracionRepository(conn=db_conn),
            estudiante_repo=SqliteEstudianteRepository(conn=db_conn),
            asignacion_repo=SqliteAsignacionRepository(conn=db_conn),
        )

    def test_resumen_cierres_institucional_scopeado(self, db_conn, seed_result):
        _svc, ctx = _montar_dos_instituciones(db_conn, seed_result)
        cierre_svc = self._cierre_svc(db_conn)
        periodo_id = ctx["periodo_id"]

        # Cada institución tiene exactamente 1 asignación en el periodo montado.
        with usar_institucion(1):
            res_1 = cierre_svc.resumen_cierres_institucional(periodo_id)
        with usar_institucion(ctx["inst_b"]):
            res_b = cierre_svc.resumen_cierres_institucional(periodo_id)
        # Admin (None) ve las dos.
        res_admin = cierre_svc.resumen_cierres_institucional(periodo_id)

        assert res_1["total"] == 1
        assert res_b["total"] == 1
        assert res_admin["total"] == 2


# =============================================================================
# T3 — Estadísticos institucionales scopeados
# =============================================================================

class _EstadRepoConteo:
    """Repo de estadísticos falso: devuelve métricas no vacías para cualquier
    grupo, de modo que metricas_institucionales incluye una fila por grupo
    visible. Permite contar cuántos grupos entran al agregado."""

    def calcular_metricas_dashboard(self, grupo_id, periodo_id, nota_minima):
        from src.domain.models.dtos import DashboardMetricsDTO
        return DashboardMetricsDTO(
            grupo_id=grupo_id,
            total_estudiantes=10,
            promedio_general=80.0,
            porcentaje_asistencia=95.0,
            estudiantes_en_riesgo=1,
            actividades_publicadas=0,
            alertas_pendientes=0,
        )


class TestScopeEstadisticos:

    def test_metricas_institucionales_scopeadas(self, db_conn, seed_result):
        from src.services.estadisticos_service import EstadisticosService

        _svc, ctx = _montar_dos_instituciones(db_conn, seed_result)
        infra_repo = SqliteInfraestructuraRepository(conn=db_conn)
        est_svc = EstadisticosService(_EstadRepoConteo(), infra_repo=infra_repo)
        periodo_id = ctx["periodo_id"]

        with usar_institucion(1):
            m_1 = est_svc.metricas_institucionales(periodo_id)
            ids_1 = {f["grupo_id"] for f in m_1.grupos}
        assert ctx["grupo_a"] in ids_1
        assert ctx["grupo_b"] not in ids_1

        with usar_institucion(ctx["inst_b"]):
            m_b = est_svc.metricas_institucionales(periodo_id)
            ids_b = {f["grupo_id"] for f in m_b.grupos}
        assert ids_b == {ctx["grupo_b"]}

        # Admin (None) agrega ambos grupos.
        m_admin = est_svc.metricas_institucionales(periodo_id)
        ids_admin = {f["grupo_id"] for f in m_admin.grupos}
        assert {ctx["grupo_a"], ctx["grupo_b"]}.issubset(ids_admin)
