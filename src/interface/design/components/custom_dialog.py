"""
custom_dialog.py — Diálogo modal con card estilizada del design system.

Cuándo usar cada componente:
  - `confirm_dialog`   → confirmar una acción (Sí/No).
  - `form_dialog`      → formulario CRUD con campos primitivos definidos por dict.
  - `custom_dialog`    → diálogos con contenido custom (no encaja en form_dialog):
                         listas, wizards, tablas, previews, formularios multi-sección.

Uso (context manager que te posiciona dentro de la card ya estilizada):

    from src.interface.design.components import custom_dialog

    with custom_dialog(max_width="md") as dlg:
        ui.label("Traslado de estudiante").classes("font-h3 form-dialog-title")
        # ... contenido custom ...
        with ui.row().classes("form-dialog-actions"):
            btn_ghost("Cancelar", on_click=dlg.close)
            btn_primary("Confirmar", on_click=lambda: (_ejecutar(), dlg.close()))
    dlg.open()

Reemplaza el patrón prohibido `with ui.dialog() as dlg, ui.card().classes(
"andes-card form-dialog-card max-w-md"):` en páginas.
"""
from __future__ import annotations

import contextlib
from collections.abc import Iterator
from typing import Literal

from nicegui import ui

_MAX_WIDTHS: dict[str, str] = {
    "sm": "form-dialog-card-sm",
    "md": "form-dialog-card-md",
    "lg": "form-dialog-card-lg",
    "xl": "form-dialog-card-xl",
}


@contextlib.contextmanager
def custom_dialog(
    max_width: Literal["sm", "md", "lg", "xl"] = "md",
    persistent: bool = False,
) -> Iterator[ui.dialog]:
    """
    Context manager que crea un `ui.dialog` con una card estilizada del design
    system. Al entrar al `with`, el flujo de NiceGUI queda posicionado dentro
    de la card — cualquier `ui.label(...)`, `ui.row(...)`, etc. se añade allí.

    Args:
        max_width:   Ancho máximo del card: sm | md | lg | xl.
        persistent:  Si True, no se cierra al hacer click fuera.

    Yields:
        El `ui.dialog` para poder llamar `dlg.open()` / `dlg.close()` desde el
        cuerpo del `with` o desde handlers externos.
    """
    dlg = ui.dialog()
    if persistent:
        dlg.props("persistent")

    ancho_cls = _MAX_WIDTHS.get(max_width, _MAX_WIDTHS["md"])
    with dlg:
        with ui.card().classes(f"andes-card form-dialog-card {ancho_cls}"):
            yield dlg


__all__ = ["custom_dialog"]
