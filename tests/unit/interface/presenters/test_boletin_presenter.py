"""Tests del BoletinPresenter (compartido por boletin_periodo/anual)."""
from __future__ import annotations

from src.interface.presenters.informes.boletin_presenter import BoletinPresenter


def test_a_int_coerciona_y_preserva_none():
    assert BoletinPresenter.a_int("5") == 5
    assert BoletinPresenter.a_int(None) is None


def test_set_grupo_coerciona():
    p = BoletinPresenter()
    p.set_grupo("7")
    assert p.estado["grupo_id"] == 7
    p.set_grupo(None)
    assert p.estado["grupo_id"] is None


def test_set_estudiantes_y_grupos():
    p = BoletinPresenter()
    p.set_estudiantes([1, 2])
    p.set_grupos([3])
    assert p.estado["estudiantes"] == [1, 2]
    assert p.estado["grupos"] == [3]
