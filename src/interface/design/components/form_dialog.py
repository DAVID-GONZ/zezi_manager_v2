"""
form_dialog.py — Modal de formulario CRUD del design system Andes Minimal.
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.interface.design.components.base_form import base_form


def form_dialog(
    titulo: str,
    campos: list[dict],
    on_submit: Callable[[dict], "bool | None"],
    texto_submit: str = "Guardar",
    on_cancelar: Callable | None = None,
    max_width: str = "max-w-md",
    columnas: int = 1,
) -> None:
    """
    Abre un diálogo modal con un formulario estandarizado del design system.

    Args:
        titulo:        Título del diálogo.
        campos:        Lista de dicts de campo; ver base_form() para schema.
        on_submit:     Callback(datos: dict) -> bool | None.
                       Retornar False mantiene el dialog abierto (error de validación).
                       Retornar None o True lo cierra automáticamente (éxito).
        texto_submit:  Etiqueta del botón de confirmación.
        on_cancelar:   Callback adicional al cancelar (opcional).
        max_width:     Clase CSS de ancho máximo del card (ej: "max-w-md", "max-w-lg").
        columnas:      Número de columnas del grid de campos.
    """
    with ui.dialog() as dlg, ui.card().classes(f"andes-card form-dialog-card {max_width}"):
        ui.label(titulo).classes("font-h3 form-dialog-title")

        def _cancelar() -> None:
            if on_cancelar:
                on_cancelar()
            dlg.close()

        def _submit(datos: dict) -> None:
            result = on_submit(datos)
            if result is not False:
                dlg.close()

        base_form(
            campos=campos,
            on_submit=_submit,
            texto_submit=texto_submit,
            texto_cancelar="Cancelar",
            on_cancelar=_cancelar,
            columnas=columnas,
        )

    dlg.open()


__all__ = ["form_dialog"]
