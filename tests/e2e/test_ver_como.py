"""e2e headless — impersonación "Ver como" (uitest_10).

El admin de plataforma (scope cross-tenant) impersona a un director desde
`/admin/usuarios`. Tras `iniciar_ver_como`, la sesión pasa a **solo lectura** y
scope de la institución del director; el layout muestra el banner persistente
"Estás viendo como … solo lectura". El botón "Salir" revierte a admin.

La lógica de scope/solo-lectura de `SessionContext.iniciar_ver_como` /
`salir_ver_como` está cubierta en unidad; aquí se verifica el recorrido a través
de la UI real (banner + salida).
"""
from __future__ import annotations

import pytest
from nicegui.testing import User

pytestmark = [pytest.mark.e2e, pytest.mark.nicegui_main_file("tests/e2e/e2e_app.py")]

_INICIO = "Bienvenido al portal de gestión docente."
_BANNER = "Estás viendo como"


async def _login(user: User, usuario: str, password: str) -> None:
    await user.open("/login")
    user.find(marker="login-usuario").type(usuario)
    user.find(marker="login-password").type(password)
    user.find(marker="login-submit").click()
    await user.should_see(_INICIO)


async def test_admin_ver_como_director_y_salir(user: User) -> None:
    await _login(user, "admin", "Admin2025*")

    # 1. El admin ve al director en el listado y lo impersona.
    await user.open("/admin/usuarios")
    await user.should_see("María Elena")
    user.find(marker="ver-como-director").click()

    # 2. Impersonando: banner persistente de solo-lectura.
    await user.should_see(_BANNER)
    await user.should_see("solo lectura")

    # 3. "Salir" revierte la impersonación.
    user.find("Salir").click()
    await user.should_not_see(_BANNER)
