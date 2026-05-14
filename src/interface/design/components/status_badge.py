"""
status_badge.py — Badges de estado del design system Andes Minimal.

Implementación: ui.html() en vez de ui.element().text() porque en
NiceGUI 3.x el método .text() no existe como builder chainable en Element.
"""
from __future__ import annotations

from nicegui import ui


def status_badge(texto: str, variante: str = "neutral") -> ui.html:
    """
    Badge genérico del design system.

    Args:
        texto:    Etiqueta visible.
        variante: Clase CSS de color. Opciones:
                  - Semánticos: success | warning | error | info | neutral
                  - Asistencia: P | FJ | FI | R | E
                  - Desempeño:  bajo | basico | alto | superior

    Returns:
        Elemento ui.html con el span del badge.
    """
    return ui.html(f'<span class="badge badge-{variante}">{texto}</span>')


def badge_asistencia(estado: str) -> ui.html:
    """
    Badge de asistencia con etiqueta en español.

    Args:
        estado: Código de asistencia — "P", "FJ", "FI", "R" o "E".

    Ejemplo:
        badge_asistencia("FJ")  →  badge amarillo "F. Just."
    """
    etiquetas: dict[str, str] = {
        "P":  "Presente",
        "FJ": "F. Just.",
        "FI": "F. Injust.",
        "R":  "Retraso",
        "E":  "Excusa",
    }
    return status_badge(etiquetas.get(estado, estado), variante=estado)


def badge_desempeno(nivel: str) -> ui.html:
    """
    Badge de nivel de desempeño académico.

    Args:
        nivel: "Bajo", "Básico", "Alto" o "Superior".

    Ejemplo:
        badge_desempeno("Superior")  →  badge verde "Superior"
    """
    # Normalizar para coincidir con las clases CSS: badge-bajo, badge-basico, etc.
    variante = (
        nivel.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    return status_badge(nivel, variante=variante)


def badge_estado_general(activo: bool) -> ui.html:
    """Badge de estado activo/inactivo para usuarios y registros."""
    if activo:
        return status_badge("Activo", variante="success")
    return status_badge("Inactivo", variante="neutral")


__all__ = ["status_badge", "badge_asistencia", "badge_desempeno", "badge_estado_general"]
