"""Presenter puro del catálogo de instituciones (`/admin/instituciones`).

Página CRUD fina: el aprovisionamiento y la validación viven en el servicio; el
único view-state es la lista cargada. Sin import de NiceGUI.
"""
from __future__ import annotations


class CatalogoInstitucionesPresenter:
    """View-model del catálogo de instituciones (solo la lista cargada)."""

    def __init__(self) -> None:
        self.estado: dict = {"instituciones": []}

    def set_instituciones(self, instituciones) -> None:
        self.estado["instituciones"] = list(instituciones)


__all__ = ["CatalogoInstitucionesPresenter"]
