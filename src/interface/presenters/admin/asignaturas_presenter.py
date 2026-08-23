"""Presenter puro de la página de asignaturas/áreas (`/admin/asignaturas`).

Sin import de NiceGUI. La validación (nombre, código, unicidad) vive en el
modelo/servicio; aquí el view-state es: filtro de área, búsqueda de texto (con su
predicado client-side) y los dos formularios de creación (área y asignatura) con
sus resets.
"""
from __future__ import annotations

from typing import ClassVar


class AsignaturasPresenter:
    """View-model de asignaturas: filtros + búsqueda + formularios."""

    _AREA_FORM_DEFAULTS: ClassVar[dict] = {"area_nombre": "", "area_codigo": ""}
    _ASIG_FORM_DEFAULTS: ClassVar[dict] = {
        "asig_nombre": "",
        "asig_codigo": "",
        "asig_area_id": None,
    }

    def __init__(self) -> None:
        self.estado: dict = {
            "areas": [],
            "asignaturas": [],
            "area_filtro_id": None,
            "busqueda": "",
            **dict(self._AREA_FORM_DEFAULTS),
            **dict(self._ASIG_FORM_DEFAULTS),
        }

    # ── Datos cargados ──────────────────────────────────────────────────────

    def set_areas(self, areas) -> None:
        self.estado["areas"] = list(areas)

    def set_asignaturas(self, asignaturas) -> None:
        self.estado["asignaturas"] = list(asignaturas)

    # ── Filtros ─────────────────────────────────────────────────────────────

    def set_area_filtro(self, valor) -> None:
        self.estado["area_filtro_id"] = valor

    def set_busqueda(self, valor) -> None:
        self.estado["busqueda"] = (valor or "").strip().lower()

    def filtrar(self, asignaturas) -> list:
        """Aplica la búsqueda de texto (nombre o código) sobre la lista dada."""
        q = self.estado["busqueda"]
        if not q:
            return list(asignaturas)
        return [a for a in asignaturas if q in a.nombre.lower() or q in (a.codigo or "").lower()]

    # ── Formularios ─────────────────────────────────────────────────────────

    def reset_area_form(self) -> None:
        self.estado.update(self._AREA_FORM_DEFAULTS)

    def reset_asig_form(self) -> None:
        self.estado.update(self._ASIG_FORM_DEFAULTS)


__all__ = ["AsignaturasPresenter"]
