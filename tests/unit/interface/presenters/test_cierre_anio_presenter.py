"""Tests del CierreAnioPresenter."""
from __future__ import annotations

from types import SimpleNamespace

from src.interface.presenters.evaluacion.cierre_anio_presenter import CierreAnioPresenter


def test_grupo_nombre():
    p = CierreAnioPresenter()
    assert p.grupo_nombre() == ""
    p.set_grupos([SimpleNamespace(id=1, codigo="6A")])
    p.set_grupo(1)
    assert p.grupo_nombre() == "6A"
    p.set_grupo(99)
    assert p.grupo_nombre() == "99"
