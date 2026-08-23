"""Tests del PlanEstudiosPresenter."""
from __future__ import annotations

from src.interface.presenters.admin.plan_estudios_presenter import PlanEstudiosPresenter


def test_seleccionar_grado_resetea_vinc():
    p = PlanEstudiosPresenter()
    p.estado["vinc_asig_id"] = 9
    p.set_grado_sel(6)
    assert p.estado["grado_sel"] == 6
    assert p.estado["vinc_asig_id"] is None


def test_reset_grado_form():
    p = PlanEstudiosPresenter()
    p.estado["g_numero"] = 7
    p.estado["g_nombre"] = "Séptimo"
    p.reset_grado_form()
    assert p.estado["g_numero"] is None and p.estado["g_nombre"] == ""


def test_limpiar_vinc():
    p = PlanEstudiosPresenter()
    p.estado["vinc_asig_id"] = 3
    p.limpiar_vinc()
    assert p.estado["vinc_asig_id"] is None
