"""Tests del ReportePeriodoPresenter."""
from __future__ import annotations

from src.interface.presenters.convivencia.reporte_periodo_presenter import ReportePeriodoPresenter


def test_aplicar_seleccion():
    p = ReportePeriodoPresenter()
    p.aplicar_seleccion({
        "sel_grupo_id": 3, "sel_periodo_id": 1,
        "sel_grupo_nombre": "6A", "sel_periodo_nombre": "P1",
    })
    assert p.estado["grupo_id"] == 3
    assert p.estado["periodo_id"] == 1
    assert p.estado["sel_grupo_nombre"] == "6A"
