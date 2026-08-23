"""Presenter puro de configuración de alertas (`/convivencia/configuracion-alertas`).

Página de configuración fina: el guardado y la validación (umbral, tipo) viven en
`alerta_service`/el modelo. El único view-state es el año activo y las
configuraciones cargadas por tipo. Sin import de NiceGUI.
"""
from __future__ import annotations


class ConfiguracionAlertasPresenter:
    """View-model de configuración de alertas (año activo + configs por tipo)."""

    def __init__(self) -> None:
        self.estado: dict = {"anio_id": None, "anio_nombre": "", "configs": {}}

    def set_anio(self, anio_id, anio_nombre: str = "") -> None:
        self.estado["anio_id"] = anio_id
        self.estado["anio_nombre"] = anio_nombre

    def set_configs(self, configs: dict) -> None:
        self.estado["configs"] = dict(configs)

    def limpiar(self) -> None:
        self.estado["anio_id"] = None
        self.estado["configs"] = {}


__all__ = ["ConfiguracionAlertasPresenter"]
