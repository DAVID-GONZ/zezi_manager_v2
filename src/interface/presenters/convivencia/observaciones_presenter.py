"""Presenter puro de la página de observaciones (`/convivencia/observaciones`).

Sin import de NiceGUI. Guarda el view-state de la selección (periodo/grupo/
asignatura + estudiantes elegidos) y los datos cargados del grupo. `aplicar_seleccion`
copia la selección del selector inline y resetea los estudiantes elegidos; la carga
de estudiantes/asignaciones se queda en la página.
"""
from __future__ import annotations


class ObservacionesPresenter:
    """View-model de observaciones: selección periodo/grupo/asignatura."""

    def __init__(self) -> None:
        self.estado: dict = {
            "estudiantes": [],
            "periodos": [],
            "anio_id": None,
            "sel_estudiante_ids": [],
            "sel_periodo_id": None,
            "sel_grupo_id": None,
            "sel_grupo_nombre": "",
            "sel_asignacion_id": None,
            "sel_asignacion_nombre": "",
            "plantilla_id": None,
            "asignaciones_grupo": [],
        }

    def aplicar_seleccion(self, seleccion: dict) -> None:
        """Copia periodo/grupo/asignatura del selector y limpia los estudiantes elegidos."""
        self.estado["sel_periodo_id"] = seleccion["sel_periodo_id"]
        self.estado["sel_grupo_id"] = seleccion["sel_grupo_id"]
        self.estado["sel_asignacion_id"] = seleccion["sel_asignacion_id"]
        self.estado["sel_asignacion_nombre"] = seleccion.get("sel_asignacion_nombre", "")
        self.estado["sel_estudiante_ids"] = []


__all__ = ["ObservacionesPresenter"]
