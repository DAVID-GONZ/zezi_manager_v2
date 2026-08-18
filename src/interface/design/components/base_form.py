"""
base_form.py — Formulario base reutilizable del design system Andes Minimal.

Estilo Formik: etiqueta estática sobre cada campo, inputs compactos,
sin label flotante de Quasar.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from src.interface.design.components.buttons import btn_primary, btn_secondary
from src.interface.design.components.toast import toast_warning


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
        minlength  int   — longitud mínima de texto (validada al enviar).
        maxlength  int   — longitud máxima de texto (prop HTML en el input).
        normalizar str   — "titulo" | "minusculas" | "mayusculas" — case aplicado al recoger datos.
        opciones_desde str — key del campo padre cuyo valor determina las opciones de este select.
        opciones_fn Callable — f(valor_padre) → list[str]; genera opciones dinámicas.
        min/max/step/format — solo tipo='number'.
    """
    _valores: dict[str, ui.input | ui.select | ui.textarea | ui.number | ui.checkbox] = {}
    _requeridos: dict[str, str] = {}
    _normalizacion: dict[str, str] = {}
    _minlengths: dict[str, tuple[str, int]] = {}
    _cascadas: list[tuple[str, str, object]] = []

    def _recoger_datos() -> dict:
        datos: dict = {}
        for k, w in _valores.items():
            val = w.value
            if isinstance(val, str):
                val = val.strip()
                modo = _normalizacion.get(k)
                if modo == "titulo":
                    val = val.title()
                elif modo == "minusculas":
                    val = val.lower()
                elif modo == "mayusculas":
                    val = val.upper()
            datos[k] = val
        return datos

    def _validar_campos() -> bool:
        vacios: list[str] = []
        for key, label in _requeridos.items():
            widget = _valores.get(key)
            if widget is None:
                continue
            val = widget.value
            if val is None or (isinstance(val, str) and not val.strip()):
                vacios.append(label)
        if vacios:
            toast_warning(f"Completa los campos obligatorios: {', '.join(vacios)}")
            return False

        for key, (label, minlen) in _minlengths.items():
            widget = _valores.get(key)
            if widget is None:
                continue
            val = widget.value
            if isinstance(val, str) and len(val.strip()) < minlen:
                toast_warning(f"{label} debe tener al menos {minlen} caracteres")
                return False

        return True

    contenedor = ui.element("div").classes("base-form-wrapper")

    with contenedor:
        if titulo:
            ui.label(titulo).classes("font-h3 base-form-title")
            ui.separator().classes("base-form-sep u-mb-md")

        with ui.element("div").classes(f"base-form-grid base-form-grid-{columnas}col"):
            for campo in campos:
                key = campo.get("key", "")
                label = campo.get("label", key)
                tipo = campo.get("tipo", "text")
                opciones = campo.get("opciones", [])
                placeholder = campo.get("placeholder", "") or label
                requerido = campo.get("requerido", False)
                ref = campo.get("ref", None)
                hint = campo.get("hint", "")
                disabled = campo.get("disabled", False)
                span = campo.get("span", False)
                tooltip_txt = campo.get("tooltip", "")
                display_label = label.removesuffix(" *") if requerido else label
                label_text = f"{display_label} *" if requerido else label
                minlength_v = campo.get("minlength")
                maxlength_v = campo.get("maxlength")
                normalizar_v = campo.get("normalizar")
                opciones_desde_v = campo.get("opciones_desde")
                opciones_fn_v = campo.get("opciones_fn")

                if requerido and key:
                    _requeridos[key] = display_label
                if normalizar_v and key:
                    _normalizacion[key] = normalizar_v
                if minlength_v is not None and key:
                    _minlengths[key] = (display_label, minlength_v)
                if opciones_desde_v and opciones_fn_v and key:
                    _cascadas.append((opciones_desde_v, key, opciones_fn_v))

                # ── Sección visual — divider con título ─────────────────
                if tipo == "section":
                    with ui.element("div").classes("form-section-header"):
                        icono_section = campo.get("icono")
                        if icono_section:
                            ui.html(
                                f'<span class="material-symbols-rounded" '
                                f'style="font-size:14px;opacity:.7;">'
                                f"{icono_section}</span>"
                            )
                        ui.label(label)
                    continue

                span_cls = "base-form-field-span" if span else ""

                with ui.element("div").classes(f"base-form-field-col {span_cls}"):
                    # ── Select ──────────────────────────────────────────
                    if tipo == "select":
                        _label_above(display_label, requerido, tooltip_txt)
                        widget = (
                            ui.select(
                                options=opciones,
                                value=campo.get("valor"),
                            )
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        if placeholder and placeholder != label:
                            widget.props(f'placeholder="{placeholder}"')
                        if disabled:
                            widget.props("disable")

                    # ── Textarea ─────────────────────────────────────────
                    elif tipo == "textarea":
                        _label_above(display_label, requerido, tooltip_txt)
                        widget = (
                            ui.textarea(
                                placeholder=placeholder,
                                value=campo.get("valor", ""),
                            )
                            .classes("andes-input andes-textarea w-full")
                            .props("borderless")
                        )
                        if disabled:
                            widget.props("disable")

                    # ── Password ─────────────────────────────────────────
                    elif tipo == "password":
                        _label_above(display_label, requerido, tooltip_txt)
                        widget = (
                            ui.input(
                                placeholder=placeholder,
                                value=campo.get("valor", ""),
                                password=True,
                                password_toggle_button=True,
                            )
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        if disabled:
                            widget.props("disable")

                    # ── Number ───────────────────────────────────────────
                    elif tipo == "number":
                        _label_above(display_label, requerido, tooltip_txt)
                        min_val = campo.get("min")
                        max_val = campo.get("max")
                        step_val = campo.get("step")
                        fmt_val = campo.get("format")
                        kwargs: dict = {"value": campo.get("valor"), "placeholder": placeholder}
                        if min_val is not None:
                            kwargs["min"] = min_val
                        if max_val is not None:
                            kwargs["max"] = max_val
                        if step_val is not None:
                            kwargs["step"] = step_val
                        if fmt_val is not None:
                            kwargs["format"] = fmt_val
                        widget = (
                            ui.number(**kwargs)
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
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
                        _label_above(display_label, requerido, tooltip_txt)
                        widget = (
                            ui.input(value=campo.get("valor", ""))
                            .props("type=time borderless dense")
                            .classes("andes-input w-full")
                        )
                        if disabled:
                            widget.props("disable")

                    # ── Date ─────────────────────────────────────────────
                    elif tipo == "date":
                        _label_above(display_label, requerido, tooltip_txt)
                        widget = (
                            ui.input(value=campo.get("valor", ""))
                            .props("type=date borderless dense")
                            .classes("andes-input w-full")
                        )
                        if disabled:
                            widget.props("disable")

                    # ── Email ─────────────────────────────────────────────
                    elif tipo == "email":
                        _label_above(display_label, requerido, tooltip_txt)
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
                        _label_above(display_label, requerido, tooltip_txt)
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
                        _label_above(display_label, requerido, tooltip_txt)
                        widget = (
                            ui.input(
                                placeholder=placeholder,
                                value=campo.get("valor", ""),
                            )
                            .classes("andes-input w-full")
                            .props("borderless dense")
                        )
                        if disabled:
                            widget.props("disable")

                    # tooltip ya está en el label; también en el widget para accesibilidad
                    if tooltip_txt and tipo in ("checkbox", "switch"):
                        widget.tooltip(tooltip_txt)

                    _valores[key] = widget
                    if maxlength_v is not None and hasattr(widget, "props"):
                        widget.props(f"maxlength={maxlength_v}")
                    if isinstance(ref, list):
                        ref.append(widget)

                    if hint:
                        ui.label(hint).classes("form-field-hint")

        for padre_key, hijo_key, fn in _cascadas:
            padre = _valores.get(padre_key)
            hijo = _valores.get(hijo_key)
            if padre is not None and hijo is not None and isinstance(hijo, ui.select):

                def _hacer_handler(_h: ui.select, _fn: object):
                    def _handler(e) -> None:
                        _h.options = _fn(e.value) if e.value else []
                        _h.value = None
                        _h.update()

                    return _handler

                padre.on_value_change(_hacer_handler(hijo, fn))

        ui.separator().classes("base-form-sep u-mt-lg u-mb-sm")

        with ui.row().classes("base-form-footer w-full gap-2 justify-end"):
            if on_cancelar and texto_cancelar:
                btn_secondary(texto_cancelar, on_click=on_cancelar)

            def _on_click_submit() -> None:
                if _validar_campos():
                    on_submit(_recoger_datos())

            _btn = btn_primary(
                texto_submit,
                on_click=_on_click_submit,
            )
            if _submit_btn_ref is not None:
                _submit_btn_ref.append(_btn)

    return contenedor


__all__ = ["base_form"]
