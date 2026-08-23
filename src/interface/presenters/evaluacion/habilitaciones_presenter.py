"""Presenter puro de la página de habilitaciones/nivelación (`/evaluacion/habilitaciones`).

Sin import de NiceGUI. La lógica de nivelación (bajo desempeño, planilla, cierre)
vive en `nivelacion_service`; aquí el view-state es la selección de periodo y
asignación y los datos cargados de esa selección.
"""
from __future__ import annotations


class HabilitacionesPresenter:
    """View-model de habilitaciones: selección + datos de nivelación cargados."""

    def __init__(self) -> None:
        self.estado: dict = {
            "periodos": [],
            "asignaciones": [],
            "nivel_periodo_id": None,
            "nivel_asig_id": None,
            "nivel_cierres": [],
            "nivel_cierre": None,
            "nivel_planilla": None,
        }

    def set_nivel_periodo(self, valor) -> None:
        self.estado["nivel_periodo_id"] = valor

    def set_nivel_asig(self, valor) -> None:
        self.estado["nivel_asig_id"] = valor


__all__ = ["HabilitacionesPresenter"]
