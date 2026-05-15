"""
base_form.py — Formulario base reutilizable del design system Andes Minimal.
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui


def base_form(
    campos: list[dict],
    on_submit: Callable,
    titulo: str = "",
    texto_submit: str = "Guardar",
    texto_cancelar: str = "",
    on_cancelar: Callable | None = None,
    columnas: int = 1,
) -> ui.card:
    """
    Formulario base reutilizable con layout estándar del design system.

    Args:
        campos:          Lista de dicts con configuración de cada campo:
                         {
                             "key":         str,           # Identificador del campo
                             "label":       str,           # Etiqueta visible
                             "tipo":        str,           # "text" | "password" | "select" | "textarea"
                             "opciones":    list | None,   # Solo para tipo "select"
                             "placeholder": str,           # Texto de ayuda opcional
                             "requerido":   bool,          # Marca campo obligatorio
                             "ref":         list,          # Lista de 1 elemento para recibir el widget
                         }
        on_submit:       Callback con firma fn(datos: dict) al enviar el formulario.
        titulo:          Título opcional mostrado sobre el formulario.
        texto_submit:    Etiqueta del botón de envío.
        texto_cancelar:  Etiqueta del botón de cancelación (si se provee on_cancelar).
        on_cancelar:     Callback sin argumentos ejecutado al cancelar.
        columnas:        Número de columnas para el grid de campos (1 o 2).

    Returns:
        El elemento raíz (ui.card) para encadenamiento.

    Ejemplo:
        widgets = []
        base_form(
            campos=[
                {"key": "nombre", "label": "Nombre completo", "tipo": "text",
                 "requerido": True, "ref": []},
                {"key": "rol", "label": "Rol", "tipo": "select",
                 "opciones": ["profesor", "admin"], "ref": []},
            ],
            on_submit=lambda datos: print(datos),
            titulo="Nuevo usuario",
        )
    """
    _valores: dict[str, ui.input | ui.select | ui.textarea] = {}

    def _recoger_datos() -> dict:
        return {k: w.value for k, w in _valores.items()}

    card = ui.card().classes("andes-card").style(
        "width:100%;"
        "padding:var(--space-lg);"
        "background:var(--color-surface);"
    )
    with card:
        if titulo:
            ui.label(titulo).classes("font-h3").style(
                "color:var(--color-text-primary);"
                "margin-bottom:var(--space-md);"
            )
            ui.separator().style("margin-bottom:var(--space-md);background:var(--color-divider);")

        col_style = (
            "display:grid;"
            f"grid-template-columns:repeat({columnas},1fr);"
            "gap:var(--space-md);"
            "width:100%;"
        )
        with ui.element("div").style(col_style):
            for campo in campos:
                key         = campo.get("key", "")
                label       = campo.get("label", key)
                tipo        = campo.get("tipo", "text")
                opciones    = campo.get("opciones", [])
                placeholder = campo.get("placeholder", "")
                requerido   = campo.get("requerido", False)
                ref         = campo.get("ref", None)

                label_text = f"{label} *" if requerido else label

                with ui.column().classes("gap-1").style("width:100%;"):
                    if tipo == "select":
                        widget = ui.select(
                            options=opciones,
                            label=label_text,
                        ).classes("andes-input").style("width:100%;")
                    elif tipo == "textarea":
                        widget = ui.textarea(
                            label=label_text,
                            placeholder=placeholder,
                        ).classes("andes-input").style("width:100%;")
                    elif tipo == "password":
                        widget = ui.input(
                            label=label_text,
                            placeholder=placeholder,
                            password=True,
                            password_toggle_button=True,
                        ).classes("andes-input").style("width:100%;")
                    else:
                        widget = ui.input(
                            label=label_text,
                            placeholder=placeholder,
                        ).classes("andes-input").style("width:100%;")

                    _valores[key] = widget
                    if isinstance(ref, list):
                        ref.append(widget)

        ui.separator().style("margin:var(--space-md) 0;background:var(--color-divider);")

        with ui.row().classes("gap-2 justify-end").style("width:100%;"):
            if on_cancelar and texto_cancelar:
                ui.button(
                    texto_cancelar,
                    on_click=on_cancelar,
                ).classes("btn-secondary")

            ui.button(
                texto_submit,
                on_click=lambda: on_submit(_recoger_datos()),
            ).classes("btn-primary")

    return card


__all__ = ["base_form"]
