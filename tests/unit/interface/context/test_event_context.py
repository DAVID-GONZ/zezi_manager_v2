"""Tests guardarrail del interceptor global de tenant en event handlers."""

from unittest.mock import MagicMock, patch

import pytest
from nicegui.client import Client

import src.interface.context.event_context as mod


@pytest.fixture(autouse=True)
def _reset_interceptor():
    """Restaura Client.handle_event y el sentinel del módulo entre tests."""
    original_method = Client.handle_event
    original_sentinel = mod._original_handle_event
    yield
    Client.handle_event = original_method
    mod._original_handle_event = original_sentinel


def _fresh_install():
    """Instala el interceptor partiendo de estado limpio."""
    mod._original_handle_event = None
    from src.interface.context.event_context import instalar_interceptor_tenant

    instalar_interceptor_tenant()


def test_interceptor_reemplaza_handle_event():
    original = Client.handle_event
    _fresh_install()
    assert Client.handle_event is not original


def test_interceptor_llama_desde_storage():
    _fresh_install()

    fake_client = MagicMock(spec=Client)
    fake_msg = {"id": "elem-1", "args": []}

    with (
        patch("src.interface.context.session_context.SessionContext.desde_storage") as mock_ds,
        patch.object(mod, "_original_handle_event") as mock_orig,
    ):
        mock_ds.return_value = None
        Client.handle_event(fake_client, fake_msg)

    mock_ds.assert_called_once()
    mock_orig.assert_called_once_with(fake_client, fake_msg)


def test_interceptor_ignora_runtimeerror_fuera_de_ui_context():
    _fresh_install()

    fake_client = MagicMock(spec=Client)
    fake_msg = {"id": "elem-2", "args": []}

    with (
        patch(
            "src.interface.context.session_context.SessionContext.desde_storage",
            side_effect=RuntimeError("app.storage.user can only be used within a UI context"),
        ),
        patch.object(mod, "_original_handle_event") as mock_orig,
    ):
        Client.handle_event(fake_client, fake_msg)

    mock_orig.assert_called_once_with(fake_client, fake_msg)


def test_interceptor_es_idempotente():
    _fresh_install()
    wrapper_primera = Client.handle_event

    from src.interface.context.event_context import instalar_interceptor_tenant

    instalar_interceptor_tenant()
    wrapper_segunda = Client.handle_event

    assert wrapper_primera is wrapper_segunda
