"""e2e headless — matriz RBAC ejecutada en la UI real (uitest_08).

Para cada rol se hace login real y se abren rutas representativas, verificando el
guard EJECUTÁNDOSE (no `decidir_acceso` en aislamiento): una ruta permitida rinde
su página (no vuelve a /inicio); una denegada redirige a /inicio.

Los veredictos son el espejo de la tabla declarada en
`tests/unit/interface/auth/test_matriz_rutas_completa.py` (uitest_07); aquí se
comprueban a través del navegador headless.
"""
from __future__ import annotations

import pytest
from nicegui.testing import User

pytestmark = [pytest.mark.e2e, pytest.mark.nicegui_main_file("tests/e2e/e2e_app.py")]

_INICIO = "Bienvenido al portal de gestión docente."

# Rutas representativas con veredicto por rol (True = permitida, False = denegada).
# Derivadas de ACCESO_ESPERADO (guard). Se eligen las que más diferencian roles.
_RUTAS = [
    "/admin/usuarios",           # admin + director
    "/admin/auditoria",          # solo admin
    "/horarios",                 # aula (director/coordinador/profesor)
    "/estudiantes",              # aula
    "/evaluacion/configuracion",  # solo profesor
]

_MATRIZ: dict[str, tuple[str, str, dict[str, bool]]] = {
    # rol: (usuario, password, {ruta: permitida})
    "admin": ("admin", "Admin2025*", {
        "/admin/usuarios": True, "/admin/auditoria": True,
        "/horarios": False, "/estudiantes": False, "/evaluacion/configuracion": False,
    }),
    "director": ("director", "Director2025*", {
        "/admin/usuarios": True, "/admin/auditoria": False,
        "/horarios": True, "/estudiantes": True, "/evaluacion/configuracion": False,
    }),
    "coordinador": ("coordinador", "Coord2025*", {
        "/admin/usuarios": False, "/admin/auditoria": False,
        "/horarios": True, "/estudiantes": True, "/evaluacion/configuracion": False,
    }),
    "profesor": ("rgomez", "Pass2025*", {
        "/admin/usuarios": False, "/admin/auditoria": False,
        "/horarios": True, "/estudiantes": True, "/evaluacion/configuracion": True,
    }),
}


async def _login(user: User, usuario: str, password: str) -> None:
    await user.open("/login")
    user.find(marker="login-usuario").type(usuario)
    user.find(marker="login-password").type(password)
    user.find(marker="login-submit").click()
    await user.should_see(_INICIO)


@pytest.mark.parametrize("rol", list(_MATRIZ))
async def test_matriz_rbac_por_rol(user: User, rol: str) -> None:
    usuario, password, veredictos = _MATRIZ[rol]
    await _login(user, usuario, password)

    for ruta in _RUTAS:
        permitida = veredictos[ruta]
        await user.open(ruta)
        if permitida:
            # Rindió la página destino: NO fue redirigido a /inicio.
            await user.should_not_see(_INICIO)
        else:
            # El guard denegó y redirigió a /inicio.
            await user.should_see(_INICIO)
