"""Presenter puro de la página de plan de estudios (`/admin/plan-estudios`).

Sin import de NiceGUI. Guarda el view-state (grado seleccionado, formulario de
grado, vinculación de asignatura) y las listas cargadas. La validación (horas,
grado 1-13) vive en el servicio/modelo.
"""
from __future__ import annotations


class PlanEstudiosPresenter:
    """View-model de plan de estudios: selección de grado + formularios."""

    def __init__(self) -> None:
        self.estado: dict = {
            "grados": [],
            "asignaturas": [],
            "areas": [],
            "grado_sel": None,
            "plan_map": {},
            # formulario nuevo grado
            "g_numero": None,
            "g_nombre": "",
            "g_min": 20,
            "g_max": 40,
            "g_horas": 30,
            # vincular asignatura
            "vinc_area_id": None,
            "vinc_asig_id": None,
        }

    def set_grado_sel(self, numero) -> None:
        """Seleccionar un grado resetea la asignatura a vincular."""
        self.estado["grado_sel"] = numero
        self.estado["vinc_asig_id"] = None

    def reset_grado_form(self) -> None:
        """Restaura el formulario de grado tras guardar (número y nombre)."""
        self.estado["g_numero"] = None
        self.estado["g_nombre"] = ""

    def limpiar_vinc(self) -> None:
        self.estado["vinc_asig_id"] = None

    def set_grados(self, grados) -> None:
        self.estado["grados"] = list(grados)


__all__ = ["PlanEstudiosPresenter"]
