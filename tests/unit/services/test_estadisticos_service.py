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
