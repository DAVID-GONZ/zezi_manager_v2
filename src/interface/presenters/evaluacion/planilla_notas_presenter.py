"""Presenter puro de la planilla de notas (`/evaluacion/planilla`).

Sin import de NiceGUI. Los cálculos de nota (ponderaciones, pesos, cortes) viven
en `evaluacion_service`; aquí el view-state es el contexto seleccionado, el modo de
vista, los toggles y los formularios de actividad/categoría.
"""
from __future__ import annotations

from typing import ClassVar


class PlanillaNotasPresenter:
    """View-model de la planilla: selección + modo + toggles + formularios."""

    _ACT_FORM_DEFAULTS: ClassVar[dict] = {
        "act_nombre": "",
        "act_descripcion": "",
        "act_valor_max": 100.0,
        "act_categoria_id": None,
    }
    _CAT_FORM_DEFAULTS: ClassVar[dict] = {"form_cat_nombre": "", "form_cat_peso": 10}

    def __init__(self) -> None:
        self.estado: dict = {
            "asignacion_id": None,
            "periodo_id": None,
            "grupo_id": None,
            "sel_periodo_id": None,
            "sel_periodo_nombre": "",
            "sel_grupo_id": None,
            "sel_grupo_nombre": "",
            "sel_asignacion_id": None,
            "sel_asignacion_nombre": "",
            "categorias": [],
            "actividades": [],
            "planilla": [],
            "puntos_extra": {},
            "mostrar_puntos": False,
            "modo": "planilla",  # planilla | actividades | corte
            "corte": None,
            "notas_corte": {},
            **dict(self._ACT_FORM_DEFAULTS),
            **dict(self._CAT_FORM_DEFAULTS),
            "anio_id": None,
            "siee_cfg": None,
            "cats_inst": [],
            "peso_disponible": 1.0,
            "cargando": True,
        }

    def aplicar_seleccion(self, seleccion: dict) -> None:
        self.estado["asignacion_id"] = seleccion["sel_asignacion_id"]
        self.estado["periodo_id"] = seleccion["sel_periodo_id"]
        self.estado["grupo_id"] = seleccion["sel_grupo_id"]

    def set_modo(self, modo: str) -> None:
        self.estado["modo"] = modo

    def toggle_puntos(self) -> None:
        self.estado["mostrar_puntos"] = not self.estado["mostrar_puntos"]

    def reset_act_form(self) -> None:
        self.estado.update(self._ACT_FORM_DEFAULTS)

    def reset_cat_form(self) -> None:
        self.estado.update(self._CAT_FORM_DEFAULTS)


__all__ = ["PlanillaNotasPresenter"]
