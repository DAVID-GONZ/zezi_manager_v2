"""
base_form.py — Formulario base reutilizable del design system Andes Minimal.

Estilo Formik: etiqueta estática sobre cada campo, inputs compactos,
sin label flotante de Quasar.
"""
from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from src.interface.design.components.buttons import btn_primary, btn_secondary


def _label_above(label: str, requerido: bool, tooltip_txt: str = "") -> None:
    """Renderiza la etiqueta estática sobre un campo (Formik-style)."""
    with ui.row().classes("form-field-label-row"):
        ui.label(label).classes("form-field-label")
        if requerido:
            ui.html('<span class="form-field-req">*</span>')
        if tooltip_txt:
            ui.html(
                f'<span class="material-symbols-rounded form-field-tooltip-icon" '
                f'title="{tooltip_txt}">help</span>'
            )


def base_form(
    campos: list[dict],
    on_submit: Callable,
    titulo: str = "",
    texto_submit: str = "Guardar",
    texto_cancelar: str = "",
    on_cancelar: Callable | None = None,
    columnas: int = 1,
    _submit_btn_ref: list | None = None,
) -> ui.element:
    """
    Formulario base reutilizable del design system.

    Atributos de campo (dict):
        key        str   — clave en el dict de datos que recibe on_submit.
        label      str   — etiqueta del campo.
        tipo       str   — text | password | email | number | select | textarea |
                           checkbox | switch | time | date | color | readonly | section.
        valor      any   — valor inicial.
        placeholder str  — placeholder (campos de texto). Usa label si omitido.
        requerido  bool  — muestra asterisco (*) en la etiqueta.
        opciones   list  — opciones para tipo='select'.
        hint       str   — texto auxiliar bajo el campo.
        disabled   bool  — deshabilita la interacción.
        span       bool  — ocupa todo el ancho del grid (ignora columnas).
        tooltip    str   — tooltip al hacer hover (ícono de ayuda junto a la etiqueta).
        ref        list  — se le hace append del widget creado (para acceso externo).
        icono      str   — material symbol (solo tipo='section').
        min/max/step/format — solo tipo='number'.
    """
    _valores: dict[str, ui.input | ui.select | ui.textarea | ui.number | ui.checkbox] = {}

    def _recoger_datos() -> dict:
        return {k: w.value for k, w in _valores.items()}

    contenedor = ui.element("div").classes("base-form-wrapper")

    with contenedor:
        if titulo:
            ui.label(titulo).classes("font-h3 base-form-title")
            ui.separator().classes("base-form-sep u-mb-md")

        with ui.element("div").classes(f"base-form-grid base-form-grid-{columnas}col"):
            for campo in campos:
                key         = campo.get("key", "")
                label       = campo.get("label", key)
                tipo        = campo.get("tipo", "text")
                opciones    = campo.get("opciones", [])
                placeholder = campo.get("placeholder", "") or label
                requerido   = campo.get("requerido", False)
                ref         = campo.get("ref", None)
                hint        = campo.get("hint", "")
                disabled    = campo.get("disabled", False)
                span        = campo.get("span", False)
                tooltip_txt = campo.get("tooltip", "")
                label_text  = f"{label} *" if requerido else label

                # ── Sección visual — divider con título ─────────────────
                if tipo == "section":
                    with ui.element("div").classes("form-section-header"):
                        icono_section = campo.get("icono")
                        if icono_section:
                            ui.html(
                                f'<span class="material-symbols-rounded" '
                                f'style="font-size:14px;opacity:.7;">'
                                f'{icono_section}</span>'
                            )
                        ui.label(label)
                    continue

                span_cls = "base-form-field-span" if span else ""

                with ui.element("div").classes(f"base-form-field-col {span_cls}"):

                    # ── Select ──────────────────────────────────────────
                    if tipo == "select":
                        _label_above(label, requerido, tooltip_txt)
                        widget = ui.select(
                            options=opciones,
                            value=campo.get("valor"),
                        ).classes("andes-input w-full").props("borderless dense")
                        if placeholder and placeholder != label:
                            widget.props(f'placeholder="{placeholder}"')
                        if disabled:
                            widget.props("disable")

                    # ── Textarea ─────────────────────────────────────────
                    elif tipo == "textarea":
                        _label_above(label, requerido, tooltip_txt)
                        widget = ui.textarea(
                            placeholder=placeholder,
                            value=campo.get("valor", ""),
                        ).classes("andes-input andes-textarea w-full").props("borderless")
                        if disabled:
                            widget.props("disable")

                    # ── Password ─────────────────────────────────────────
                    elif tipo == "password":
                        _label_above(label, requerido, tooltip_txt)
                        widget = ui.input(
                            placeholder=placeholder,
                            value=campo.get("valor", ""),
                            password=True,
                            password_toggle_button=True,
                        ).classes("andes-input w-full").props("borderless dense")
                        if disabled:
                            widget.props("disable")

                    # ── Number ───────────────────────────────────────────
                    elif tipo == "number":
                        _label_above(label, requerido, tooltip_txt)
                        min_val  = campo.get("min")
                        max_val  = campo.get("max")
                        step_val = campo.get("step")
                        fmt_val  = campo.get("format")
                        kwargs: dict = {"value": campo.get("valor"), "placeholder": placeholder}
                        if min_val  is not None: kwargs["min"]    = min_val
                        if max_val  is not None: kwargs["max"]    = max_val
                        if step_val is not None: kwargs["step"]   = step_val
                        if fmt_val  is not None: kwargs["format"] = fmt_val
                        widget = ui.number(**kwargs).classes("andes-input w-full").props("borderless dense")
                        if disabled:
                            widget.props("disable")

                    # ── Checkbox (label inline, sin etiqueta superior) ───
                    elif tipo == "checkbox":
                        widget = ui.checkbox(label_text, value=bool(campo.get("valor", False)))
                        if disabled:
                            widget.props("disable")

                    # ── Switch (label inline) ─────────────────────────────
                    elif tipo == "switch":
                        widget = ui.switch(label_text, value=bool(campo.get("valor", False)))
                        if disabled:
                            widget.props("disable")

                    # ── Time ─────────────────────────────────────────────
                    elif tipo == "time":
                        _label_above(label, requerido, tooltip_txt)
                        widget = (
                            ui.input(value=campo.get("valor", ""))
                            .props("type=time borderless dense")
                            .classes("andes-input w-full")
                        )
                        if disabled:
                            widget.props("disable")

                    # ── Date ─────────────────────────────────────────────
                    elif tipo == "date":
                        _label_above(label, requerido, tooltip_txt)
                        widget = (
                            ui.input(value=campo.get("valor", ""))
                            .props("type=date borderless dense")
                            .classes("andes-input w-full")
                        )
                        if disabled:
                            widget.props("disable")

                    # ── Email ─────────────────────────────────────────────
                    elif tipo == "email":
                        _label_above(label, requerido, tooltip_txt)
                        widget = (
                            ui.input(
                                placeholder=placeholder,
                                value=campo.get("valor", ""),
                            )
                            .props("type=email borderless dense")
                            .classes("andes-input w-full")
                        )
                        if disabled:
                            widget.props("disable")

                    # ── Color ─────────────────────────────────────────────
                    elif tipo == "color":
                        _label_above(label, requerido, tooltip_txt)
                        widget = (
                            ui.color_input(
                                value=campo.get("valor", ""),
                            )
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        if disabled:
                            widget.props("disable")

                    # ── Readonly ──────────────────────────────────────────
                    elif tipo == "readonly":
                        ui.label(label).classes("base-form-readonly-label text-xs")
                        ui.label(str(campo.get("valor", ""))).classes(
                            "readonly-field-value text-sm"
                        )
                        if hint:
                            ui.label(hint).classes("form-field-hint")
                        continue

                    # ── Text (default) ───────────────────────────────────
                    else:
                        _label_above(label, requerido, tooltip_txt)
                        widget = ui.input(
                            placeholder=placeholder,
                            value=campo.get("valor", ""),
                        ).classes("andes-input w-full").props("borderless dense")
                        if disabled:
                            widget.props("disable")

                    # tooltip ya está en el label; también en el widget para accesibilidad
                    if tooltip_txt and tipo in ("checkbox", "switch"):
                        widget.tooltip(tooltip_txt)

                    _valores[key] = widget
                    if isinstance(ref, list):
                        ref.append(widget)

                    if hint:
                        ui.label(hint).classes("form-field-hint")

        ui.separator().classes("base-form-sep u-mt-lg u-mb-sm")

        with ui.row().classes("base-form-footer w-full gap-2 justify-end"):
            if on_cancelar and texto_cancelar:
                btn_secondary(texto_cancelar, on_click=on_cancelar)

            _btn = btn_primary(
                texto_submit,
                on_click=lambda: on_submit(_recoger_datos()),
            )
            if _submit_btn_ref is not None:
                _submit_btn_ref.append(_btn)

    return contenedor


__all__ = ["base_form"]
