"""Presenter puro de planes de mejoramiento (`/evaluacion/planes`).

Sin import de NiceGUI. Guarda el view-state (selección de periodo/asignación,
grupo derivado, formulario de actividad) y los datos cargados. La derivación del
grupo a partir de la asignación es view-logic pura y testeable.
"""
from __future__ import annotations

from typing import ClassVar


class PlanesMejoramientoPresenter:
    """View-model de planes de mejoramiento: selección + formulario de actividad."""

    _ACT_FORM_DEFAULTS: ClassVar[dict] = {
        "form_act_nombre": "",
        "form_act_peso": 0.20,
        "form_act_desc": "",
    }

    def __init__(self) -> None:
        self.estado: dict = {
            "periodos": [],
            "asignaciones": [],
            "periodo_id": None,
            "asignacion_id": None,
            "grupo_id": None,
            "corte": None,
            "notas_corte": [],
            "actividades_plan": [],
            **dict(self._ACT_FORM_DEFAULTS),
            "nombres_est": {},
            "notas_act": {},
        }

    def grupo_de_asignacion(self, asignacion_id) -> int | None:
        """Grupo de la asignación seleccionada (o None si no se encuentra)."""
        info = next(
            (a for a in self.estado["asignaciones"] if a.asignacion_id == asignacion_id), None
        )
        return info.grupo_id if info else None

    def reset_actividad_form(self) -> None:
        self.estado.update(self._ACT_FORM_DEFAULTS)


__all__ = ["PlanesMejoramientoPresenter"]
