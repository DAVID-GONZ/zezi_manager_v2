"""Tests del UsuariosPresenter — view-state de filtros de usuarios."""
from __future__ import annotations

from src.interface.presenters.admin.usuarios_presenter import UsuariosPresenter


def test_estado_inicial():
    p = UsuariosPresenter()
    assert p.estado["filtro_rol"] is None
    assert p.estado["filtro_activos"] is True
    assert p.estado["filtro_institucion"] is None
    assert p.estado["usuarios"] == []


def test_transiciones_de_filtro():
    p = UsuariosPresenter()
    p.set_filtro_rol("profesor")
    p.set_filtro_activos(False)
    p.set_filtro_institucion(2)
    assert p.estado["filtro_rol"] == "profesor"
    assert p.estado["filtro_activos"] is False
    assert p.estado["filtro_institucion"] == 2


def test_set_usuarios():
    p = UsuariosPresenter()
    p.set_usuarios([1, 2, 3])
    assert p.estado["usuarios"] == [1, 2, 3]
