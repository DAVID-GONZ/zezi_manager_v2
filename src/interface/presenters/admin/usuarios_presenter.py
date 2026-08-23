"""Presenter puro de la página de usuarios (`/admin/usuarios`).

Sin import de NiceGUI. El filtrado es server-side (lo hace `usuario_service` con
un `FiltroUsuariosDTO`); aquí el view-state son los tres filtros y la lista
cargada. Presenter fino: transiciones de filtro + setter de la lista.
"""
from __future__ import annotations


class UsuariosPresenter:
    """View-model de usuarios: filtros (rol/activos/institución) + lista."""

    def __init__(self) -> None:
        self.estado: dict = {
            "usuarios": [],
            "filtro_rol": None,
            "filtro_activos": True,
            "filtro_institucion": None,
        }

    def set_usuarios(self, usuarios) -> None:
        self.estado["usuarios"] = list(usuarios)

    def set_filtro_rol(self, valor) -> None:
        self.estado["filtro_rol"] = valor

    def set_filtro_activos(self, valor) -> None:
        self.estado["filtro_activos"] = bool(valor)

    def set_filtro_institucion(self, valor) -> None:
        self.estado["filtro_institucion"] = valor


__all__ = ["UsuariosPresenter"]
