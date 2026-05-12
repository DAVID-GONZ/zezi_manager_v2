"""Tests unitarios para InformeService."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from src.domain.models.dtos import (
    FormatoInforme, InformeAsistenciaDTO, InformeNotasDTO,
)
from src.domain.ports.estadisticos_repo import IEstadisticosRepository
from src.domain.ports.service_ports import IExporterService
from src.domain.models.configuracion import NivelDesempeno
from src.domain.models.dtos import DashboardMetricsDTO
from src.services.informe_service import InformeService


# ===========================================================================
# Fakes
# ===========================================================================

class FakeEstadRepo(IEstadisticosRepository):
    def calcular_metricas_dashboard(self, g, p, nota_minima=60.0) -> DashboardMetricsDTO:
        return DashboardMetricsDTO(grupo_id=g)

    def promedio_general_grupo(self, g, p, nota_minima=60.0) -> float:
        return 70.0

    def porcentaje_asistencia_global(self, g, p) -> float:
        return 85.0

    def contar_alertas_pendientes(self, g) -> int:
        return 0

    def promedio_por_asignacion(self, g, a, p) -> float:
        return 70.0

    def distribucion_desempenos(self, g, a, p, niveles) -> dict[str, int]:
        return {}

    def comparativo_periodos(self, g, a, anio) -> list[dict[str, Any]]:
        return []

    def promedios_por_area(self, g, p) -> list[dict[str, Any]]:
        return []

    def estudiantes_en_riesgo_academico(self, g, p, nota_minima=60.0, min_asig=1) -> list[int]:
        return []

    def ranking_grupo(self, g, p) -> list[dict[str, Any]]:
        return []

    def tendencia_asistencia(self, g, a, p) -> list[dict[str, Any]]:
        return []

    def distribucion_estados_asistencia(self, g, a, p) -> dict[str, int]:
        return {}

    def consolidado_notas_grupo(self, g, p) -> list[dict[str, Any]]:
        return [{"nombre": "Est A", "matematicas": 80.0, "promedio_periodo": 80.0}]

    def consolidado_asistencia_grupo(self, g, p) -> list[dict[str, Any]]:
        return [{"nombre": "Est A", "presentes": 20}]

    def consolidado_anual_grupo(self, g, anio) -> list[dict[str, Any]]:
        return [{"nombre": "Est A", "nota_anual": 75.0}]


class FakeExporter(IExporterService):
    def exportar_excel(self, datos, nombre_hoja="Datos", ruta_destino=None) -> bytes:
        return b"EXCEL:" + str(len(datos)).encode()

    def exportar_pdf(self, html_content, ruta_destino=None) -> bytes:
        return b"PDF:" + html_content[:20].encode()

    def exportar_csv(self, datos, ruta_destino=None, encoding="utf-8-sig") -> bytes:
        return b"CSV"


# ===========================================================================
# Helpers
# ===========================================================================

def _dto_notas() -> InformeNotasDTO:
    return InformeNotasDTO(
        grupo_id=10, asignacion_id=3, periodo_id=5,
        fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 6, 30),
    )


def _dto_asistencia() -> InformeAsistenciaDTO:
    return InformeAsistenciaDTO(
        grupo_id=10, asignacion_id=3, periodo_id=5,
        fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 6, 30),
    )


# ===========================================================================
# Tests
# ===========================================================================

class TestSinExporter:
    def test_datos_informe_notas_sin_exporter(self):
        svc = InformeService(FakeEstadRepo())  # sin exporter
        datos = svc.datos_informe_notas(_dto_notas())
        assert len(datos) == 1

    def test_lanza_si_intenta_generar_sin_exporter(self):
        svc = InformeService(FakeEstadRepo())
        with pytest.raises(ValueError, match="exportador"):
            svc.generar_notas(_dto_notas())

    def test_datos_asistencia_sin_exporter(self):
        svc = InformeService(FakeEstadRepo())
        datos = svc.datos_informe_asistencia(_dto_asistencia())
        assert isinstance(datos, list)


class TestConExporter:
    def test_genera_notas_en_excel(self):
        svc = InformeService(FakeEstadRepo(), exporter=FakeExporter())
        resultado = svc.generar_notas(_dto_notas())
        assert resultado.startswith(b"EXCEL:")

    def test_genera_notas_en_pdf(self):
        svc = InformeService(FakeEstadRepo(), exporter=FakeExporter())
        dto = InformeNotasDTO(
            grupo_id=10, asignacion_id=3, periodo_id=5,
            fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 6, 30),
            formato=FormatoInforme.PDF,
        )
        resultado = svc.generar_notas(dto)
        assert resultado.startswith(b"PDF:")

    def test_genera_consolidado_anual(self):
        svc = InformeService(FakeEstadRepo(), exporter=FakeExporter())
        resultado = svc.generar_consolidado_anual(grupo_id=10, anio_id=1)
        assert resultado.startswith(b"EXCEL:")

    def test_exportar_csv(self):
        svc = InformeService(FakeEstadRepo(), exporter=FakeExporter())
        resultado = svc.exportar_csv([{"col": "val"}])
        assert resultado == b"CSV"
