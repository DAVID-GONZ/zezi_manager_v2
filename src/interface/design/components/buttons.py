"""
buttons.py — Fábrica centralizada de botones del Design System Andes Minimal v2.

Regla: TODA creación de botón en src/interface/ pasa por estas funciones.
       Prohibido en páginas y components: ui.button().props("flat"),
       ui.button(color="primary"), etc.

Por qué color=None es obligatorio:
  Quasar inyecta clases .bg-primary, .text-white, etc. cuando se pasa
  color="primary". Esas clases sobreescriben los estilos de .btn-primary
  definidos en styles.css. color=None bloquea esa inyección.
"""
from __future__ import annotations

from typing import Callable, Literal

from nicegui import ui


def _build(
    text: str,
    on_click: Callable | None,
    variant: str,
    icon: str | None,
    size: str | None,
    disabled: bool,
) -> ui.button:
    btn = ui.button(text, on_click=on_click, color=None, icon=icon)
    clases = f"btn btn-{variant}"
    if size == "sm":
        clases += " btn-sm"
    elif size == "lg":
        clases += " btn-lg"
    btn.classes(clases)
    if disabled:
        btn.props("disable")
    return btn


def btn_primary(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button:
    """Acción principal — fondo sólido primario."""
    return _build(text, on_click, "primary", icon, size, disabled)


def btn_secondary(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button:
    """Acción secundaria — borde primario, fondo transparente."""
    return _build(text, on_click, "secondary", icon, size, disabled)


def btn_danger(
    text: str,
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button:
    """Acción destructiva — fondo rojo."""
    return _build(text, on_click, "danger", icon, size, disabled)


def btn_ghost(
    text: str | None = "",
    on_click: Callable | None = None,
    *,
    icon: str | None = None,
    size: Literal["sm", "md", "lg"] | None = None,
    disabled: bool = False,
) -> ui.button:
    """Acción terciaria / cancelar — plano, sin borde ni fondo.

    `text` ahora es opcional para permitir llamadas que pasan solo kwargs
    (ej. `btn_ghost(icon="edit", on_click=...)`). En esos casos se
    renderiza un botón sin texto visible.
    """
    return _build(text or "", on_click, "ghost", icon, size, disabled)


def btn_icon(
    icono: str,
    on_click: Callable | None = None,
    *,
    tooltip: str = "",
    variante: Literal["primary", "secondary", "danger", "ghost"] = "ghost",
    size: Literal["sm", "md"] = "md",
) -> ui.button:
    """
    Botón solo-icono circular.
    Reemplaza: ui.button(icon=X).props("flat round dense")
    """
    size_cls = "btn-icon-sm" if size == "sm" else "btn-icon"
    btn = ui.button(icon=icono, on_click=on_click, color=None)
    btn.classes(f"btn {size_cls} btn-{variante}")
    if tooltip:
        btn.tooltip(tooltip)
    return btn


__all__ = ["btn_primary", "btn_secondary", "btn_danger", "btn_ghost", "btn_icon"]
