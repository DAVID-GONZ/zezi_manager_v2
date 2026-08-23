"""Presenter puro del tablero de estadísticos (`/academico/tablero`).

Sin import de NiceGUI. Los cálculos y agregados viven en `estadisticos_service`;
aquí el view-state es el contexto académico seleccionado, el drill-down de
directivos y los datos/KPIs cargados.
"""
from __future__ import annotations


class TableroEstadisticosPresenter:
    """View-model del tablero: selección + drill-down + datos cargados."""

    def __init__(self) -> None:
        self.estado: dict = {
            "periodo_id": None,
            "anio_id": None,
            "grupo_id": None,
            "asignacion_id": None,
            "sel_periodo_id": None,
            "sel_periodo_nombre": "",
            "sel_grupo_id": None,
            "sel_grupo_nombre": "",
            "sel_asignacion_id": None,
            "sel_asignacion_nombre": "",
            "global_data": [],
            "kpi_grupos": 0,
            "kpi_promedio": 0.0,
            "kpi_asistencia": 0.0,
            "kpi_riesgo": 0,
            "drill_grupo_id": None,
            "drill_asig_id": None,
            "drill_asignaciones": [],
            "cargando_global": True,
        }

    def aplicar_seleccion(self, seleccion: dict) -> None:
        """Copia el contexto del selector y resetea el drill-down."""
        self.estado["periodo_id"] = seleccion["sel_periodo_id"]
        self.estado["grupo_id"] = seleccion["sel_grupo_id"]
        self.estado["asignacion_id"] = seleccion["sel_asignacion_id"]
        self.estado["drill_grupo_id"] = None
        self.estado["drill_asig_id"] = None

    def set_drill_grupo(self, grupo_id) -> None:
        """Elegir grupo en el drill resetea la asignación del drill."""
        self.estado["drill_grupo_id"] = grupo_id
        self.estado["drill_asig_id"] = None

    def set_drill_asig(self, asignacion_id) -> None:
        self.estado["drill_asig_id"] = asignacion_id


__all__ = ["TableroEstadisticosPresenter"]
