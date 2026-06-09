"""
empty_state.py — Estado vacío reutilizable del design system.

Uso:
    from src.interface.design.components import empty_state

    empty_state(
        titulo="No hay grupos registrados",
        descripcion="Crea el primer grupo para comenzar a organizar estudiantes.",
        cta_label="+ Crear grupo",
        cta_on_click=lambda: dialog.open(),
        cta_icono="add",
    )
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from ..theme import ThemeManager
from .buttons import btn_primary, btn_ghost

_VARIANTE_ICONO_COLOR: dict[str, str] = {
    "default": "var(--color-text-secondary)",
    "search":  "var(--color-text-secondary)",
    "error":   "var(--color-error)",
}


def empty_state(
    *,
    icono: str = "inbox",
    titulo: str,
    descripcion: str = "",
    cta_label: str | None = None,
    cta_on_click: Callable | None = None,
    cta_icono: str | None = None,
    variante: str = "default",
) -> None:
    """
    Renderiza un estado vacío centrado con icono, título, descripción opcional
    y CTA opcional.

    Args:
        icono:         Material Symbol para el área de icono (64px).
        titulo:        Texto principal del estado vacío.
        descripcion:   Texto secundario explicativo (opcional).
        cta_label:     Etiqueta del botón de acción (opcional).
        cta_on_click:  Callback del botón (requerido si cta_label está presente).
        cta_icono:     Icono del botón CTA (opcional).
        variante:      "default" | "search" | "error". Controla el color del icono.
    """
    color_icono = _VARIANTE_ICONO_COLOR.get(variante, _VARIANTE_ICONO_COLOR["default"])

    with ui.column().classes(f"empty-state empty-state--{variante}"):
        with ui.element("div").classes("empty-state__icon-wrap"):
            ThemeManager.icono(icono, size=48, color=color_icono)
        ui.label(titulo).classes("empty-state__title")
        if descripcion:
            ui.label(descripcion).classes("empty-state__description")
        if cta_label and cta_on_click:
            btn_fn = btn_ghost if variante == "error" else btn_primary
            btn_fn(cta_label, on_click=cta_on_click, icono=cta_icono)
