"""Presenter puro de registro de asistencia (`/asistencia`).

Sin import de NiceGUI. Guarda el view-state (fecha, registros/observaciones por
estudiante, selección) y las transiciones de marcado. La persistencia y el conteo
de clases viven en `asistencia_service`.
"""
from __future__ import annotations

from datetime import date


class RegistroAsistenciaPresenter:
    """View-model de registro de asistencia: marcado + selección + flag pendiente."""

    def __init__(self) -> None:
        self.estado: dict = {
            "fecha": date.today(),
            "registros": {},  # {estudiante_id: str_codigo}
            "observaciones": {},  # {estudiante_id: str}
            "estudiantes": [],
            "periodo_cerrado": False,
            "pendiente": False,
            # aliases actualizados por aplicar_seleccion
            "grupo_id": None,
            "asignacion_id": None,
            "periodo_id": None,
            # claves del selector inline
            "sel_periodo_id": None,
            "sel_periodo_nombre": "",
            "sel_grupo_id": None,
            "sel_grupo_nombre": "",
            "sel_asignacion_id": None,
            "sel_asignacion_nombre": "",
        }

    # ── Selección ───────────────────────────────────────────────────────────

    def aplicar_seleccion(self, seleccion: dict) -> None:
        """Copia grupo/asignación/periodo del selector a los alias de trabajo."""
        self.estado["grupo_id"] = seleccion["sel_grupo_id"]
        self.estado["asignacion_id"] = seleccion["sel_asignacion_id"]
        self.estado["periodo_id"] = seleccion["sel_periodo_id"]

    def set_fecha(self, fecha) -> None:
        self.estado["fecha"] = fecha

    # ── Marcado ─────────────────────────────────────────────────────────────

    def marcar(self, estudiante_id: int, estado: str) -> None:
        self.estado["registros"][estudiante_id] = estado
        self.estado["pendiente"] = True

    def marcar_todos(self, estado: str) -> None:
        for est in self.estado["estudiantes"]:
            self.estado["registros"][est.id] = estado
        self.estado["pendiente"] = True

    def set_obs(self, estudiante_id: int, texto: str) -> None:
        self.estado["observaciones"][estudiante_id] = texto


__all__ = ["RegistroAsistenciaPresenter"]
