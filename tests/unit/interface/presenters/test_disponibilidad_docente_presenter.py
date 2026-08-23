"""Tests del DisponibilidadDocentePresenter."""
from __future__ import annotations

from src.interface.presenters.admin.disponibilidad_docente_presenter import (
    DisponibilidadDocentePresenter,
)


def test_toggle_slot_por_defecto_disponible():
    p = DisponibilidadDocentePresenter()
    clave = ("lunes", 1)
    p.toggle_slot(clave)          # por defecto True → pasa a False
    assert p.estado["disponibilidad"][clave] is False
    p.toggle_slot(clave)          # vuelve a True
    assert p.estado["disponibilidad"][clave] is True


def test_set_docente():
    p = DisponibilidadDocentePresenter()
    p.set_docente(7)
    assert p.estado["docente_id"] == 7
