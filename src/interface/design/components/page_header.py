"""
page_header.py — Cabecera de página del design system Andes Minimal.

Ajustes NiceGUI 3.x:
  - Iconos via ThemeManager.icono() (ui.html) en vez de ui.element().text()
  - Botones de acción usan context managers o parámetros directos, no .add()
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.interface.design.theme import ThemeManager


def page_header(
    titulo: str,
    subtitulo: str = "",
    icono: str = "",
    acciones: list[dict] | None = None,
) -> None:
    """
    Renderiza la cabecera estándar de una página/sección.

    Args:
        titulo:    Texto principal del encabezado.
        subtitulo: Descripción secundaria opcional.
        icono:     Nombre de Material Symbol Rounded (ej: "space_dashboard").
                   Si está vacío, no se renderiza icono.
        acciones:  Lista de dicts con configuración de botones. Cada dict:
                   {
                       "label":    str,           # Texto del botón
                       "on_click": Callable,      # Handler del click
                       "icono":    str | None,    # Icono opcional (Material Symbol)
                       "variante": str,           # "primary" | "secondary" | "danger"
                   }
                   Si es None o lista vacía, no se renderizan botones.

    Ejemplo:
        page_header(
            titulo="Gestión de Estudiantes",
            subtitulo="Lista completa de estudiantes activos",
            icono="school",
            acciones=[
                {"label": "Nuevo", "on_click": crear_estudiante, "icono": "add", "variante": "primary"},
                {"label": "Exportar", "on_click": exportar, "icono": "download", "variante": "secondary"},
            ],
        )
    """
    with ui.row().classes("items-center justify-between").style(
        "width:100%;"
        "margin-bottom:var(--space-lg);"
        "padding-bottom:var(--space-md);"
        "border-bottom: 1px solid var(--color-divider);"
    ):
        # Lado izquierdo: icono + textos
        with ui.row().classes("items-center gap-3"):
            if icono:
                ThemeManager.icono(
                    icono,
                    size=32,
                    color="var(--color-primary)",
                )

            with ui.column().classes("gap-0"):
                ui.label(titulo).classes("font-h2").style(
                    "color:var(--color-text-primary); line-height:1.2;"
                )
                if subtitulo:
                    ui.label(subtitulo).style(
                        "color:var(--color-text-secondary);"
                        "font-size:var(--font-size-small);"
                        "margin-top:2px;"
                    )

        # Lado derecho: botones de acción
        if acciones:
            with ui.row().classes("gap-2 items-center"):
                for accion in acciones:
                    variante = accion.get("variante", "primary")
                    btn_class = {
                        "primary":   "btn-primary",
                        "secondary": "btn-secondary",
                        "danger":    "btn-danger",
                    }.get(variante, "btn-primary")

                    icono_accion = accion.get("icono", "")
                    label_accion = accion.get("label", "")
                    on_click     = accion.get("on_click", lambda: None)

                    with ui.button(on_click=on_click).classes(btn_class).style(
                        "display:inline-flex;align-items:center;gap:6px;"
                    ):
                        if icono_accion:
                            ThemeManager.icono(icono_accion, size=18, color="inherit")
                        ui.label(label_accion)


__all__ = ["page_header"]
