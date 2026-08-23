"""Presenter puro de configuración SIE (`/admin/configuracion`).

Sin import de NiceGUI. Guarda el view-state (año activo, niveles, criterios,
config SIEE) y dos consultas de vista: el id del año activo y el modo SIEE actual.
La carga y la persistencia viven en los servicios.
"""
from __future__ import annotations


class ConfiguracionSiePresenter:
    """View-model de configuración SIE."""

    def __init__(self) -> None:
        self.estado: dict = {
            "config_activa": None,
            "nuevo_anio": 2026,
            "niveles": [],
            "criterios": None,
            "siee_cfg": None,
            "cats_inst": [],
        }

    def anio_id(self) -> int | None:
        cfg = self.estado["config_activa"]
        return cfg.id if cfg else None

    def modo_actual(self) -> str:
        cfg = self.estado["siee_cfg"]
        return cfg.modo.value if cfg else "libre"


__all__ = ["ConfiguracionSiePresenter"]
