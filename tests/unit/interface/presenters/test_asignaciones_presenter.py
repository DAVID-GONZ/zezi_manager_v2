"""Tests del AsignacionesPresenter — view-state de /admin/asignaciones."""
from __future__ import annotations

from src.interface.presenters.admin.asignaciones_presenter import AsignacionesPresenter


class TestTransiciones:
    def test_setters_actualizan_estado(self):
        p = AsignacionesPresenter()
        p.set_periodo(3)
        p.set_grupo_sel(10)
        p.set_docente_sel(7)
        p.set_perspectiva("docente")
        p.set_solo_con_cupo(False)
        assert p.estado["periodo_id"] == 3
        assert p.estado["grupo_sel_id"] == 10
        assert p.estado["docente_sel_id"] == 7
        assert p.estado["perspectiva"] == "docente"
        assert p.estado["solo_con_cupo"] is False


class TestLoaderObjetivo:
    def test_profesor_siempre_su_tablero(self):
        p = AsignacionesPresenter()
        assert p.loader_objetivo(es_profesor=True) == "profesor"
        p.set_perspectiva("docente")
        assert p.loader_objetivo(es_profesor=True) == "profesor"

    def test_directivo_segun_perspectiva(self):
        p = AsignacionesPresenter()  # perspectiva "grupo" por defecto
        assert p.loader_objetivo(es_profesor=False) == "grupo"
        p.set_perspectiva("docente")
        assert p.loader_objetivo(es_profesor=False) == "docente"
