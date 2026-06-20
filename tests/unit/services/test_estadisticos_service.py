"""Tests unitarios para EstadisticosService."""
from __future__ import annotations

from typing import Any

import pytest

from src.domain.models.configuracion import NivelDesempeno
from src.domain.models.dtos import DashboardMetricsDTO
from src.domain.ports.estadisticos_repo import IEstadisticosRepository
from src.services.estadisticos_service import EstadisticosService


# ===========================================================================
# Fake
# ===========================================================================

class FakeEstadRepo(IEstadisticosRepository):
    def calcular_metricas_dashboard(self, grupo_id, periodo_id, nota_minima=60.0) -> DashboardMetricsDTO:
        return DashboardMetricsDTO(
            grupo_id=grupo_id,
            total_estudiantes=25,
            promedio_general=72.5,
            porcentaje_asistencia=90.0,
            estudiantes_en_riesgo=3,
            actividades_publicadas=8,
            alertas_pendientes=2,
        )

    def promedio_general_grupo(self, grupo_id, periodo_id, nota_minima=60.0) -> float:
        return 72.5

    def porcentaje_asistencia_global(self, grupo_id, periodo_id) -> float:
        return 88.0

    def contar_alertas_pendientes(self, grupo_id) -> int:
        return 2

    def promedio_por_asignacion(self, grupo_id, asignacion_id, periodo_id) -> float:
        return 75.0

    def distribucion_desempenos(self, grupo_id, asig_id, per_id, niveles) -> dict[str, int]:
        return {n.nombre: 5 for n in niveles}

    def comparativo_periodos(self, grupo_id, asig_id, anio_id) -> list[dict[str, Any]]:
        return [{"periodo_nombre": "P1", "promedio": 70.0}]

    def promedios_por_area(self, grupo_id, per_id) -> list[dict[str, Any]]:
        return []

    def estudiantes_en_riesgo_academico(self, grupo_id, per_id, nota_minima=60.0, min_asig=1) -> list[int]:
        return [1, 2, 3]

    def ranking_grupo(self, grupo_id, per_id) -> list[dict[str, Any]]:
        return []

    def tendencia_asistencia(self, grupo_id, asig_id, per_id) -> list[dict[str, Any]]:
        return []

    def distribucion_estados_asistencia(self, grupo_id, asig_id, per_id) -> dict[str, int]:
        return {"P": 100, "FI": 5}

    def consolidado_notas_grupo(self, grupo_id, per_id) -> list[dict[str, Any]]:
        return [{"nombre": "Estudiante A", "matematicas": 80.0}]

    def consolidado_asistencia_grupo(self, grupo_id, per_id) -> list[dict[str, Any]]:
        return []

    def consolidado_anual_grupo(self, grupo_id, anio_id) -> list[dict[str, Any]]:
        return []

    def boletin_datos_periodo(self, estudiante_id, grupo_id, periodo_id):
        return {"estudiante": {}, "areas": []}

    def boletin_datos_acumulado(self, estudiante_id, grupo_id, hasta_periodo_id):
        return {"estudiante": {}, "periodos": [], "areas": [], "es_ultimo_periodo": False}

    def boletin_datos_anual(self, estudiante_id, grupo_id, anio_id):
        return {"estudiante": {}, "periodos": [], "areas": []}


# ===========================================================================
# Tests
# ===========================================================================

class TestMetricasDashboard:
    def test_retorna_metricas_dto(self):
        svc = EstadisticosService(FakeEstadRepo())
        m = svc.metricas_dashboard(grupo_id=10, periodo_id=5)
        assert m.total_estudiantes == 25
        assert m.promedio_general == pytest.approx(72.5)

    def test_promedio_general_grupo(self):
        svc = EstadisticosService(FakeEstadRepo())
        prom = svc.promedio_general_grupo(grupo_id=10, periodo_id=5)
        assert prom == pytest.approx(72.5)

    def test_porcentaje_asistencia(self):
        svc = EstadisticosService(FakeEstadRepo())
        pct = svc.porcentaje_asistencia_global(grupo_id=10, periodo_id=5)
        assert pct == pytest.approx(88.0)


class TestEstadisticasNotas:
    def test_comparativo_periodos(self):
        svc = EstadisticosService(FakeEstadRepo())
        resultado = svc.comparativo_periodos(grupo_id=10, asignacion_id=3, anio_id=1)
        assert len(resultado) == 1
        assert resultado[0]["periodo_nombre"] == "P1"

    def test_estudiantes_en_riesgo(self):
        svc = EstadisticosService(FakeEstadRepo())
        en_riesgo = svc.estudiantes_en_riesgo_academico(grupo_id=10, periodo_id=5)
        assert len(en_riesgo) == 3


class TestConsolidados:
    def test_consolidado_notas_retorna_lista(self):
        svc = EstadisticosService(FakeEstadRepo())
        datos = svc.consolidado_notas_grupo(grupo_id=10, periodo_id=5)
        assert len(datos) == 1

    def test_consolidado_anual_retorna_lista(self):
        svc = EstadisticosService(FakeEstadRepo())
        datos = svc.consolidado_anual_grupo(grupo_id=10, anio_id=1)
        assert isinstance(datos, list)


# ===========================================================================
# Group 5 — métricas institucionales (agregador, sin N+1 en la vista)
# ===========================================================================

class _Grupo:
    def __init__(self, gid, codigo):
        self.id = gid
        self.codigo = codigo


class _FakeInfraRepo:
    def __init__(self, grupos):
        self._grupos = grupos
    def listar_grupos(self, grado=None):
        return self._grupos


class TestMetricasInstitucionales:
    def test_agrega_todos_los_grupos(self):
        infra = _FakeInfraRepo([_Grupo(1, "601"), _Grupo(2, "602")])
        svc = EstadisticosService(FakeEstadRepo(), infra_repo=infra)
        r = svc.metricas_institucionales(periodo_id=5)
        assert r.kpi_grupos == 2
        assert r.kpi_promedio == 72.5
        assert r.kpi_asistencia == 90.0
        assert r.kpi_riesgo == 6  # 3 + 3
        assert [f["codigo"] for f in r.grupos] == ["601", "602"]

    def test_sin_periodo_devuelve_vacio(self):
        infra = _FakeInfraRepo([_Grupo(1, "601")])
        svc = EstadisticosService(FakeEstadRepo(), infra_repo=infra)
        r = svc.metricas_institucionales(periodo_id=0)
        assert r.kpi_grupos == 0 and r.grupos == []

    def test_sin_infra_repo_devuelve_vacio(self):
        svc = EstadisticosService(FakeEstadRepo())
        r = svc.metricas_institucionales(periodo_id=5)
        assert r.kpi_grupos == 0


# ===========================================================================
# Group 6 — pendientes del docente (agregador de solo lectura)
# ===========================================================================

class _AsigInfo:
    def __init__(self, asignacion_id, grupo_id):
        self.asignacion_id = asignacion_id
        self.grupo_id = grupo_id


class _FakeAsignacionRepo:
    def __init__(self, asignaciones):
        self._asigs = asignaciones
    def listar_por_docente(self, usuario_id, periodo_id=None, solo_activas=True):
        return self._asigs


class _Act:
    def __init__(self, aid, publicada=True):
        self.id = aid
        self.esta_publicada = publicada


class _FakeEvalRepo:
    """notas_por_act: {actividad_id: [notas]}"""
    def __init__(self, actividades_por_asig, notas_por_act):
        self._acts = actividades_por_asig
        self._notas = notas_por_act
    def listar_actividades(self, asignacion_id, periodo_id):
        return self._acts.get(asignacion_id, [])
    def listar_notas_por_actividad(self, actividad_id):
        return self._notas.get(actividad_id, [])


class _FakeAsistRepo:
    """con_registro: set de (grupo_id, asignacion_id) que SÍ tienen asistencia hoy."""
    def __init__(self, con_registro):
        self._con = con_registro
    def listar_por_grupo_y_fecha(self, grupo_id, asignacion_id, fecha):
        return ["x"] if (grupo_id, asignacion_id) in self._con else []


class _Est:
    def __init__(self, eid):
        self.id = eid


class _FakeEstRepo:
    def __init__(self, por_grupo):
        self._por_grupo = por_grupo
    def listar_por_grupo(self, grupo_id, solo_activos=True):
        return self._por_grupo.get(grupo_id, [])


class _FakeAlertaRepo:
    def __init__(self, pendientes_por_est):
        self._p = pendientes_por_est
    def contar_pendientes(self, estudiante_id, nivel=None):
        return self._p.get(estudiante_id, 0)


class TestPendientesDocente:
    def _svc(self):
        asig = _FakeAsignacionRepo([_AsigInfo(11, 1), _AsigInfo(12, 2)])
        # asig 11 -> act 100 (sin notas), act 101 (con notas)
        # asig 12 -> act 102 (borrador, no cuenta)
        eval_repo = _FakeEvalRepo(
            {11: [_Act(100), _Act(101)], 12: [_Act(102, publicada=False)]},
            {100: [], 101: ["n1"], 102: []},
        )
        # asistencia hoy registrada solo para (grupo 1, asig 11)
        asist = _FakeAsistRepo({(1, 11)})
        est = _FakeEstRepo({1: [_Est(1001), _Est(1002)], 2: [_Est(2001)]})
        alertas = _FakeAlertaRepo({1001: 2, 1002: 0, 2001: 1})
        return EstadisticosService(
            FakeEstadRepo(),
            evaluacion_repo=eval_repo,
            asistencia_repo=asist,
            estudiante_repo=est,
            asignacion_repo=asig,
            alerta_repo=alertas,
        )

    def test_agrega_pendientes(self):
        d = self._svc().pendientes_docente(usuario_id=4, periodo_id=5, anio_id=1)
        assert d.total_asignaciones == 2
        assert d.actividades_sin_calificar == 1     # solo act 100
        assert d.asignaciones_sin_asistencia == 1   # solo asig 12 sin registro hoy
        assert d.alertas_estudiantes == 3           # 2 + 0 + 1
        assert d.hay_pendientes is True

    def test_sin_asignacion_repo_devuelve_vacio(self):
        svc = EstadisticosService(FakeEstadRepo())
        d = svc.pendientes_docente(usuario_id=4, periodo_id=5)
        assert d.total_asignaciones == 0
        assert d.hay_pendientes is False

    def test_sin_usuario_devuelve_vacio(self):
        d = self._svc().pendientes_docente(usuario_id=0, periodo_id=5)
        assert d.total_asignaciones == 0
