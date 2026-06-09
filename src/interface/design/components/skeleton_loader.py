"""
skeleton_loader.py — Placeholders de carga con animación shimmer (paso_12b).

Uso:
    from src.interface.design.components import skeleton_table, skeleton_cards, skeleton_form

    # Mientras carga una tabla:
    skeleton_table(rows=10, cols=6)

    # Mientras cargan tarjetas KPI:
    skeleton_cards(count=4)

    # Mientras carga un formulario:
    skeleton_form(fields=5)
"""
from __future__ import annotations

from nicegui import ui


def skeleton_table(rows: int = 8, cols: int = 5) -> None:
    """
    Renderiza un placeholder para una tabla mientras se carga el contenido.

    Args:
        rows: Número de filas de esqueleto.
        cols: Número de columnas de esqueleto.
    """
    with ui.column().classes("skeleton-table"):
        # Cabecera
        with ui.row().classes("skeleton-row skeleton-row--header"):
            for _ in range(cols):
                ui.element("div").classes("skeleton-bar skeleton-bar--header")
        # Filas de cuerpo
        for _ in range(rows):
            with ui.row().classes("skeleton-row"):
                for _ in range(cols):
                    ui.element("div").classes("skeleton-bar")


def skeleton_cards(count: int = 4) -> None:
    """
    Renderiza placeholders de tarjetas KPI/estadísticas.

    Args:
        count: Número de tarjetas de esqueleto.
    """
    with ui.row().classes("skeleton-cards"):
        for _ in range(count):
            with ui.column().classes("skeleton-card"):
                ui.element("div").classes("skeleton-bar skeleton-bar--lg")
                ui.element("div").classes("skeleton-bar skeleton-bar--sm")
                ui.element("div").classes("skeleton-bar skeleton-bar--xs")


def skeleton_form(fields: int = 6) -> None:
    """
    Renderiza un placeholder para un formulario mientras carga.

    Args:
        fields: Número de campos de esqueleto a mostrar.
    """
    with ui.column().classes("skeleton-form"):
        for _ in range(fields):
            with ui.column().classes("skeleton-form-field"):
                ui.element("div").classes("skeleton-bar skeleton-bar--label")
                ui.element("div").classes("skeleton-bar skeleton-bar--input")
