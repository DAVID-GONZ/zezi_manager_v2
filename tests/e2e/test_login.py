"""e2e headless — flujo de login (uitest_05).

Conduce el formulario real de `/login` con el fixture `user` y verifica el
recorrido completo login → SessionContext → guard → `/inicio`. Las credenciales
provienen del seed (`seed_dev`, bcrypt real): admin / Admin2025*.
"""
from __future__ import annotations

import pytest
from nicegui.testing import User

pytestmark = [pytest.mark.e2e, pytest.mark.nicegui_main_file("tests/e2e/e2e_app.py")]

# Texto siempre presente en /inicio (greeting_hero).
_INICIO = "Bienvenido al portal de gestión docente."


async def test_login_exitoso_lleva_a_inicio(user: User) -> None:
    await user.open("/login")
    user.find(marker="login-usuario").type("admin")
    user.find(marker="login-password").type("Admin2025*")
    user.find(marker="login-submit").click()
    await user.should_see(_INICIO)


async def test_login_credenciales_invalidas_muestra_error(user: User) -> None:
    await user.open("/login")
    user.find(marker="login-usuario").type("admin")
    user.find(marker="login-password").type("clave-incorrecta")
    user.find(marker="login-submit").click()
    await user.should_see("Usuario o contraseña incorrectos.")
    await user.should_not_see(_INICIO)


async def test_login_campos_vacios_pide_completar(user: User) -> None:
    await user.open("/login")
    user.find(marker="login-submit").click()
    await user.should_see("Completa usuario y contraseña.")
