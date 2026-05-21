"""
base_form.py — Formulario base reutilizable del design system Andes Minimal.
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.interface.design.components.buttons import btn_primary, btn_secondary


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
                                                           # | "number" | "checkbox" | "time" | "email"
                                                           # | "readonly"
                             "valor":       Any,           # Valor inicial (para modo edición)
                             "opciones":    list | None,   # Solo para tipo "select"
                             "placeholder": str,           # Texto de ayuda opcional
                             "requerido":   bool,          # Marca campo obligatorio
                             "ref":         list,          # Lista de 1 elemento para recibir el widget
                             # Sólo para tipo="number":
                             "min":    int | float,
                             "max":    int | float,
                             "step":   int | float,
                             "format": str,                # ej: "%.2f"
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

    card = ui.card().classes("andes-card base-form-card")
    with card:
        if titulo:
            ui.label(titulo).classes("font-h3 base-form-title")
            ui.separator().classes("base-form-sep")

        with ui.element("div").classes("base-form-grid").style(
            f"grid-template-columns: repeat({columnas}, 1fr);"
        ):
            for campo in campos:
                key         = campo.get("key", "")
                label       = campo.get("label", key)
                tipo        = campo.get("tipo", "text")
                opciones    = campo.get("opciones", [])
                placeholder = campo.get("placeholder", "")
                requerido   = campo.get("requerido", False)
                ref         = campo.get("ref", None)

                label_text = f"{label} *" if requerido else label

                with ui.column().classes("gap-1 w-full"):
                    if tipo == "select":
                        widget = ui.select(
                            options=opciones,
                            label=label_text,
                            value=campo.get("valor"),
                        ).classes("andes-input w-full")
                    elif tipo == "textarea":
                        widget = ui.textarea(
                            label=label_text,
                            placeholder=placeholder,
                            value=campo.get("valor", ""),
                        ).classes("andes-input w-full")
                    elif tipo == "password":
                        widget = ui.input(
                            label=label_text,
                            placeholder=placeholder,
                            value=campo.get("valor", ""),
                            password=True,
                            password_toggle_button=True,
                        ).classes("andes-input w-full")
                    elif tipo == "number":
                        min_val  = campo.get("min")
                        max_val  = campo.get("max")
                        step_val = campo.get("step")
                        fmt_val  = campo.get("format")
                        kwargs: dict = {"label": label_text, "value": campo.get("valor")}
                        if min_val  is not None: kwargs["min"]    = min_val
                        if max_val  is not None: kwargs["max"]    = max_val
                        if step_val is not None: kwargs["step"]   = step_val
                        if fmt_val  is not None: kwargs["format"] = fmt_val
                        widget = ui.number(**kwargs).classes("andes-input w-full")
                    elif tipo == "checkbox":
                        widget = ui.checkbox(label_text, value=bool(campo.get("valor", False)))
                    elif tipo == "time":
                        widget = (
                            ui.input(label=label_text, value=campo.get("valor", ""))
                            .props("type=time")
                            .classes("andes-input w-full")
                        )
                    elif tipo == "email":
                        widget = (
                            ui.input(
                                label=label_text,
                                placeholder=placeholder,
                                value=campo.get("valor", ""),
                            )
                            .props("type=email")
                            .classes("andes-input w-full")
                        )
                    elif tipo == "readonly":
                        ui.label(str(campo.get("valor", ""))).classes(
                            "readonly-field-value text-sm"
                        )
                        continue  # No añadir a _valores
                    else:
                        # default: text
                        widget = ui.input(
                            label=label_text,
                            placeholder=placeholder,
                            value=campo.get("valor", ""),
                        ).classes("andes-input w-full")

                    _valores[key] = widget
                    if isinstance(ref, list):
                        ref.append(widget)

        ui.separator().classes("base-form-sep")

        with ui.row().classes("base-form-footer gap-2 justify-end"):
            if on_cancelar and texto_cancelar:
                btn_secondary(texto_cancelar, on_click=on_cancelar)

            btn_primary(
                texto_submit,
                on_click=lambda: on_submit(_recoger_datos()),
            )

    return card


__all__ = ["base_form"]
