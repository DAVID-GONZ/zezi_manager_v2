"""
page_header.py — Cabecera de página del design system Andes Minimal.

Ajustes NiceGUI 3.x:
  - Iconos via ThemeManager.icono() (ui.html) en vez de ui.element().text()
  - Botones de acción usan btn_*() del design system
"""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.interface.design.theme import ThemeManager
from src.interface.design.components.buttons import btn_primary, btn_secondary, btn_danger


def page_header(
    titulo: str,
    subtitulo: str = "",
    icono: str = "",
    acciones: list[dict] | None = None,
) -> None:
    """
    .. deprecated::
        Usar los parámetros page_titulo/page_subtitulo/page_icono/page_acciones
        en app_layout() en su lugar. Este componente se mantiene por compatibilidad.

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
    with ui.row().classes("page-header-row items-center justify-between"):
        # Lado izquierdo: icono + textos
        with ui.row().classes("items-center gap-3"):
            if icono:
                ThemeManager.icono(
                    icono,
                    size=32,
                    color="var(--color-primary)",
                )

            with ui.column().classes("gap-0"):
                ui.label(titulo).classes("font-h2 page-header-title")
                if subtitulo:
                    ui.label(subtitulo).classes("page-header-sub")

        # Lado derecho: botones de acción
        if acciones:
            with ui.row().classes("gap-2 items-center"):
                for accion in acciones:
                    variante     = accion.get("variante", "primary")
                    icono_accion = accion.get("icono", None)
                    label_accion = accion.get("label", "")
                    on_click     = accion.get("on_click", lambda: None)

                    if variante == "danger":
                        btn_danger(label_accion, on_click=on_click, icon=icono_accion)
                    elif variante == "secondary":
                        btn_secondary(label_accion, on_click=on_click, icon=icono_accion)
                    else:
                        btn_primary(label_accion, on_click=on_click, icon=icono_accion)


__all__ = ["page_header"]
