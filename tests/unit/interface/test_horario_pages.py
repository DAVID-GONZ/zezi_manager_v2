"""
Minimal import tests para las páginas de generación y la parrilla.
"""
from __future__ import annotations


def test_horario_generar_page_importa():
    from src.interface.pages.academico.horario_generar import horario_generar_page
    assert callable(horario_generar_page)


def test_parrilla_widget_importa():
    from src.interface.pages.academico.parrilla_widget import render_parrilla
    assert callable(render_parrilla)
