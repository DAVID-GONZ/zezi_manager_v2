"""
src/interface/pages/convivencia/plantillas.py
=============================================
Delegate de compatibilidad — ZECI Manager v2.0 (convivencia_33).

La gestión de plantillas fue fusionada en la página unificada
`/convivencia/configuracion`. Esta página se conserva solo como redirect
para no romper enlaces existentes a `/convivencia/plantillas`.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
"""

from __future__ import annotations

from nicegui import ui

from src.interface.context.session_context import SessionContext


# page-delegate: ruta y guard de rol registrados en main.py
def plantillas_page() -> None:
    """Guard de sesión y redirect a la vista unificada de configuración."""
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return
    ui.navigate.to("/convivencia/configuracion")


__all__ = ["plantillas_page"]
