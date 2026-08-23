"""Presenter puro de los boletines (`/informes/boletin-*`).

Compartido por boletin_periodo y boletin_anual: ambos comparten el view-state de
selección de grupo (con coerción a int) y la lista de estudiantes del grupo. Cada
página añade su campo propio al estado (`periodo_id` / `anio_id`). La generación
del boletín (servicio + descarga) se queda en cada página. Sin import de NiceGUI.
"""
from __future__ import annotations


class BoletinPresenter:
    """View-model común de los boletines: grupo + estudiantes."""

    def __init__(self) -> None:
        self.estado: dict = {
            "grupo_id": None,
            "grupos": [],
            "estudiantes": [],
            "todas_asignaciones_docente": [],
            "generando": False,
        }

    @staticmethod
    def a_int(valor) -> int | None:
        return int(valor) if valor is not None else None

    def set_grupo(self, valor) -> None:
        self.estado["grupo_id"] = self.a_int(valor)

    def set_estudiantes(self, estudiantes) -> None:
        self.estado["estudiantes"] = list(estudiantes)

    def set_grupos(self, grupos) -> None:
        self.estado["grupos"] = list(grupos)


__all__ = ["BoletinPresenter"]
