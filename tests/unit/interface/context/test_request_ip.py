"""
Tests unitarios para src/interface/context/request_ip.py (obs_06 — T4).

Cubre:
  (a) X-Forwarded-For con varios saltos → devuelve el primer salto.
  (b) Sin cabecera pero con client.host → devuelve el host.
  (c) Sin nada → devuelve None y emite warning (R2, R3).

Los tests (a) y (b) fallan si el resultado es None (R3).
"""
from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.interface.context.request_ip import _de_request

# ---------------------------------------------------------------------------
# Dobles de petición
# ---------------------------------------------------------------------------

def _request_con_forwarded(header: str) -> MagicMock:
    """Petición con X-Forwarded-For."""
    req = MagicMock()
    req.headers.get = lambda k, default="": header if k == "X-Forwarded-For" else default
    req.client = None
    return req


def _request_con_host(host: str) -> MagicMock:
    """Petición sin X-Forwarded-For pero con client.host."""
    req = MagicMock()
    req.headers.get = lambda k, default="": "" if k == "X-Forwarded-For" else default
    req.client = SimpleNamespace(host=host)
    return req


def _request_vacio() -> MagicMock:
    """Petición sin cabecera X-Forwarded-For ni client.host."""
    req = MagicMock()
    req.headers.get = lambda k, default="": "" if k == "X-Forwarded-For" else default
    req.client = None
    return req


# ---------------------------------------------------------------------------
# (a) X-Forwarded-For — varios saltos
# ---------------------------------------------------------------------------

def test_de_request_xforwardedfor_un_salto():
    """Un solo salto en X-Forwarded-For → devuelve esa IP."""
    req = _request_con_forwarded("203.0.113.5")
    result = _de_request(req)
    assert result == "203.0.113.5", "No debe devolver None ante X-Forwarded-For"


def test_de_request_xforwardedfor_varios_saltos():
    """Varios saltos en X-Forwarded-For → devuelve el primero (el cliente real)."""
    req = _request_con_forwarded("203.0.113.5, 10.0.0.1, 192.168.1.1")
    result = _de_request(req)
    assert result == "203.0.113.5", "Debe devolver el primer salto, no None"


def test_de_request_xforwardedfor_con_espacios():
    """X-Forwarded-For con espacios adicionales → devuelve IP sin espacios."""
    req = _request_con_forwarded("  198.51.100.1  , 10.0.0.2")
    result = _de_request(req)
    assert result == "198.51.100.1"


# ---------------------------------------------------------------------------
# (b) client.host sin X-Forwarded-For
# ---------------------------------------------------------------------------

def test_de_request_client_host():
    """Sin X-Forwarded-For pero con client.host → devuelve el host."""
    req = _request_con_host("192.168.0.10")
    result = _de_request(req)
    assert result == "192.168.0.10", "No debe devolver None cuando client.host existe"


def test_de_request_localhost():
    """client.host = 127.0.0.1 → devuelve '127.0.0.1'."""
    req = _request_con_host("127.0.0.1")
    result = _de_request(req)
    assert result == "127.0.0.1"


# ---------------------------------------------------------------------------
# (c) Sin nada → None y warning
# ---------------------------------------------------------------------------

def test_de_request_sin_ip_devuelve_none():
    """Sin X-Forwarded-For ni client.host → _de_request devuelve None."""
    req = _request_vacio()
    result = _de_request(req)
    assert result is None


def test_ip_de_peticion_sin_contexto_emite_warning(caplog):
    """
    ip_de_peticion() sin contexto NiceGUI debe emitir warning y devolver None.

    No accedemos al módulo nicegui real — la función maneja la excepción
    internamente y emite el warning esperado.
    """
    from src.interface.context.request_ip import ip_de_peticion

    with caplog.at_level(logging.WARNING, logger="INTERFACE.REQUEST_IP"):
        result = ip_de_peticion()

    # En entorno de test sin NiceGUI, debe retornar None
    assert result is None
    # Debe haber emitido al menos un warning
    assert any("IP no resuelta" in r.message for r in caplog.records), (
        "Se esperaba un warning 'IP no resuelta' pero no se encontró"
    )
