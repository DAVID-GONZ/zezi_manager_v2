"""Tests del AsignaturasPresenter — filtro/búsqueda + formularios."""
from __future__ import annotations

from types import SimpleNamespace

from src.interface.presenters.admin.asignaturas_presenter import AsignaturasPresenter


def _asig(nombre, codigo=None):
    return SimpleNamespace(nombre=nombre, codigo=codigo)


class TestBusqueda:
    def test_set_busqueda_normaliza(self):
        p = AsignaturasPresenter()
        p.set_busqueda("  MaTe  ")
        assert p.estado["busqueda"] == "mate"

    def test_filtrar_sin_busqueda_devuelve_todo(self):
        p = AsignaturasPresenter()
        asigs = [_asig("Matemáticas"), _asig("Lengua")]
        assert p.filtrar(asigs) == asigs

    def test_filtrar_por_nombre(self):
        p = AsignaturasPresenter()
        p.set_busqueda("mate")
        r = p.filtrar([_asig("Matemáticas"), _asig("Lengua")])
        assert [a.nombre for a in r] == ["Matemáticas"]

    def test_filtrar_por_codigo(self):
        p = AsignaturasPresenter()
        p.set_busqueda("mat")
        r = p.filtrar([_asig("Álgebra", codigo="MAT"), _asig("Lengua", codigo="LEN")])
        assert [a.nombre for a in r] == ["Álgebra"]

    def test_filtrar_tolera_codigo_none(self):
        p = AsignaturasPresenter()
        p.set_busqueda("zzz")
        assert p.filtrar([_asig("Lengua", codigo=None)]) == []


class TestFormularios:
    def test_reset_area_form(self):
        p = AsignaturasPresenter()
        p.estado["area_nombre"] = "Ciencias"
        p.estado["area_codigo"] = "CN"
        p.reset_area_form()
        assert p.estado["area_nombre"] == "" and p.estado["area_codigo"] == ""

    def test_reset_asig_form(self):
        p = AsignaturasPresenter()
        p.estado["asig_nombre"] = "Física"
        p.estado["asig_area_id"] = 3
        p.reset_asig_form()
        assert p.estado["asig_nombre"] == "" and p.estado["asig_area_id"] is None

    def test_set_area_filtro(self):
        p = AsignaturasPresenter()
        p.set_area_filtro(5)
        assert p.estado["area_filtro_id"] == 5
