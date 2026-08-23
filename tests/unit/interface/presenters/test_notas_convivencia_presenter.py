"""Tests del NotasConvivenciaPresenter."""
from __future__ import annotations

from src.interface.presenters.convivencia.notas_convivencia_presenter import (
    NotasConvivenciaPresenter,
)


def test_aplicar_seleccion_resetea_detalle():
    p = NotasConvivenciaPresenter()
    p.estado["sel_estudiante_id"] = 5
    p.estado["cambios_pendientes"] = {5: {"valor": 3}}
    p.estado["observaciones_estudiante"] = [1]
    p.aplicar_seleccion({
        "sel_periodo_id": 1,
        "sel_grupo_id": 2,
        "sel_asignacion_id": 3,
    })
    assert p.estado["sel_periodo_id"] == 1
    assert p.estado["sel_estudiante_id"] is None
    assert p.estado["cambios_pendientes"] == {}
    assert p.estado["observaciones_estudiante"] == []
    assert p.estado["sel_asignacion_nombre"] == ""
