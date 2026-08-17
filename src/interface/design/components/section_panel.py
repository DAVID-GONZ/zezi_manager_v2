"""
section_panel.py — Panel con encabezado estándar (icono + título).

Componente de presentación puro: no llama servicios ni Container.
Usa las clases .panel-card, .panel-header y .panel-title del CSS core.
"""
from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from nicegui import ui

from src.interface.design.theme import ThemeManager


@contextmanager
def section_panel(
    titulo: str,
    icono: str,
    *,
    color: str = "var(--color-primary)",
) -> Iterator[ui.element]:
    """Context manager: envuelve contenido con .panel-card + .panel-header + .panel-title.

    Args:
        titulo: Texto del encabezado del panel.
        icono:  Nombre del Material Symbol Rounded.
        color:  Color CSS del icono (token semántico preferido).

    Yields:
        El elemento raíz del panel (.panel-card) para encadenar estilos si es necesario.

    Ejemplo::

        with section_panel("Actividad reciente", "history") as panel:
            ui.label("Contenido del panel")
    """
    with ui.element("div").classes("panel-card") as el:
        with ui.element("div").classes("panel-header"):
            ThemeManager.icono(icono, size=20, color=color)
            ui.label(titulo).classes("panel-title")
        yield el


__all__ = ["section_panel"]
