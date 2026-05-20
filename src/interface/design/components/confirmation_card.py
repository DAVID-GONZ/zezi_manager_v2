"""
confirmation_card.py — Tarjeta de confirmación inline del design system Andes Minimal.

Alternativa al diálogo modal: muestra la confirmación dentro del flujo de página,
sin interrumpir con un overlay. Útil para acciones en listas o formularios.
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.interface.design.theme import ThemeManager
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_danger


def confirmation_card(
    mensaje: str,
    on_confirm: Callable,
    on_cancelar: Callable | None = None,
    titulo: str = "¿Confirmar acción?",
    texto_confirmar: str = "Confirmar",
    texto_cancelar: str = "Cancelar",
    variante: str = "warning",
) -> ui.card:
    """
    Tarjeta de confirmación inline (no modal) del design system.

    Muestra un bloque de confirmación embebido en el contenido de la página,
    útil cuando el contexto no debe interrumpirse con un diálogo flotante.

    Args:
        mensaje:          Texto explicativo de la acción a confirmar.
        on_confirm:       Callback ejecutado al confirmar.
        on_cancelar:      Callback ejecutado al cancelar (oculta la tarjeta si None).
        titulo:           Título descriptivo de la confirmación.
        texto_confirmar:  Etiqueta del botón de confirmación.
        texto_cancelar:   Etiqueta del botón de cancelación.
        variante:         "danger" | "warning" | "info" — afecta color del icono y borde.

    Returns:
        El elemento raíz (ui.card) para poder ocultarlo con .set_visibility(False).

    Ejemplo:
        card = confirmation_card(
            mensaje="¿Eliminar al estudiante Juan García del grupo 6A?",
            on_confirm=lambda: eliminar(estudiante_id),
            variante="danger",
        )
        # Para ocultar: card.set_visibility(False)
    """
    _COLOR_MAP = {
        "danger":  ("var(--color-error)",   "var(--color-error-light)",   "warning"),
        "warning": ("var(--color-warning)", "var(--color-warning-light)", "warning"),
        "info":    ("var(--color-info)",    "var(--color-info-light)",    "info"),
    }
    icono_color, bg_color, icono_nombre = _COLOR_MAP.get(
        variante, ("var(--color-warning)", "var(--color-warning-light)", "warning")
    )

    card = ui.card().classes("andes-card").style(
        f"background:{bg_color}; border-left: 4px solid {icono_color};"
    )
    with card:
        with ui.row().classes("w-full items-start gap-3"):
            ThemeManager.icono(icono_nombre, size=24, color=icono_color)

            with ui.column().classes("confirm-card-inner gap-2"):
                ui.label(titulo).classes("font-h3").style(
                    f"color:{icono_color}"
                )
                ui.label(mensaje).classes("confirm-card-body")

                with ui.row().classes("confirm-card-actions items-center gap-2"):
                    def _cancelar():
                        if on_cancelar:
                            on_cancelar()
                        else:
                            card.set_visibility(False)

                    btn_secondary(texto_cancelar, on_click=_cancelar)

                    if variante == "danger":
                        btn_danger(texto_confirmar, on_click=on_confirm)
                    else:
                        btn_primary(texto_confirmar, on_click=on_confirm)

    return card


__all__ = ["confirmation_card"]
