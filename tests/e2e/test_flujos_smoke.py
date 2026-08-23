"""Smoke e2e headless: la app arranca contra la BD sembrada y sirve rutas reales.

Recorre guard→página→(servicio/repo) de verdad, sin navegador. Este primer flujo
es el público (`/`), que no requiere sesión.
"""
from __future__ import annotations

import pytest
from nicegui.testing import User

pytestmark = [pytest.mark.e2e, pytest.mark.nicegui_main_file("tests/e2e/e2e_app.py")]


async def test_landing_publica_renderiza(user: User) -> None:
    await user.open("/")
    # La landing es PÚBLICA: no redirige a login y muestra su marca.
    await user.should_see("Gestor Docente")
