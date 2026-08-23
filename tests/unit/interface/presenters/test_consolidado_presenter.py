"""Tests del ConsolidadoInformePresenter (compartido por consolidado_notas/asistencia)."""
from __future__ import annotations

from datetime import date

from src.interface.presenters.informes.consolidado_presenter import ConsolidadoInformePresenter


class TestCascada:
    def test_cambiar_grupo_resetea_asignacion_y_periodo(self):
        p = ConsolidadoInformePresenter()
        p.set_asignacion(7)
        p.set_periodo(2)
        p.set_grupo(10)
        assert p.estado["grupo_id"] == 10
        assert p.estado["asignacion_id"] is None
        assert p.estado["periodo_id"] is None


class TestFechas:
    def test_iso_valida(self):
        p = ConsolidadoInformePresenter()
        p.set_fecha_desde("2026-03-01")
        assert p.estado["fecha_desde"] == date(2026, 3, 1)

    def test_vacia_limpia(self):
        p = ConsolidadoInformePresenter()
        p.set_fecha_desde("2026-03-01")
        p.set_fecha_desde("")
        assert p.estado["fecha_desde"] is None

    def test_invalida_conserva_valor_previo(self):
        p = ConsolidadoInformePresenter()
        p.set_fecha_hasta("2026-03-31")
        p.set_fecha_hasta("no-es-fecha")
        assert p.estado["fecha_hasta"] == date(2026, 3, 31)


class TestFiltrosCompletos:
    def test_incompleto_hasta_tener_todo(self):
        p = ConsolidadoInformePresenter()
        assert p.filtros_completos() is False
        p.set_grupo(1)
        p.set_asignacion(2)
        p.set_periodo(3)
        assert p.filtros_completos() is False  # faltan fechas
        p.set_fecha_desde("2026-01-01")
        p.set_fecha_hasta("2026-01-31")
        assert p.filtros_completos() is True
