"""
Tests de aislamiento de solo lectura — tenant_04_tests_aislamiento (Fase 1C).

Verifica la cadena de sincronización entre SessionContext._sincronizar_solo_lectura
y el ContextVar de la capa de servicios, sin depender de app.storage.user
(que requiere contexto NiceGUI).
"""
from __future__ import annotations

import pytest

from src.interface.context.session_context import SessionContext
from src.services.solo_lectura import activar_solo_lectura, es_solo_lectura


@pytest.fixture(autouse=True)
def _reset_solo_lectura():
    """Cada test arranca y termina con solo_lectura=False."""
    activar_solo_lectura(False)
    yield
    activar_solo_lectura(False)


def test_solo_lectura_default_es_false() -> None:
    """El ContextVar arranca en False (no impersonando)."""
    assert es_solo_lectura() is False


def test_sincronizar_solo_lectura_activa() -> None:
    """_sincronizar_solo_lectura(True) activa el modo solo lectura en servicios."""
    SessionContext._sincronizar_solo_lectura(True)
    assert es_solo_lectura() is True


def test_sincronizar_solo_lectura_desactiva() -> None:
    """_sincronizar_solo_lectura(False) desactiva el modo solo lectura en servicios."""
    activar_solo_lectura(True)
    SessionContext._sincronizar_solo_lectura(False)
    assert es_solo_lectura() is False
