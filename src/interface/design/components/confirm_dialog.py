"""
confirm_dialog.py — Diálogo de confirmación modal del design system.

Ajuste NiceGUI 3.x:
  - Iconos via ThemeManager.icono() (ui.html) en vez de ui.element().text()
  - El patrón lambda: (dialog.close(), on_confirm()) crea una tupla en Python,
    lo que provoca que ambas expresiones se evalúen en orden. Es válido y legible.
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.interface.design.theme import ThemeManager
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_danger


def confirm_dialog(
    titulo: str,
    mensaje: str,
    on_confirm: Callable,
    variante: str = "danger",
    texto_confirmar: str = "Confirmar",
    texto_cancelar: str = "Cancelar",
) -> None:
    """
    Muestra un diálogo de confirmación modal y lo abre inmediatamente.

    Args:
        titulo:           Título del diálogo.
        mensaje:          Texto explicativo de la acción a confirmar.
        on_confirm:       Callback ejecutado si el usuario confirma.
        variante:         "danger" | "warning" | "info"
                          Controla el color del icono y el botón de confirmación.
        texto_confirmar:  Etiqueta del botón de confirmación.
        texto_cancelar:   Etiqueta del botón de cancelación.
    """
    _ICONO_MAP = {
        "danger":  "warning",
        "warning": "warning",
        "info":    "info",
    }
    _COLOR_MAP = {
        "danger":  "var(--color-error)",
        "warning": "var(--color-warning)",
        "info":    "var(--color-info)",
    }

    icono_nombre = _ICONO_MAP.get(variante, "help")
    icono_color  = _COLOR_MAP.get(variante, "var(--color-primary)")

    with ui.dialog() as dialog, ui.card().classes("andes-card confirm-dialog-card"):
        # Cabecera: icono + título
        with ui.row().classes("confirm-dialog-head items-center gap-3"):
            ThemeManager.icono(icono_nombre, size=28, color=icono_color)
            ui.label(titulo).classes("font-h3")

        # Cuerpo: mensaje
        ui.label(mensaje).classes("confirm-dialog-body")

        # Pie: botones
        with ui.row().classes("confirm-dialog-foot gap-2 justify-end"):
            btn_secondary(texto_cancelar, on_click=dialog.close)

            if variante == "danger":
                btn_danger(
                    texto_confirmar,
                    on_click=lambda: (dialog.close(), on_confirm()),
                )
            else:
                btn_primary(
                    texto_confirmar,
                    on_click=lambda: (dialog.close(), on_confirm()),
                )

    dialog.open()


__all__ = ["confirm_dialog"]
