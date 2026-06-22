"""
conftest.py — Fixtures de la capa de interfaz.

`registro_rutas` puebla el registro central `ruta → roles` (paso_35) llamando
a `main.registrar_rutas_ui()` una sola vez por sesión. El NAV y los tests de
autorización derivan su comportamiento de ese registro, así que necesitan que
esté poblado (de lo contrario, deny-by-default lo deja vacío).
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def registro_rutas():
    """
    Registra todas las rutas de la app en el registro central de autorización.

    `registrar_pagina` aplica `@ui.page` (sin servidor, idempotente para
    registro de rutas) y puebla el registro consultado por `roles_de_ruta`.
    Autouse: cualquier test de la capa de interfaz tiene el registro listo.
    """
    import main

    main.registrar_rutas_ui()
    from src.interface.auth import rutas_registradas

    return rutas_registradas()
