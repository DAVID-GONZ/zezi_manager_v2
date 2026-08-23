"""Tests del HorariosHubPresenter."""
from __future__ import annotations

from src.interface.presenters.academico.horarios_hub_presenter import HorariosHubPresenter


def test_estado_inicial_parametrizado():
    p = HorariosHubPresenter("generar", "Martes")
    assert p.estado["seccion"] == "generar"
    assert p.estado["doc_dia_sel"] == "Martes"
    assert p.estado["parrilla_modo"] == "Por entidad"


def test_transiciones_de_navegacion():
    p = HorariosHubPresenter("visualizar", None)
    p.set_seccion("generar")
    p.set_parrilla_modo("Tablero maestro")
    p.set_parrilla_perspectiva("Docente")
    p.set_gen_tab("resultado")
    assert p.estado["seccion"] == "generar"
    assert p.estado["parrilla_modo"] == "Tablero maestro"
    assert p.estado["parrilla_perspectiva"] == "Docente"
    assert p.estado["gen_tab"] == "resultado"
