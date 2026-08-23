"""Tests del GruposPresenter — view-state de formularios de grupos."""
from __future__ import annotations

from src.interface.presenters.admin.grupos_presenter import GruposPresenter


def test_form_arranca_con_defaults():
    p = GruposPresenter()
    assert p.estado["form_codigo"] == ""
    assert p.estado["form_jornada"] == "UNICA"
    assert p.estado["form_capacidad"] == 40


def test_reset_create_form_restaura_defaults():
    p = GruposPresenter()
    p.estado["form_codigo"] = "6A"
    p.estado["form_capacidad"] = 25
    p.reset_create_form()
    assert p.estado["form_codigo"] == ""
    assert p.estado["form_capacidad"] == 40


def test_reset_con_grado_default_fija_el_grado():
    p = GruposPresenter()
    p.estado["form_grado"] = 9
    p.reset_create_form(grado_default=3)
    assert p.estado["form_grado"] == 3


def test_reset_no_toca_estado_de_edicion():
    p = GruposPresenter()
    p.estado["edit_id"] = 5
    p.reset_create_form()
    assert p.estado["edit_id"] == 5
