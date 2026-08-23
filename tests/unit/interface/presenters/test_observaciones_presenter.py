"""Tests del ObservacionesPresenter."""
from __future__ import annotations

from src.interface.presenters.convivencia.observaciones_presenter import ObservacionesPresenter


def test_aplicar_seleccion_copia_y_resetea_estudiantes():
    p = ObservacionesPresenter()
    p.estado["sel_estudiante_ids"] = [1, 2]
    p.aplicar_seleccion({
        "sel_periodo_id": 3,
        "sel_grupo_id": 10,
        "sel_asignacion_id": 7,
        "sel_asignacion_nombre": "Matemáticas",
    })
    assert p.estado["sel_periodo_id"] == 3
    assert p.estado["sel_grupo_id"] == 10
    assert p.estado["sel_asignacion_id"] == 7
    assert p.estado["sel_asignacion_nombre"] == "Matemáticas"
    assert p.estado["sel_estudiante_ids"] == []
