"""Tests del SalasPresenter — view-state del formulario de salas."""
from __future__ import annotations

from src.interface.presenters.admin.salas_presenter import SalasPresenter


def test_form_arranca_con_defaults():
    p = SalasPresenter()
    assert p.estado["nombre"] == ""
    assert p.estado["tipo"] == "aula"
    assert p.estado["capacidad"] == 30


def test_reset_form_restaura_defaults():
    p = SalasPresenter()
    p.estado["nombre"] = "Lab 3"
    p.estado["tipo"] = "laboratorio"
    p.estado["capacidad"] = 12
    p.reset_form()
    assert p.estado["nombre"] == ""
    assert p.estado["tipo"] == "aula"
    assert p.estado["capacidad"] == 30


def test_reset_no_toca_listas_cargadas():
    p = SalasPresenter()
    p.set_salas([1, 2])
    p.set_grupos([3])
    p.reset_form()
    assert p.estado["salas"] == [1, 2]
    assert p.estado["grupos"] == [3]
