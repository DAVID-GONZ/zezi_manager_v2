"""Tests del HabilitacionesPresenter."""
from __future__ import annotations

from src.interface.presenters.evaluacion.habilitaciones_presenter import HabilitacionesPresenter


def test_setters_de_seleccion():
    p = HabilitacionesPresenter()
    p.set_nivel_periodo(2)
    p.set_nivel_asig(5)
    assert p.estado["nivel_periodo_id"] == 2
    assert p.estado["nivel_asig_id"] == 5
