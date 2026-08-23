"""Tests del HubInstitucionPresenter — modelo del formulario de settings."""
from __future__ import annotations

from src.interface.presenters.institucion.hub_institucion_presenter import HubInstitucionPresenter


def test_estructura_del_formulario():
    p = HubInstitucionPresenter()
    for clave in ("identidad", "preferencias", "modulos", "apariencia", "convivencia"):
        assert clave in p.estado
    assert p.estado["preferencias"]["numero_periodos_default"] == 4
    assert isinstance(p.estado["modulos"], dict)
