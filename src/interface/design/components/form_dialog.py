"""
form_dialog.py — Modal de formulario CRUD del design system Andes Minimal.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from nicegui import ui

from src.interface.design.components.base_form import base_form
from src.interface.design.theme import ThemeManager

_VARIANT_ICON: dict[str, str] = {
    "danger": "warning",
    "warning": "report",
    "info": "info",
    "success": "check_circle",
}

_TAMAÑO_CLS: dict[str, str] = {
    "sm": "form-dialog-card-sm",
    "md": "form-dialog-card-md",
    "lg": "form-dialog-card-lg",
    "xl": "form-dialog-card-xl",
}

# Backwards compat: Tailwind max-width classes → DS size classes
_MAX_WIDTH_MAP: dict[str, str] = {
    "max-w-sm": "form-dialog-card-sm",
    "max-w-md": "form-dialog-card-md",
    "max-w-lg": "form-dialog-card-lg",
    "max-w-xl": "form-dialog-card-xl",
    "max-w-2xl": "form-dialog-card-xl",
}


def form_dialog(
    titulo: str,
    campos: list[dict],
    on_submit: Callable[[dict], bool | None],
    texto_submit: str = "Guardar",
    on_cancelar: Callable | None = None,
    max_width: str = "max-w-md",
    columnas: int = 1,
    icono: str | None = None,
    subtitulo: str = "",
    variante: Literal["default", "danger", "warning", "info", "success"] = "default",
    texto_cancelar: str = "Cancelar",
    tamaño: Literal["sm", "md", "lg", "xl"] | None = None,
) -> None:
    """
    Abre un diálogo modal con un formulario estandarizado del design system.

    Args:
        titulo:        Título del diálogo.
        campos:        Lista de dicts de campo; ver base_form() para el schema completo.
        on_submit:     Callback(datos: dict) -> bool | None.
                       Retornar False mantiene el dialog abierto (error de validación).
                       Retornar None o True lo cierra (éxito).
        texto_submit:  Etiqueta del botón de confirmación.
        on_cancelar:   Callback adicional al cancelar (opcional).
        max_width:     Clase Tailwind de ancho máximo (backwards compat).
                       Preferir `tamaño` para nuevos usos.
        columnas:      Número de columnas del grid de campos.
        icono:         Material Symbol para el header (ej: "edit", "person_add").
                       Si es None y variante != "default", se usa el icono de la variante.
        subtitulo:     Descripción breve bajo el título.
        variante:      Acento de color del header: default | danger | warning | info | success.
        texto_cancelar: Etiqueta del botón Cancelar.
        tamaño:        sm | md | lg | xl — sobrescribe max_width si se especifica.
    """
    ancho_cls = _TAMAÑO_CLS.get(tamaño or "", "") or _MAX_WIDTH_MAP.get(
        max_width, "form-dialog-card-md"
    )
    variant_cls = f" variant-{variante}" if variante != "default" else ""
    _submit_btn_ref: list = []

    with (
        ui.dialog() as dlg,
        ui.card().classes(f"andes-card form-dialog-card {ancho_cls}{variant_cls}"),
    ):

        def _cancelar() -> None:
            if on_cancelar:
                on_cancelar()
            dlg.close()

        def _submit(datos: dict) -> None:
            if _submit_btn_ref:
                _submit_btn_ref[0].props("loading disable")
            result = on_submit(datos)
            if result is not False:
                dlg.close()
            else:
                if _submit_btn_ref:
                    _submit_btn_ref[0].props(remove="loading disable")

        # ── Header ─────────────────────────────────────────────────────────
        with ui.element("div").classes("form-dialog-header"):
            with ui.row().classes("form-dialog-header-row items-center w-full"):
                _icono = icono if icono is not None else _VARIANT_ICON.get(variante)
                if _icono:
                    with ui.element("div").classes("form-dialog-icon"):
                        ThemeManager.icono(_icono, size=16)

                with ui.element("div").classes("form-dialog-title-block"):
                    ui.label(titulo).classes("form-dialog-title")
                    if subtitulo:
                        ui.label(subtitulo).classes("form-dialog-subtitle")

                close_el = ui.element("button").classes("form-dialog-close-btn")
                close_el.on("click", _cancelar)
                with close_el:
                    ui.html(
                        '<span class="material-symbols-rounded" '
                        'style="font-size:16px;line-height:1;">close</span>'
                    )

        # ── Body (scrollable) ───────────────────────────────────────────────
        with ui.element("div").classes("form-dialog-body"):
            base_form(
                campos=campos,
                on_submit=_submit,
                texto_submit=texto_submit,
                texto_cancelar=texto_cancelar,
                on_cancelar=_cancelar,
                columnas=columnas,
                _submit_btn_ref=_submit_btn_ref,
            )

    dlg.open()


__all__ = ["form_dialog"]
