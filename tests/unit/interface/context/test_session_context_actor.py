"""
Tests unitarios para la siembra del actor en SessionContext.desde_storage()
(obs_01 — T6).

Mockea app.storage.user para no necesitar NiceGUI en ejecución.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.contexto_actor import actor_actual, limpiar_actor


def _make_storage(**kwargs):
    """Devuelve un dict-like mock de app.storage.user."""
    defaults = {
        "autenticado": True,
        "usuario_id": 10,
        "usuario_nombre": "Test",
        "usuario_rol": "director",
        "solo_lectura": False,
        "impersonando": False,
        "admin_real_id": None,
    }
    defaults.update(kwargs)
    storage = MagicMock()
    storage.get.side_effect = lambda k, default=None: defaults.get(k, default)
    return storage


def test_desde_storage_siembra_usuario_id_como_actor():
    """Sin impersonación, actor_actual() debe coincidir con usuario_id."""
    limpiar_actor()
    storage = _make_storage(usuario_id=10, impersonando=False)

    with patch("src.interface.context.session_context.app") as mock_app:
        mock_app.storage.user = storage
        from src.interface.context.session_context import SessionContext
        SessionContext.desde_storage()

    assert actor_actual() == 10
    limpiar_actor()


def test_desde_storage_bajo_impersonacion_usa_admin_real():
    """Bajo impersonación, actor_actual() debe ser admin_real_id, no usuario_id."""
    limpiar_actor()
    # usuario_id = 99 (usuario objetivo), admin_real_id = 1 (admin real)
    storage = _make_storage(usuario_id=99, impersonando=True, admin_real_id=1)

    with patch("src.interface.context.session_context.app") as mock_app:
        mock_app.storage.user = storage
        from src.interface.context.session_context import SessionContext
        SessionContext.desde_storage()

    assert actor_actual() == 1  # el admin real, no el suplantado
    limpiar_actor()
