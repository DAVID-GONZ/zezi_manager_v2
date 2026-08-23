"""Presenter puro de la página de alertas (`/convivencia/alertas`).

Sin import de NiceGUI. Guarda el estado de los filtros y la lista cargada, sus
transiciones, y helpers de vista: la normalización de la clave de nivel (para
sortear la representación `str(enum)`) y el cálculo de los KPIs de cabecera. La
carga (Container/servicio) y el render se quedan en la página.
"""
from __future__ import annotations


class AlertasPresenter:
    """View-model de la página de alertas (filtros + lista + KPIs)."""

    def __init__(self) -> None:
        self.estado: dict = {
            "alertas": [],
            "filtro_tipo": None,
            "filtro_nivel": None,
            "solo_pendientes": True,
            "nombres": {},  # cache est_id → nombre (lo puebla la página)
        }

    # ── Transiciones de filtros ─────────────────────────────────────────────

    def set_tipo(self, valor) -> None:
        self.estado["filtro_tipo"] = valor or None

    def set_nivel(self, valor) -> None:
        self.estado["filtro_nivel"] = valor or None

    def set_pendientes(self, valor) -> None:
        self.estado["solo_pendientes"] = bool(valor)

    def set_alertas(self, alertas) -> None:
        self.estado["alertas"] = list(alertas)

    # ── Helpers de vista ────────────────────────────────────────────────────

    @staticmethod
    def nivel_clave(nivel) -> str:
        """Normaliza el nivel a su clave en minúsculas ('critica', 'advertencia',
        'info'), tolerando tanto 'critica' como 'NivelAlerta.critica'."""
        texto = str(nivel)
        return (texto.split(".")[-1] if "." in texto else texto).lower()

    @classmethod
    def kpis(cls, alertas) -> dict:
        """Contadores de cabecera (resumen de la lista cargada)."""
        return {
            "total": len(alertas),
            "criticas": sum(1 for a in alertas if cls.nivel_clave(a.nivel) == "critica"),
            "pendientes": sum(1 for a in alertas if not a.resuelta),
        }


__all__ = ["AlertasPresenter"]
