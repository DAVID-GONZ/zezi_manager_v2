"""Tests del ConfiguracionConvivenciaPresenter — computaciones de vista."""
from __future__ import annotations

from types import SimpleNamespace

from src.interface.presenters.convivencia.configuracion_convivencia_presenter import (
    ConfiguracionConvivenciaPresenter,
)


def _cat(cid, nombre, activa=True):
    return SimpleNamespace(id=cid, nombre=nombre, activa=activa)


def test_opciones_categorias_solo_activas_con_sin_categoria():
    p = ConfiguracionConvivenciaPresenter()
    p.set_categorias([_cat(1, "Académica"), _cat(2, "Inactiva", activa=False)])
    opts = p.opciones_categorias()
    assert opts[None] == "Sin categoría"
    assert opts[1] == "Académica"
    assert 2 not in opts  # inactiva excluida


def test_cat_nombre_por_id():
    p = ConfiguracionConvivenciaPresenter()
    p.set_categorias([_cat(1, "A"), _cat(2, "B", activa=False)])
    assert p.cat_nombre_por_id() == {1: "A", 2: "B"}


def test_reset_selecciones():
    p = ConfiguracionConvivenciaPresenter()
    p.estado["sel_cat"] = {"x": 1}
    p.estado["sel_plt"] = {"y": 2}
    p.reset_selecciones()
    assert p.estado["sel_cat"] is None and p.estado["sel_plt"] is None


# ---------------------------------------------------------------------------
# tipos_situacion (convivencia_34)
# ---------------------------------------------------------------------------

def _tipo(tid, nombre, activa=True, nivel=1):
    return SimpleNamespace(id=tid, nombre=nombre, activa=activa, nivel=nivel)


def test_estado_inicial_incluye_tipos_situacion():
    p = ConfiguracionConvivenciaPresenter()
    assert "tipos_situacion" in p.estado
    assert p.estado["tipos_situacion"] == []
    assert p.estado["editando_tipo"] is None
    assert p.estado["sel_tipo"] is None


def test_set_tipos_situacion(self=None):
    p = ConfiguracionConvivenciaPresenter()
    tipos = [_tipo(1, "Tipo I"), _tipo(2, "Tipo II"), _tipo(3, "Tipo III")]
    p.set_tipos_situacion(tipos)
    assert len(p.estado["tipos_situacion"]) == 3
    assert p.estado["tipos_situacion"][0].nombre == "Tipo I"


def test_reset_selecciones_limpia_sel_tipo():
    p = ConfiguracionConvivenciaPresenter()
    p.estado["sel_tipo"] = {"id": 1}
    p.reset_selecciones()
    assert p.estado["sel_tipo"] is None
