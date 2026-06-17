"""
pipeline.py — Guía de flujo (stepper) del design system.

Renderiza una secuencia de pasos clicables que orienta un proceso de varios
módulos (p. ej. Asignaturas → Plan de estudios → Asignaciones → Horarios),
resaltando el paso actual y permitiendo navegar a los demás.
"""
from __future__ import annotations

from typing import Sequence

from nicegui import ui


def pipeline_nav(
    pasos: Sequence[tuple[str, str, str]],
    activo: str,
    *,
    hint: str = "",
) -> None:
    """
    Args:
        pasos: secuencia de (clave, etiqueta, ruta).
        activo: clave del paso actual (se resalta y no navega).
        hint:   texto guía contextual mostrado bajo el stepper.
    """
    with ui.element("div").classes("pipeline"):
        for i, (clave, etiqueta, ruta) in enumerate(pasos, start=1):
            es_activo = clave == activo
            cls = "pipeline-paso" + (" pipeline-paso-activo" if es_activo else "")
            paso = ui.element("div").classes(cls)
            if not es_activo and ruta:
                paso.on("click", lambda _, r=ruta: ui.navigate.to(r))
            with paso:
                ui.label(str(i)).classes("pipeline-num")
                ui.label(etiqueta)
            if i < len(pasos):
                ui.label("›").classes("pipeline-sep")
    if hint:
        ui.label(hint).classes("pipeline-hint")


__all__ = ["pipeline_nav"]
