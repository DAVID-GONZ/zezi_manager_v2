"""Presenter puro de la página de grupos (`/admin/grupos`).

Sin import de NiceGUI. La validación del grupo vive en el modelo/servicio; aquí
el view-state son los formularios de creación y edición y las listas cargadas.
"""
from __future__ import annotations

from typing import ClassVar


class GruposPresenter:
    """View-model de grupos: formularios (crear/editar) + listas cargadas."""

    _CREATE_DEFAULTS: ClassVar[dict] = {
        "form_codigo": "",
        "form_grado": 1,
        "form_jornada": "UNICA",
        "form_capacidad": 40,
    }

    def __init__(self) -> None:
        self.estado: dict = {
            "grupos": [],
            "grados": [],
            "cargando": False,
            **dict(self._CREATE_DEFAULTS),
            # estado de edición inline
            "edit_id": None,
            "edit_codigo": "",
            "edit_grado": 1,
            "edit_jornada": "UNICA",
            "edit_capacidad": 40,
        }

    def set_grupos(self, grupos) -> None:
        self.estado["grupos"] = list(grupos)

    def reset_create_form(self, grado_default: int | None = None) -> None:
        """Restaura el formulario de creación. `grado_default` permite fijar el
        primer grado válido, que la página calcula con su propio helper."""
        self.estado.update(self._CREATE_DEFAULTS)
        if grado_default is not None:
            self.estado["form_grado"] = grado_default


__all__ = ["GruposPresenter"]
