"""Presenter puro de la página de gestión de equipo docente (`/director/equipo`).

Sin import de NiceGUI. View-state: filtros (rol/activos) + lista de usuarios
del tenant del director.
"""
from __future__ import annotations


class GestionUsuariosPresenter:
    """View-model de equipo docente: filtros (rol/activos) + lista."""

    def __init__(self) -> None:
        self.estado: dict = {
            "usuarios": [],
            "filtro_rol": None,
            "filtro_activos": True,
        }

    def set_usuarios(self, usuarios) -> None:
        self.estado["usuarios"] = list(usuarios)

    def set_filtro_rol(self, valor) -> None:
        self.estado["filtro_rol"] = valor

    def set_filtro_activos(self, valor) -> None:
        self.estado["filtro_activos"] = bool(valor)


__all__ = ["GestionUsuariosPresenter"]
