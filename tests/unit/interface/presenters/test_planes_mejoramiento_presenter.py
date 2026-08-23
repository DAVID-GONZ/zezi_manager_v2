"""Tests del PlanesMejoramientoPresenter."""
from __future__ import annotations

from types import SimpleNamespace

from src.interface.presenters.evaluacion.planes_mejoramiento_presenter import (
    PlanesMejoramientoPresenter,
)


def test_grupo_de_asignacion():
    p = PlanesMejoramientoPresenter()
    p.estado["asignaciones"] = [
        SimpleNamespace(asignacion_id=1, grupo_id=10),
        SimpleNamespace(asignacion_id=2, grupo_id=20),
    ]
    assert p.grupo_de_asignacion(2) == 20
    assert p.grupo_de_asignacion(99) is None


def test_reset_actividad_form():
    p = PlanesMejoramientoPresenter()
    p.estado["form_act_nombre"] = "Taller"
    p.estado["form_act_peso"] = 0.5
    p.reset_actividad_form()
    assert p.estado["form_act_nombre"] == ""
    assert p.estado["form_act_peso"] == 0.20
