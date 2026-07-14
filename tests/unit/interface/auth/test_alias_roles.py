"""
test_alias_roles.py — Guardarraíl de coherencia de roles en alias de redirección
(mejora_04_enrutado_roles).

Convención: un alias de redirección hereda los roles de su ruta destino. Así el
guard central decide la autorización UNA sola vez (en el alias) en vez de rebotar
redirección→denegación cuando el destino es más restrictivo.

Para cada alias de redirección conocido, este test verifica sobre el registro
central (`rutas_registradas()` / `roles_de_ruta()`), poblado por el fixture
autouse `registro_rutas` que importa y ejecuta `main.registrar_rutas_ui()`:

  (a) el destino está registrado (R4), y
  (b) roles(alias) == roles(destino) (R1).
"""
from __future__ import annotations

import pytest

from src.interface.auth import roles_de_ruta, rutas_registradas

# Alias de redirección → ruta destino (definidos en main.registrar_rutas_ui()).
ALIASES_REDIRECCION = {
    "/informes": "/informes/estadisticos",
    "/evaluacion/cierre": "/evaluacion/cierre-periodo",
}


@pytest.mark.parametrize(
    ("alias", "destino"),
    list(ALIASES_REDIRECCION.items()),
)
def test_alias_hereda_roles_del_destino(alias: str, destino: str):
    registro = rutas_registradas()

    assert alias in registro, f"alias {alias} no está registrado"
    # R4: el destino de un alias debe existir en el registro.
    assert destino in registro, (
        f"destino {destino} del alias {alias} no está registrado (R4)"
    )
    # R1: el alias hereda EXACTAMENTE los roles de su destino.
    assert roles_de_ruta(alias) == roles_de_ruta(destino), (
        f"roles({alias})={roles_de_ruta(alias)!r} != "
        f"roles({destino})={roles_de_ruta(destino)!r} (R1)"
    )
