"""Presenter puro de cierre de periodo (`/evaluacion/cierre-periodo`).

Sin import de NiceGUI. La lógica de cierre vive en `cierre_service`; el view-state
es la selección de periodo/grupo y las listas cargadas.
"""
from __future__ import annotations


class CierrePeriodoPresenter:
    """View-model de cierre de periodo: selección periodo/grupo."""

    def __init__(self) -> None:
        self.estado: dict = {
            "anio_id": None,
            "periodos": [],
            "grupos": [],
            "periodo_id": None,
            "grupo_id": None,
            "asignaciones": [],
            "estado_cierres": {},  # asignacion_id → list[CierrePeriodo]
        }

    def set_periodo(self, valor) -> None:
        self.estado["periodo_id"] = valor

    def set_grupo(self, valor) -> None:
        self.estado["grupo_id"] = valor

    def set_asignaciones(self, asignaciones) -> None:
        self.estado["asignaciones"] = list(asignaciones)


__all__ = ["CierrePeriodoPresenter"]
