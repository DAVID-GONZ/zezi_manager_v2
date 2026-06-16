"""
Minimal import tests para el hub de horarios y la parrilla.
"""
from __future__ import annotations


def test_horarios_hub_page_importa():
    from src.interface.pages.academico.horarios_hub import horarios_hub_page
    assert callable(horarios_hub_page)


def test_parrilla_widget_importa():
    from src.interface.pages.academico.parrilla_widget import render_parrilla
    assert callable(render_parrilla)
