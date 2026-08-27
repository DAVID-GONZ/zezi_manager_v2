"""Tests del SeguimientoPresenter."""
from __future__ import annotations

from src.interface.presenters.convivencia.seguimiento_presenter import SeguimientoPresenter


def test_seleccionar_estudiante_vuelve_a_evolucion():
    p = SeguimientoPresenter()
    p.set_seccion("alertas")
    p.estado["resultado_360"] = {"x": 1}
    p.seleccionar_estudiante(5)
    assert p.estado["sel_estudiante_id"] == 5
    assert p.estado["sel_seccion"] == "evolucion"
    assert p.estado["resultado_360"] is None


def test_aplicar_seleccion_resetea_detalle():
    p = SeguimientoPresenter()
    p.estado["sel_estudiante_id"] = 9
    p.estado["observaciones_est"] = [1]
    p.aplicar_seleccion({"sel_periodo_id": 1, "sel_grupo_id": 2, "sel_grupo_nombre": "6A"})
    assert p.estado["sel_grupo_id"] == 2
    assert p.estado["sel_estudiante_id"] is None
    assert p.estado["observaciones_est"] == []


# convivencia_35: estado de entradas_seguimiento
def test_estado_inicial_incluye_entradas_seguimiento():
    p = SeguimientoPresenter()
    assert "entradas_seguimiento" in p.estado
    assert p.estado["entradas_seguimiento"] == []
    assert p.estado["sel_registro_id"] is None


def test_set_entradas_seguimiento():
    from types import SimpleNamespace
    p = SeguimientoPresenter()
    entradas = [SimpleNamespace(texto="A"), SimpleNamespace(texto="B")]
    p.set_entradas_seguimiento(entradas)
    assert len(p.estado["entradas_seguimiento"]) == 2


def test_reset_detalle_limpia_entradas_seguimiento():
    p = SeguimientoPresenter()
    p.estado["entradas_seguimiento"] = [1, 2, 3]
    p.estado["sel_registro_id"] = 7
    p.aplicar_seleccion({"sel_periodo_id": 1, "sel_grupo_id": 2, "sel_grupo_nombre": "6A"})
    assert p.estado["entradas_seguimiento"] == []
    assert p.estado["sel_registro_id"] is None
