"""
src/interface/pages/evaluacion/configuracion_evaluacion.py
===========================================================
Redirect de compatibilidad.

La configuración de categorías, actividades y corte de Plan de Mejoramiento
se gestionan desde /evaluacion/planilla (tres modos de vista en la misma
página). Esta ruta redirige allí para no romper bookmarks ni enlaces existentes.
"""

from __future__ import annotations

from nicegui import ui


# page-delegate: ruta registrada en main.py (paso_35)
def configuracion_evaluacion_page() -> None:
    ui.navigate.to("/evaluacion/planilla")


__all__ = ["configuracion_evaluacion_page"]
