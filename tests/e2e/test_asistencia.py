"""e2e headless — flujo de registro de asistencia (uitest_06).

Recorre login → guard → página `/asistencia` → servicios de verdad (sin
navegador). Verifica dos caminos:
  - Un rol de aula autorizado (director) alcanza la página y ve su selector.
  - El admin de plataforma (denegado en `/asistencia` por el guard) es redirigido
    a `/inicio`.

Nota de alcance: el marcado masivo + guardado completo exige conducir los menús
del selector inline (grupo/asignatura no se auto-preseleccionan); queda como
endurecimiento posterior (requiere marks de test en el selector). Este smoke ya
ejercita guard→página→servicio de punta a punta.
"""
from __future__ import annotations

import pytest
from nicegui.testing import User

pytestmark = [pytest.mark.e2e, pytest.mark.nicegui_main_file("tests/e2e/e2e_app.py")]

_INICIO = "Bienvenido al portal de gestión docente."


async def _login(user: User, usuario: str, password: str) -> None:
    await user.open("/login")
    user.find(marker="login-usuario").type(usuario)
    user.find(marker="login-password").type(password)
    user.find(marker="login-submit").click()
    await user.should_see(_INICIO)


async def test_asistencia_render_para_rol_de_aula(user: User) -> None:
    """Director (rol de aula) alcanza /asistencia y ve el selector de la página."""
    await _login(user, "director", "Director2025*")
    await user.open("/asistencia")
    # El selector inline de la página muestra el pill "Asignatura" (placeholder).
    await user.should_see("Asignatura")
    # No fue redirigido a /inicio: sigue en la página de asistencia.
    await user.should_not_see(_INICIO)


async def test_asistencia_denegada_para_admin(user: User) -> None:
    """Admin de plataforma: el guard deniega /asistencia y redirige a /inicio."""
    await _login(user, "admin", "Admin2025*")
    await user.open("/asistencia")
    await user.should_see(_INICIO)
