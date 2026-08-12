"""
src/interface/pages/convivencia/comportamiento.py
=================================================
Delegate de compatibilidad — ZECI Manager v2.0 (convivencia_26_rutas_rail).

`comportamiento` dejó de ser una página propia tras la reorganización de
convivencia: su lectura vive en el hub de Seguimiento y su creación en
Observaciones. Esta página se conserva solo como redirect para no romper
enlaces existentes a `/convivencia/comportamiento`.

Regla de capas:
  Esta página NO importa ningún símbolo de src.domain.models.*
"""
from __future__ import annotations

from nicegui import ui

from src.interface.context.session_context import SessionContext


# page-delegate: ruta y guard de rol registrados en main.py (paso_35).
def comportamiento_page() -> None:
    """Guard de sesión y redirect al hub de Seguimiento."""
    ctx = SessionContext.desde_storage()
    if not ctx:
        ui.navigate.to("/login")
        return
    ui.navigate.to("/convivencia/seguimiento")


__all__ = ["comportamiento_page"]
