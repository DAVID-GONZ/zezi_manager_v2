"""e2e headless — aislamiento multi-tenant a través de la UI (uitest_09).

`seed_dev` siembra DOS instituciones. Al hacer login, el director queda scopeado a
su institución (SessionContext → contexto_tenant). El listado de usuarios lo
auto-scopea el servicio, así que el director de la institución #1 ve a los suyos y
NUNCA al director de la #2 — aunque exista en la BD. Esa ausencia prueba el
aislamiento tenant end-to-end.

Se prueba la dirección #1 (institución plenamente configurada). El director de la
#2 cae en el gate de configuración inicial (institución sin configurar en el seed),
por lo que no es un buen sujeto de navegación. El rechazo de operar por id ajeno
(`OperacionFueraDeInstitucionError`) está cubierto a nivel de servicio/integración
(test_aislamiento_objeto_paso36, test_estudiante_service::test_aislamiento_institucion).
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


async def test_director_ve_solo_usuarios_de_su_institucion(user: User) -> None:
    await _login(user, "director", "Director2025*")

    await user.open("/admin/usuarios")
    # Ve al director de SU institución (nombre propio del seed de la institución #1)…
    await user.should_see("María Elena")
    # …y NUNCA al director de la otra institución (aislamiento tenant en el servicio).
    await user.should_not_see("Institución de Prueba")
