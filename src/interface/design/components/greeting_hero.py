"""
greeting_hero.py — Hero de bienvenida animado y transitorio.

Entra desde arriba con stagger en sus hijos, muestra una barra de cuenta
regresiva y desaparece ~4 s después colapsando el espacio que ocupaba,
de modo que el contenido inferior asciende suavemente sin salto.

Componente de presentación puro: recibe strings, no llama servicios.

Los colores vienen de variables --greeting-hero-* definidas en el bloque
GREETING HERO de cards.css. Claro: fondo índigo visible con texto oscuro
(ink-900/700). Oscuro: fondo índigo profundo con texto claro (paper-000).
Los iconos usan --greeting-hero-icon-color que cambia con el tema.
"""

from __future__ import annotations

from datetime import datetime

from nicegui import ui

from src.interface.design.styles.tokens import Icons
from src.interface.design.theme import ThemeManager


def _saludo_temporal() -> str:
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Buenos días"
    if 12 <= hora < 20:
        return "Buenas tardes"
    return "Buenas noches"


def _icono_temporal() -> str:
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "wb_sunny"
    if 12 <= hora < 19:
        return "partly_cloudy_day"
    return "bedtime"


def greeting_hero(
    nombre: str,
    rol: str,
    mensaje: str,
    *,
    nombre_completo: str | None = None,
    rol_label: str | None = None,
    animacion: bool = True,
) -> None:
    """Hero de bienvenida con entrada animada y auto-dismiss.

    Args:
        nombre:          Primer nombre del usuario (para el saludo).
        rol:             Clave interna del rol ('profesor', 'director'…).
        mensaje:         Texto descriptivo debajo del nombre.
        nombre_completo: Nombre completo mostrado en el badge de identidad.
        rol_label:       Etiqueta legible del rol ('Docente', 'Director'…).
        animacion:       False desactiva todas las animaciones (tests/a11y).
    """
    saludo = _saludo_temporal()
    icono = _icono_temporal()
    etiqueta = rol_label or rol.replace("_", " ").capitalize()
    display_nombre = nombre_completo or nombre

    clases = "greeting-hero"
    if animacion:
        clases += " greeting-hero--animated"

    with ui.element("div").classes(clases):
        # ── Contenido ─────────────────────────────────────────────────
        with ui.element("div").classes("greeting-hero-inner"):
            # Columna izquierda: saludo + nombre + mensaje
            with ui.element("div").classes("greeting-hero-left"):
                with ui.element("div").classes("greeting-time-row"):
                    with ui.element("div").classes("greeting-time-icon"):
                        ThemeManager.icono(icono, size=20, color="var(--greeting-hero-icon-color)")
                    ui.label(saludo).classes("greeting-saludo")
                ui.label(display_nombre).classes("greeting-name")
                ui.label(mensaje).classes("greeting-desc")

            # Columna derecha: badge de rol
            with ui.element("div").classes("greeting-hero-right"):
                with ui.element("div").classes("greeting-badge"):
                    ThemeManager.icono(
                        Icons.PROFILE,
                        size=16,
                        color="var(--greeting-hero-icon-color)",
                    )
                    ui.label(etiqueta).classes("greeting-role")

        # ── Barra de cuenta regresiva ──────────────────────────────────
        with ui.element("div").classes("greeting-progress-track"):
            ui.element("div").classes("greeting-progress-bar")


__all__ = ["greeting_hero"]
