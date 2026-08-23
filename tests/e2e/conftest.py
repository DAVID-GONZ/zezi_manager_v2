"""Fixtures e2e.

El plugin headless de NiceGUI (`nicegui.testing.user_plugin`, que aporta el
fixture `user`) se declara en el conftest RAÍZ (`tests/conftest.py`), porque
pytest prohíbe `pytest_plugins` en conftests anidados. El entrypoint sembrado
vive en `tests/e2e/e2e_app.py`; cada test lo apunta con el marker
`@pytest.mark.nicegui_main_file("tests/e2e/e2e_app.py")`.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _aislar_estado_nicegui():
    """Restaura el estado global de NiceGUI a "pristino" tras cada test e2e.

    La simulación arranca el ciclo de vida de la app (`app.is_started`) y crea
    clientes; si eso queda vivo, los tests de componentes que renderizan al vuelo
    (`with ui.card(): ...`) fallan porque el auto-pseudo-cliente de NiceGUI solo
    se crea cuando `not app.is_started and not script_mode and not Client.instances`
    (ver nicegui/context.py). Este teardown los deja como el resto del suite espera.
    """
    yield
    import contextlib

    from nicegui import core
    from nicegui.client import Client

    core.script_mode = False
    core.script_client = None
    Client.instances.clear()
    # `is_started` es interno; si NiceGUI cambia y deja de ser asignable, no
    # queremos romper el suite por ello.
    with contextlib.suppress(Exception):
        core.app.is_started = False
