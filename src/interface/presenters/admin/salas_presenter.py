"""Presenter puro de la página de salas (`/admin/salas`).

Página CRUD fina: la lógica de negocio (validación de sala, unicidad, borrado
seguro) vive en `sala_service`/el modelo `Sala`. Aquí el view-state es el
formulario de "nueva sala" (con sus valores por defecto y el reset tras crear) y
las dos listas cargadas. Sin import de NiceGUI.
"""
from __future__ import annotations

from typing import ClassVar


class SalasPresenter:
    """View-model de salas: formulario de creación + listas cargadas."""

    _FORM_DEFAULTS: ClassVar[dict] = {"nombre": "", "tipo": "aula", "capacidad": 30}

    def __init__(self) -> None:
        self.estado: dict = {"salas": [], "grupos": [], **dict(self._FORM_DEFAULTS)}

    def reset_form(self) -> None:
        """Restaura el formulario de nueva sala a sus valores por defecto."""
        self.estado.update(self._FORM_DEFAULTS)

    def set_salas(self, salas) -> None:
        self.estado["salas"] = list(salas)

    def set_grupos(self, grupos) -> None:
        self.estado["grupos"] = list(grupos)


__all__ = ["SalasPresenter"]
