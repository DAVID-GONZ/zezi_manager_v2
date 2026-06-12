"""
base_form.py — Formulario base reutilizable del design system Andes Minimal.
"""
from __future__ import annotations

from typing import Callable, Union

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
) -> ui.element:
    
    _valores: dict[str, Union[ui.input, ui.select, ui.textarea, ui.number, ui.checkbox]] = {}

    def _recoger_datos() -> dict:
        return {k: w.value for k, w in _valores.items()}

    # Se sustituye ui.card() por un contenedor neutro para evitar 
    # la duplicación de sombras y paddings al inyectarse en un dialog.
    contenedor = ui.element("div").classes("base-form-wrapper w-full")
    
    with contenedor:
        if titulo:
            ui.label(titulo).classes("font-h3 base-form-title")
            ui.separator().classes("base-form-sep q-mb-md")

        with ui.element("div").classes("base-form-grid").style(
            f"grid-template-columns: repeat({columnas}, 1fr); display: grid; gap: 16px;"
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
                        ).classes("andes-input w-full").props("outlined")
                        
                    elif tipo == "textarea":
                        widget = ui.textarea(
                            label=label_text,
                            placeholder=placeholder,
                            value=campo.get("valor", ""),
                        ).classes("andes-input w-full").props("outlined")
                        
                    elif tipo == "password":
                        widget = ui.input(
                            label=label_text,
                            placeholder=placeholder,
                            value=campo.get("valor", ""),
                            password=True,
                            password_toggle_button=True,
                        ).classes("andes-input w-full").props("outlined")
                        
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
                        widget = ui.number(**kwargs).classes("andes-input w-full").props("outlined")
                        
                    elif tipo == "checkbox":
                        widget = ui.checkbox(label_text, value=bool(campo.get("valor", False)))
                        
                    elif tipo == "time":
                        widget = (
                            ui.input(label=label_text, value=campo.get("valor", ""))
                            .props("type=time outlined")
                            .classes("andes-input w-full")
                        )
                        
                    elif tipo == "email":
                        widget = (
                            ui.input(
                                label=label_text,
                                placeholder=placeholder,
                                value=campo.get("valor", ""),
                            )
                            .props("type=email outlined")
                            .classes("andes-input w-full")
                        )
                        
                    elif tipo == "color":
                        widget = (
                            ui.color_input(
                                label=label_text,
                                value=campo.get("valor", ""),
                            )
                            .classes("andes-input w-full")
                            .props("outlined")
                        )

                    elif tipo == "readonly":
                        # Se añade la etiqueta descriptiva para no perder contexto
                        ui.label(label_text).classes("text-xs text-grey-6 q-mb-none")
                        ui.label(str(campo.get("valor", ""))).classes(
                            "readonly-field-value text-sm"
                        )
                        continue  
                        
                    else:
                        # default: text
                        widget = ui.input(
                            label=label_text,
                            placeholder=placeholder,
                            value=campo.get("valor", ""),
                        ).classes("andes-input w-full").props("outlined")

                    _valores[key] = widget
                    if isinstance(ref, list):
                        ref.append(widget)

        ui.separator().classes("base-form-sep q-mt-lg q-mb-sm")

        with ui.row().classes("base-form-footer w-full gap-2 justify-end"):
            if on_cancelar and texto_cancelar:
                btn_secondary(texto_cancelar, on_click=on_cancelar)

            btn_primary(
                texto_submit,
                on_click=lambda: on_submit(_recoger_datos()),
            )

    return contenedor

__all__ = ["base_form"]