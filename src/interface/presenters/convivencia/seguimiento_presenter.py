"""Presenter puro del hub de seguimiento de convivencia (`/convivencia/seguimiento`).

Sin import de NiceGUI. Guarda el view-state (selección grupo/periodo, estudiante y
sección del detalle) y sus transiciones. La carga de series/observaciones/alertas
y el cálculo 360° viven en `convivencia_service`.
"""
from __future__ import annotations


class SeguimientoPresenter:
    """View-model de seguimiento: selección grupo/periodo + detalle del estudiante."""

    def __init__(self) -> None:
        self.estado: dict = {
            "sel_periodo_id": None,
            "sel_periodo_nombre": "",
            "sel_grupo_id": None,
            "sel_grupo_nombre": "",
            "anio_id": None,
            "estudiantes": [],
            "resumen": [],
            "docentes": [],
            "sel_estudiante_id": None,
            "sel_seccion": "evolucion",  # evolucion|observaciones|registros|alertas
            "serie": [],
            "observaciones_est": [],
            "registros_est": [],
            "resultado_360": None,
            "alertas": [],
        }

    def aplicar_seleccion(self, seleccion: dict) -> None:
        """Cambiar grupo/periodo limpia la selección de estudiante y su detalle."""
        self.estado["sel_periodo_id"] = seleccion["sel_periodo_id"]
        self.estado["sel_grupo_id"] = seleccion["sel_grupo_id"]
        self.estado["sel_grupo_nombre"] = seleccion.get("sel_grupo_nombre", "")
        self._reset_detalle()

    def seleccionar_estudiante(self, estudiante_id) -> None:
        """Elegir estudiante vuelve a la sección 'evolución' y limpia el 360°."""
        self.estado["sel_estudiante_id"] = estudiante_id
        self.estado["sel_seccion"] = "evolucion"
        self.estado["resultado_360"] = None

    def set_seccion(self, seccion: str) -> None:
        self.estado["sel_seccion"] = seccion

    def _reset_detalle(self) -> None:
        self.estado["sel_estudiante_id"] = None
        self.estado["resultado_360"] = None
        self.estado["serie"] = []
        self.estado["observaciones_est"] = []
        self.estado["registros_est"] = []
        self.estado["alertas"] = []


__all__ = ["SeguimientoPresenter"]
