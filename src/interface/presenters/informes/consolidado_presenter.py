"""Presenter puro de los informes consolidados (`/informes/consolidado-*`).

Compartido por consolidado_notas y consolidado_asistencia, que tienen el mismo
view-state: selectores (grupo/asignación/periodo/formato) con cascada de reseteos
al cambiar de grupo, y dos fechas parseadas desde ISO. Sin import de NiceGUI. La
generación del informe (DTO + servicio) se queda en cada página.
"""
from __future__ import annotations

import contextlib
from datetime import date


class ConsolidadoInformePresenter:
    """View-model de los filtros de un informe consolidado."""

    def __init__(self) -> None:
        self.estado: dict = {
            "grupo_id": None,
            "asignacion_id": None,
            "periodo_id": None,
            "fecha_desde": None,
            "fecha_hasta": None,
            "formato": "excel",
            "grupos": [],
            "asignaciones": [],
            "periodos": [],
        }

    # ── Transiciones de selectores ──────────────────────────────────────────

    def set_grupo(self, valor) -> None:
        """Cambiar de grupo resetea asignación y periodo (dependen del grupo)."""
        self.estado.update({"grupo_id": valor, "asignacion_id": None, "periodo_id": None})

    def set_asignacion(self, valor) -> None:
        self.estado["asignacion_id"] = valor

    def set_periodo(self, valor) -> None:
        self.estado["periodo_id"] = valor

    def set_formato(self, valor) -> None:
        self.estado["formato"] = valor

    # ── Fechas (ISO → date; entrada inválida conserva el valor previo) ──────

    def set_fecha_desde(self, valor: str) -> None:
        self._set_fecha("fecha_desde", valor)

    def set_fecha_hasta(self, valor: str) -> None:
        self._set_fecha("fecha_hasta", valor)

    def _set_fecha(self, clave: str, valor: str) -> None:
        if not valor:
            self.estado[clave] = None
            return
        # Entrada inválida → se conserva el valor anterior.
        with contextlib.suppress(ValueError):
            self.estado[clave] = date.fromisoformat(valor)

    # ── Predicado ───────────────────────────────────────────────────────────

    def filtros_completos(self) -> bool:
        e = self.estado
        return all(
            [e["grupo_id"], e["asignacion_id"], e["periodo_id"], e["fecha_desde"], e["fecha_hasta"]]
        )


__all__ = ["ConsolidadoInformePresenter"]
