"""
form_fields.py — Primitivos atómicos de campos estilo Formik/TanStack.

Reutilizables fuera de `base_form` (filtros, toolbars, inline en tablas,
formularios ad-hoc). Todos aplican la clase `andes-input` y props
`borderless dense` — el mismo contrato visual del design system.

Regla de contenido:
    * `label` = etiqueta semántica ARRIBA del campo (siempre que aporte).
    * `placeholder` = EJEMPLO literal de contenido válido — no se usa como
      sustituto del label. Ej: label="Código" + placeholder="601".

Layout:
    Cuando hay `label`, el helper envuelve label+widget en un contenedor
    `.form-field-wrap` (flex column). Así, aunque el llamador coloque el
    campo dentro de un `ui.row()` horizontal, el label sigue quedando
    ARRIBA del widget — nunca a su lado. `cls_extra` se aplica al
    wrapper (para anchos tipo `w-48`); el widget interno usa `w-full`.

API pública:
    label_above(label, requerido, tooltip)          — etiqueta Formik-style
    field_input(label, ...)   -> ui.input           — text con label arriba
    field_password(label, ...) -> ui.input          — password con label
    field_email(label, ...)   -> ui.input           — email con label
    field_number(label, ...)  -> ui.number          — number con label
    field_select(label, options, ...) -> ui.select  — select con label
    field_textarea(label, ...) -> ui.textarea       — textarea con label
    field_date(label, ...)    -> ui.input           — date con label
    field_time(label, ...)    -> ui.input           — time con label
    filter_input(label, ...) -> ui.input            — filtro toolbar (label opcional)
    filter_select(label, options, ...) -> ui.select — filtro toolbar (label opcional)
    filter_number(label, ...) -> ui.number          — filtro toolbar (label opcional)
    inline_input/select/number(...)                 — celdas de tabla (sin label)
    field_hint(texto)                               — hint auxiliar bajo un campo
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager, nullcontext
from typing import Any

from nicegui import ui

_BASE_CLS = "andes-input w-full"
_BASE_PROPS = "borderless dense"


def label_above(label: str, requerido: bool = False, tooltip: str = "") -> None:
    """Renderiza la etiqueta estática sobre un campo (Formik-style)."""
    with ui.row().classes("form-field-label-row"):
        ui.label(label).classes("form-field-label")
        if requerido:
            ui.html('<span class="form-field-req">*</span>')
        if tooltip:
            ui.html(
                f'<span class="material-symbols-rounded form-field-tooltip-icon" '
                f'title="{tooltip}">help</span>'
            )


def field_hint(texto: str) -> None:
    """Texto auxiliar bajo un campo."""
    if texto:
        ui.label(texto).classes("form-field-hint")


@contextmanager
def _wrap(label: str, cls_extra: str):
    """Envuelve label+widget en un contenedor flex-column cuando hay label.

    Sin label, el `cls_extra` se aplica al widget directamente (retornando
    un nullcontext y dejando la clase al llamador via `_apply`).
    """
    if label:
        cls = f"form-field-wrap {cls_extra}".strip()
        wrap = ui.element("div").classes(cls)
        with wrap:
            yield True  # wrapper activo → cls_extra ya se aplicó al wrapper
    else:
        with nullcontext():
            yield False  # sin wrapper → cls_extra debe ir al widget


def _apply(
    widget: Any,
    cls_extra: str,
    props_extra: str,
    disabled: bool,
    wrapped: bool = False,
) -> Any:
    # Si ya envolvimos, no repetimos cls_extra en el widget (solo w-full).
    cls = _BASE_CLS if wrapped else f"{_BASE_CLS} {cls_extra}".strip()
    widget.classes(cls)
    props = f"{_BASE_PROPS} {props_extra}".strip()
    widget.props(props)
    if disabled:
        widget.props("disable")
    return widget


def _escape_prop(value: str) -> str:
    """Escapa comillas para pasar un string dentro de un prop de Quasar."""
    return value.replace('\\', '\\\\').replace('"', '\\"')


def _set_placeholder(widget: Any, placeholder: str) -> None:
    if placeholder:
        widget.props(f'placeholder="{_escape_prop(placeholder)}"')


def field_input(
    label: str,
    value: str | None = "",
    placeholder: str = "",
    requerido: bool = False,
    tooltip: str = "",
    hint: str = "",
    disabled: bool = False,
    on_change: Callable | None = None,
    cls_extra: str = "",
    props_extra: str = "",
    maxlength: int | None = None,
) -> ui.input:
    """Input de texto con label estilo Formik.

    `placeholder` es un EJEMPLO literal (ej: "601"), no un sustituto del
    label. Se deja vacío si no hay un ejemplo natural.
    """
    with _wrap(label, cls_extra) as wrapped:
        label_above(label, requerido, tooltip)
        widget = ui.input(
            placeholder=placeholder,
            value=value or "",
            on_change=on_change,
        )
        _apply(widget, cls_extra, props_extra, disabled, wrapped=wrapped)
        if maxlength is not None:
            widget.props(f"maxlength={maxlength}")
        if hint:
            field_hint(hint)
    return widget


def field_password(
    label: str,
    value: str = "",
    placeholder: str = "",
    requerido: bool = False,
    tooltip: str = "",
    hint: str = "",
    disabled: bool = False,
    on_change: Callable | None = None,
    cls_extra: str = "",
    toggle: bool = True,
) -> ui.input:
    """Input de contraseña con label Formik."""
    with _wrap(label, cls_extra) as wrapped:
        label_above(label, requerido, tooltip)
        widget = ui.input(
            placeholder=placeholder,
            value=value,
            password=True,
            password_toggle_button=toggle,
            on_change=on_change,
        )
        _apply(widget, cls_extra, "", disabled, wrapped=wrapped)
        if hint:
            field_hint(hint)
    return widget


def field_email(
    label: str,
    value: str = "",
    placeholder: str = "",
    requerido: bool = False,
    tooltip: str = "",
    hint: str = "",
    disabled: bool = False,
    on_change: Callable | None = None,
    cls_extra: str = "",
) -> ui.input:
    """Input de email con label Formik."""
    with _wrap(label, cls_extra) as wrapped:
        label_above(label, requerido, tooltip)
        widget = ui.input(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
        )
        _apply(widget, cls_extra, "type=email", disabled, wrapped=wrapped)
        if hint:
            field_hint(hint)
    return widget


def field_number(
    label: str,
    value: float | int | None = None,
    placeholder: str = "",
    requerido: bool = False,
    tooltip: str = "",
    hint: str = "",
    disabled: bool = False,
    on_change: Callable | None = None,
    cls_extra: str = "",
    min: float | int | None = None,
    max: float | int | None = None,
    step: float | int | None = None,
    format: str | None = None,
    precision: int | None = None,
) -> ui.number:
    """Input numérico con label Formik.

    `precision` es un kwarg Python de ui.number (no un prop Quasar) que
    redondea el valor al número de decimales indicado. `format` es una
    cadena `%` para el display textual.
    """
    with _wrap(label, cls_extra) as wrapped:
        label_above(label, requerido, tooltip)
        kwargs: dict = {"placeholder": placeholder, "value": value, "on_change": on_change}
        if min is not None:
            kwargs["min"] = min
        if max is not None:
            kwargs["max"] = max
        if step is not None:
            kwargs["step"] = step
        if format is not None:
            kwargs["format"] = format
        if precision is not None:
            kwargs["precision"] = precision
        widget = ui.number(**kwargs)
        _apply(widget, cls_extra, "", disabled, wrapped=wrapped)
        if hint:
            field_hint(hint)
    return widget


def field_select(
    label: str,
    options: list | dict,
    value: Any = None,
    placeholder: str = "",
    requerido: bool = False,
    tooltip: str = "",
    hint: str = "",
    disabled: bool = False,
    on_change: Callable | None = None,
    cls_extra: str = "",
    clearable: bool = False,
    multiple: bool = False,
    with_input: bool = False,
) -> ui.select:
    """Select con label Formik.

    `with_input=True` habilita el modo combobox con filtrado por escritura
    (mapea al kwarg de `ui.select`, que instala el handler de filter).
    """
    with _wrap(label, cls_extra) as wrapped:
        label_above(label, requerido, tooltip)
        widget = ui.select(
            options=options,
            value=value,
            on_change=on_change,
            multiple=multiple,
            with_input=with_input,
        )
        props_extra = "clearable" if clearable else ""
        _apply(widget, cls_extra, props_extra, disabled, wrapped=wrapped)
        _set_placeholder(widget, placeholder)
        if hint:
            field_hint(hint)
    return widget


def field_textarea(
    label: str,
    value: str = "",
    placeholder: str = "",
    requerido: bool = False,
    tooltip: str = "",
    hint: str = "",
    disabled: bool = False,
    on_change: Callable | None = None,
    cls_extra: str = "",
    rows: int | None = None,
) -> ui.textarea:
    """Textarea con label Formik."""
    with _wrap(label, cls_extra) as wrapped:
        label_above(label, requerido, tooltip)
        widget = ui.textarea(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
        )
        # Textarea no usa _apply para preservar la clase andes-textarea.
        cls_widget = "andes-input andes-textarea w-full" if wrapped else (
            f"andes-input andes-textarea w-full {cls_extra}".strip()
        )
        widget.classes(cls_widget)
        widget.props("borderless")
        if rows is not None:
            widget.props(f"rows={rows}")
        if disabled:
            widget.props("disable")
        if hint:
            field_hint(hint)
    return widget


def field_date(
    label: str,
    value: str = "",
    requerido: bool = False,
    tooltip: str = "",
    hint: str = "",
    disabled: bool = False,
    on_change: Callable | None = None,
    cls_extra: str = "",
) -> ui.input:
    """Input tipo date con label Formik."""
    with _wrap(label, cls_extra) as wrapped:
        label_above(label, requerido, tooltip)
        widget = ui.input(value=value, on_change=on_change)
        _apply(widget, cls_extra, "type=date", disabled, wrapped=wrapped)
        if hint:
            field_hint(hint)
    return widget


def field_time(
    label: str,
    value: str = "",
    requerido: bool = False,
    tooltip: str = "",
    hint: str = "",
    disabled: bool = False,
    on_change: Callable | None = None,
    cls_extra: str = "",
) -> ui.input:
    """Input tipo time con label Formik."""
    with _wrap(label, cls_extra) as wrapped:
        label_above(label, requerido, tooltip)
        widget = ui.input(value=value, on_change=on_change)
        _apply(widget, cls_extra, "type=time", disabled, wrapped=wrapped)
        if hint:
            field_hint(hint)
    return widget


# ── Filtros de toolbars (label opcional arriba) ────────────────────────────
# Para toolbars/filtros. Igual que field_*, pero con label OPCIONAL: cuando
# el contexto ya deja claro el significado (una barra "Filtros:" antepuesta,
# una tabla con encabezados), se puede omitir. `placeholder` sigue siendo
# EJEMPLO, nunca sustituto del label.

def filter_input(
    label: str = "",
    value: str | None = "",
    placeholder: str = "",
    on_change: Callable | None = None,
    disabled: bool = False,
    cls_extra: str = "",
) -> ui.input:
    """Input de filtro. Pasa `label` para etiquetarlo semánticamente."""
    with _wrap(label, cls_extra) as wrapped:
        if label:
            label_above(label)
        widget = ui.input(placeholder=placeholder, value=value or "", on_change=on_change)
        _apply(widget, cls_extra, "", disabled, wrapped=wrapped)
    return widget


def filter_select(
    label: str = "",
    options: list | dict | None = None,
    value: Any = None,
    placeholder: str = "",
    on_change: Callable | None = None,
    disabled: bool = False,
    clearable: bool = True,
    cls_extra: str = "",
    multiple: bool = False,
    with_input: bool = False,
) -> ui.select:
    """Select de filtro. Pasa `label` para etiquetarlo semánticamente."""
    with _wrap(label, cls_extra) as wrapped:
        if label:
            label_above(label)
        widget = ui.select(
            options=options or {},
            value=value,
            on_change=on_change,
            multiple=multiple,
            with_input=with_input,
        )
        props_extra = "clearable" if clearable else ""
        _apply(widget, cls_extra, props_extra, disabled, wrapped=wrapped)
        _set_placeholder(widget, placeholder)
    return widget


def filter_number(
    label: str = "",
    value: float | int | None = None,
    placeholder: str = "",
    on_change: Callable | None = None,
    disabled: bool = False,
    cls_extra: str = "",
    min: float | int | None = None,
    max: float | int | None = None,
    step: float | int | None = None,
    precision: int | None = None,
) -> ui.number:
    """Number de filtro. Pasa `label` para etiquetarlo semánticamente."""
    with _wrap(label, cls_extra) as wrapped:
        if label:
            label_above(label)
        kwargs: dict = {"placeholder": placeholder, "value": value, "on_change": on_change}
        if min is not None:
            kwargs["min"] = min
        if max is not None:
            kwargs["max"] = max
        if step is not None:
            kwargs["step"] = step
        if precision is not None:
            kwargs["precision"] = precision
        widget = ui.number(**kwargs)
        _apply(widget, cls_extra, "", disabled, wrapped=wrapped)
    return widget


def inline_select(
    options: list | dict,
    value: Any = None,
    on_change: Callable | None = None,
    disabled: bool = False,
    cls_extra: str = "",
    clearable: bool = False,
) -> ui.select:
    """Select inline sin label — celdas de tabla u otro contexto denso."""
    widget = ui.select(options=options, value=value, on_change=on_change)
    props_extra = "clearable" if clearable else ""
    _apply(widget, cls_extra, props_extra, disabled)
    return widget


def inline_input(
    value: str = "",
    placeholder: str = "",
    on_change: Callable | None = None,
    disabled: bool = False,
    cls_extra: str = "",
) -> ui.input:
    """Input inline sin label — celdas de tabla."""
    widget = ui.input(value=value, placeholder=placeholder, on_change=on_change)
    _apply(widget, cls_extra, "", disabled)
    return widget


def inline_number(
    value: float | int | None = None,
    on_change: Callable | None = None,
    disabled: bool = False,
    cls_extra: str = "",
    min: float | int | None = None,
    max: float | int | None = None,
    step: float | int | None = None,
    precision: int | None = None,
) -> ui.number:
    """Number inline sin label — celdas de tabla."""
    kwargs: dict = {"value": value, "on_change": on_change}
    if min is not None:
        kwargs["min"] = min
    if max is not None:
        kwargs["max"] = max
    if step is not None:
        kwargs["step"] = step
    if precision is not None:
        kwargs["precision"] = precision
    widget = ui.number(**kwargs)
    _apply(widget, cls_extra, "", disabled)
    return widget


__all__ = [
    "field_date",
    "field_email",
    "field_hint",
    "field_input",
    "field_number",
    "field_password",
    "field_select",
    "field_textarea",
    "field_time",
    "filter_input",
    "filter_number",
    "filter_select",
    "inline_input",
    "inline_number",
    "inline_select",
    "label_above",
]
