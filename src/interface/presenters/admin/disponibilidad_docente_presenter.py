"""Presenter puro de disponibilidad docente (`/admin/disponibilidad-docente`).

Sin import de NiceGUI. Guarda el view-state (docente seleccionado, rejilla de
disponibilidad por franja, límites) y la transición de toggle de cada celda. La
carga de la plantilla y la persistencia se quedan en la página.
"""
from __future__ import annotations


class DisponibilidadDocentePresenter:
    """View-model de disponibilidad docente: selección + rejilla de slots."""

    def __init__(self) -> None:
        self.estado: dict = {
            "docentes": [],
            "docente_id": None,
            "franjas": [],
            "dias_activos": [],
            "disponibilidad": {},  # {(dia, orden): bool} — True = disponible
            "min_horas_dia": 0,
            "max_horas_dia": 8,
            "plantilla_ok": True,
        }

    def set_docente(self, valor) -> None:
        self.estado["docente_id"] = valor

    def set_docentes(self, docentes) -> None:
        self.estado["docentes"] = list(docentes)

    def toggle_slot(self, clave) -> None:
        """Alterna disponible/no-disponible de una celda (por defecto disponible)."""
        self.estado["disponibilidad"][clave] = not self.estado["disponibilidad"].get(clave, True)


__all__ = ["DisponibilidadDocentePresenter"]
