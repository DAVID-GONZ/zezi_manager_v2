"""Presenter puro de cierre de año (`/evaluacion/cierre-anio`).

Sin import de NiceGUI. La lógica de cierre/promoción vive en `cierre_service`; el
view-state es el grupo seleccionado, el año activo y el resultado del cierre.
"""
from __future__ import annotations


class CierreAnioPresenter:
    """View-model de cierre de año: selección de grupo + resultado."""

    def __init__(self) -> None:
        self.estado: dict = {"grupos": [], "anio": None, "grupo_id": None, "resultado": []}

    def set_grupo(self, valor) -> None:
        self.estado["grupo_id"] = valor

    def set_resultado(self, resultado) -> None:
        self.estado["resultado"] = resultado

    def set_grupos(self, grupos) -> None:
        self.estado["grupos"] = list(grupos)

    def set_anio(self, anio) -> None:
        self.estado["anio"] = anio

    def grupo_nombre(self) -> str:
        gid = self.estado["grupo_id"]
        if gid is None:
            return ""
        return next((g.codigo for g in self.estado["grupos"] if g.id == gid), str(gid))


__all__ = ["CierreAnioPresenter"]
