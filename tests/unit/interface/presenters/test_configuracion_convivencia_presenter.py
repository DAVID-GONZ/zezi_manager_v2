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
