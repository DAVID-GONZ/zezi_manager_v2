"""Tests del TableroEstadisticosPresenter."""
from __future__ import annotations

from src.interface.presenters.academico.tablero_estadisticos_presenter import (
    TableroEstadisticosPresenter,
)


def test_aplicar_seleccion_resetea_drill():
    p = TableroEstadisticosPresenter()
    p.estado["drill_grupo_id"] = 5
    p.estado["drill_asig_id"] = 7
    p.aplicar_seleccion({"sel_periodo_id": 1, "sel_grupo_id": 2, "sel_asignacion_id": 3})
    assert p.estado["periodo_id"] == 1
    assert p.estado["drill_grupo_id"] is None and p.estado["drill_asig_id"] is None


def test_set_drill_grupo_resetea_asig():
    p = TableroEstadisticosPresenter()
    p.set_drill_asig(9)
    p.set_drill_grupo(4)
    assert p.estado["drill_grupo_id"] == 4
    assert p.estado["drill_asig_id"] is None
