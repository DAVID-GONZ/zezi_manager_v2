"""
confirmation_card.py — Tarjeta de confirmación inline del design system Andes Minimal.

Alternativa al diálogo modal: muestra la confirmación dentro del flujo de página,
sin interrumpir con un overlay. Útil para acciones en listas o formularios.
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.interface.design.theme import ThemeManager


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
        "danger":  ("var(--color-error)",   "#FFEBEE", "warning"),
        "warning": ("var(--color-warning)", "#FFF3E0", "warning"),
        "info":    ("var(--color-info)",    "#E1F5FE", "info"),
    }
    icono_color, bg_color, icono_nombre = _COLOR_MAP.get(
        variante, ("var(--color-warning)", "#FFF3E0", "warning")
    )
    btn_class = "btn-danger" if variante == "danger" else "btn-primary"

    card = ui.card().classes("andes-card").style(
        f"background:{bg_color};"
        f"border-left:4px solid {icono_color};"
        "padding:var(--space-md);"
        "width:100%;"
    )
    with card:
        with ui.row().classes("items-start gap-3").style("width:100%;"):
            ThemeManager.icono(icono_nombre, size=24, color=icono_color)

            with ui.column().classes("gap-2").style("flex:1;"):
                ui.label(titulo).classes("font-h3").style(
                    f"color:{icono_color};"
                )
                ui.label(mensaje).style(
                    "color:var(--color-text-primary);"
                    "font-size:var(--font-size-body);"
                    "line-height:1.5;"
                )

                with ui.row().classes("gap-2 items-center").style("margin-top:var(--space-sm)"):
                    def _cancelar():
                        if on_cancelar:
                            on_cancelar()
                        else:
                            card.set_visibility(False)

                    ui.button(
                        texto_cancelar,
                        on_click=_cancelar,
                    ).classes("btn-secondary")

                    ui.button(
                        texto_confirmar,
                        on_click=on_confirm,
                    ).classes(btn_class)

    return card


__all__ = ["confirmation_card"]
