"""Tests del CierrePeriodoPresenter."""
from __future__ import annotations

from src.interface.presenters.evaluacion.cierre_periodo_presenter import CierrePeriodoPresenter


def test_setters():
    p = CierrePeriodoPresenter()
    p.set_periodo(2)
    p.set_grupo(10)
    p.set_asignaciones([1, 2])
    assert p.estado["periodo_id"] == 2
    assert p.estado["grupo_id"] == 10
    assert p.estado["asignaciones"] == [1, 2]
