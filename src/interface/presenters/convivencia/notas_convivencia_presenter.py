"""Presenter puro de la página de notas de convivencia (`/convivencia/notas`).

Sin import de NiceGUI. Guarda el view-state (selección + detalle del estudiante +
cambios pendientes) y `aplicar_seleccion`, que copia la selección del selector y
resetea el detalle. La carga (estudiantes/notas) y la verificación de periodo se
quedan en la página.
"""
from __future__ import annotations


class NotasConvivenciaPresenter:
    """View-model de notas de convivencia: selección + detalle del estudiante."""

    def __init__(self) -> None:
        self.estado: dict = {
            "estudiantes": [],
            "periodos": [],
            "notas": [],
            "sel_estudiante_ids": [],
            "sel_estudiante_id": None,
            "observaciones_estudiante": [],
            "registros_estudiante": [],
            "asignaciones_grupo": [],
            "sel_periodo_id": None,
            "sel_grupo_id": None,
            "sel_grupo_nombre": "",
            "sel_asignacion_id": None,
            "sel_asignacion_nombre": "",
            "periodo_cerrado": False,
            "cambios_pendientes": {},
            "nota_min_escala": 0.0,
            "nota_max_escala": 100.0,
        }

    def aplicar_seleccion(self, seleccion: dict) -> None:
        """Copia la selección y resetea el detalle del estudiante y los cambios."""
        self.estado["sel_periodo_id"] = seleccion["sel_periodo_id"]
        self.estado["sel_grupo_id"] = seleccion["sel_grupo_id"]
        self.estado["sel_asignacion_id"] = seleccion["sel_asignacion_id"]
        self.estado["sel_asignacion_nombre"] = seleccion.get("sel_asignacion_nombre", "")
        self.estado["sel_estudiante_ids"] = []
        self.estado["sel_estudiante_id"] = None
        self.estado["observaciones_estudiante"] = []
        self.estado["registros_estudiante"] = []
        self.estado["cambios_pendientes"] = {}


__all__ = ["NotasConvivenciaPresenter"]
