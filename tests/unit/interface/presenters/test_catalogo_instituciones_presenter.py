"""Tests del CatalogoInstitucionesPresenter."""
from __future__ import annotations

from src.interface.presenters.admin.catalogo_instituciones_presenter import (
    CatalogoInstitucionesPresenter,
)


def test_set_instituciones():
    p = CatalogoInstitucionesPresenter()
    p.set_instituciones([1, 2, 3])
    assert p.estado["instituciones"] == [1, 2, 3]
