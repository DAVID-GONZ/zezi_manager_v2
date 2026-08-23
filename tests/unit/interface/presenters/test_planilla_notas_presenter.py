"""Tests del PlanillaNotasPresenter."""
from __future__ import annotations

from src.interface.presenters.evaluacion.planilla_notas_presenter import PlanillaNotasPresenter


def test_set_modo_y_toggle_puntos():
    p = PlanillaNotasPresenter()
    p.set_modo("actividades")
    assert p.estado["modo"] == "actividades"
    assert p.estado["mostrar_puntos"] is False
    p.toggle_puntos()
    assert p.estado["mostrar_puntos"] is True


def test_aplicar_seleccion():
    p = PlanillaNotasPresenter()
    p.aplicar_seleccion({"sel_asignacion_id": 7, "sel_periodo_id": 1, "sel_grupo_id": 3})
    assert p.estado["asignacion_id"] == 7
    assert p.estado["grupo_id"] == 3


def test_resets_de_formularios():
    p = PlanillaNotasPresenter()
    p.estado["act_nombre"] = "Quiz"
    p.estado["form_cat_nombre"] = "Ser"
    p.reset_act_form()
    p.reset_cat_form()
    assert p.estado["act_nombre"] == "" and p.estado["act_valor_max"] == 100.0
    assert p.estado["form_cat_nombre"] == "" and p.estado["form_cat_peso"] == 10
