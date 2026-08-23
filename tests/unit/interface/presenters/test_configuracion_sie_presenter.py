"""Tests del ConfiguracionSiePresenter."""
from __future__ import annotations

from types import SimpleNamespace

from src.interface.presenters.admin.configuracion_sie_presenter import ConfiguracionSiePresenter


def test_anio_id():
    p = ConfiguracionSiePresenter()
    assert p.anio_id() is None
    p.estado["config_activa"] = SimpleNamespace(id=7)
    assert p.anio_id() == 7


def test_modo_actual_default_libre():
    p = ConfiguracionSiePresenter()
    assert p.modo_actual() == "libre"
    p.estado["siee_cfg"] = SimpleNamespace(modo=SimpleNamespace(value="mixto_autonomia"))
    assert p.modo_actual() == "mixto_autonomia"
