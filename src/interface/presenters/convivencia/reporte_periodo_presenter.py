"""Presenter puro del reporte de periodo de convivencia (`/convivencia/reporte-periodo`).

Sin import de NiceGUI. El cálculo del reporte y los KPIs vive en
`convivencia_service`; el view-state es la selección de grupo/periodo y los datos
cargados.
"""
from __future__ import annotations


class ReportePeriodoPresenter:
    """View-model del reporte de periodo: selección grupo/periodo + datos."""

    def __init__(self) -> None:
        self.estado: dict = {
            "grupo_id": None,
            "periodo_id": None,
            "filas": [],
            "kpis": None,
            "sel_periodo_id": None,
            "sel_periodo_nombre": "",
            "sel_grupo_id": None,
            "sel_grupo_nombre": "",
        }

    def aplicar_seleccion(self, seleccion: dict) -> None:
        self.estado["grupo_id"] = seleccion["sel_grupo_id"]
        self.estado["periodo_id"] = seleccion["sel_periodo_id"]
        self.estado["sel_grupo_nombre"] = seleccion.get("sel_grupo_nombre", "")
        self.estado["sel_periodo_nombre"] = seleccion.get("sel_periodo_nombre", "")

    def set_filas(self, filas) -> None:
        self.estado["filas"] = list(filas)

    def set_kpis(self, kpis) -> None:
        self.estado["kpis"] = kpis


__all__ = ["ReportePeriodoPresenter"]
