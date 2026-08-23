"""Tests del EstudiantesPresenter — filtros + predicado hay_filtro_activo."""
from __future__ import annotations

from src.interface.presenters.academico.estudiantes_presenter import EstudiantesPresenter


class TestHayFiltroActivo:
    def test_arranca_inactivo(self):
        assert EstudiantesPresenter().hay_filtro_activo() is False

    def test_tocar_un_filtro_lo_activa(self):
        p = EstudiantesPresenter()
        p.set_grupo(None)  # "Todos los grupos" también cuenta como interacción
        assert p.hay_filtro_activo() is True

    def test_busqueda_no_vacia_lo_activa(self):
        p = EstudiantesPresenter()
        p.estado["filtro_busqueda"] = "  ana  "
        # incluso sin marcar filtro_tocado, una búsqueda con texto lo activa
        p.estado["filtro_tocado"] = False
        assert p.hay_filtro_activo() is True

    def test_busqueda_solo_espacios_no_activa(self):
        p = EstudiantesPresenter()
        p.estado["filtro_busqueda"] = "   "
        p.estado["filtro_tocado"] = False
        assert p.hay_filtro_activo() is False


class TestTransiciones:
    def test_cada_filtro_marca_tocado(self):
        for setter, args in [("set_grupo", (3,)), ("set_estado", ("activo",)), ("set_busqueda", ("x",))]:
            p = EstudiantesPresenter()
            getattr(p, setter)(*args)
            assert p.estado["filtro_tocado"] is True

    def test_piar_normaliza_a_true_o_none(self):
        p = EstudiantesPresenter()
        p.set_piar(True)
        assert p.estado["filtro_piar"] is True
        p.set_piar(False)
        assert p.estado["filtro_piar"] is None

    def test_set_estudiantes(self):
        p = EstudiantesPresenter()
        p.set_estudiantes([1, 2])
        assert p.estado["estudiantes"] == [1, 2]
