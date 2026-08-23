"""Tests del ConfiguracionAlertasPresenter."""
from __future__ import annotations

from src.interface.presenters.convivencia.configuracion_alertas_presenter import (
    ConfiguracionAlertasPresenter,
)


def test_set_anio_y_configs():
    p = ConfiguracionAlertasPresenter()
    p.set_anio(3, "2026")
    p.set_configs({"promedio_bajo": object()})
    assert p.estado["anio_id"] == 3
    assert p.estado["anio_nombre"] == "2026"
    assert "promedio_bajo" in p.estado["configs"]


def test_limpiar():
    p = ConfiguracionAlertasPresenter()
    p.set_anio(3, "2026")
    p.set_configs({"x": 1})
    p.limpiar()
    assert p.estado["anio_id"] is None and p.estado["configs"] == {}
