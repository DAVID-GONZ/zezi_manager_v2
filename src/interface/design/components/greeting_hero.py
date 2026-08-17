"""
greeting_hero.py — Hero de saludo con nombre, rol y mensaje descriptivo.

Componente de presentación puro: recibe datos como strings,
no llama servicios ni Container.
"""
from __future__ import annotations

from datetime import datetime

from nicegui import ui

from src.interface.design.theme import ThemeManager
from src.interface.design.styles.tokens import Icons


def _saludo_temporal() -> str:
    """Decide 'Buenos días / Buenas tardes / Buenas noches' según la hora."""
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Buenos días"
    elif 12 <= hora < 20:
        return "Buenas tardes"
    return "Buenas noches"


def greeting_hero(
    nombre: str,
    rol: str,
    mensaje: str,
    *,
    nombre_completo: str | None = None,
    rol_label: str | None = None,
    animacion: bool = True,
) -> None:
    """Hero de saludo del dashboard.

    Args:
        nombre:          Nombre corto (primer nombre) para el saludo.
        rol:             Rol del usuario (clave interna, ej: 'profesor').
        mensaje:         Descripción debajo del saludo.
        nombre_completo: Nombre completo para la cápsula de metadata.
        rol_label:       Etiqueta legible del rol (ej: 'Docente').
        animacion:       Si True, añade clase .greeting-hero-animated con fade-up.
    """
    clases = "greeting-hero w-full"
    if animacion:
        clases += " greeting-hero-animated"

    with ui.element("div").classes(clases):
        ui.label(f"{_saludo_temporal()}, {nombre}").classes("greeting-name")
        ui.label(mensaje).classes("greeting-desc")
        with ui.element("div").classes("greeting-meta"):
            ThemeManager.icono(Icons.PROFILE, size=16, color="var(--color-primary)")
            ui.label(nombre_completo or nombre).classes("greeting-user")
            ui.element("span").classes("greeting-dot")
            ui.label(
                rol_label or rol.capitalize()
            ).classes("greeting-role")


__all__ = ["greeting_hero", "_saludo_temporal"]
