"""
Tests de la política alerta_ip (obs_03).

Cubre:
  - Fallos se acumulan por IP.
  - Al superar MAX_FALLOS_IP se emite advertencia al logger zeci.security.
  - IP vacía se ignora.
  - La ventana expira y los fallos se reinician.
  - reset_ip limpia solo la IP especificada.
  - reset_all limpia todo el estado.
"""
from __future__ import annotations

import logging
import time

import pytest

import src.domain.policies.alerta_ip as alerta_ip_module
from src.domain.policies.alerta_ip import (
    MAX_FALLOS_IP,
    VENTANA_SEGUNDOS,
    registrar_fallo_ip,
    reset_all,
    reset_ip,
)


@pytest.fixture(autouse=True)
def limpiar_estado():
    """Limpia el estado global de alerta_ip antes de cada test."""
    reset_all()
    yield
    reset_all()


# ---------------------------------------------------------------------------
# Tests básicos
# ---------------------------------------------------------------------------

def test_ip_vacia_ignorada():
    """Una IP vacía no debe generar errores ni estado."""
    registrar_fallo_ip("")
    registrar_fallo_ip("   ")
    # Sin error: OK


def test_fallos_acumulan():
    """Los fallos se acumulan en el estado interno."""
    for _ in range(MAX_FALLOS_IP - 1):
        registrar_fallo_ip("10.0.0.1")
    estado = alerta_ip_module._estados.get("10.0.0.1")
    assert estado is not None
    assert estado.fallos == MAX_FALLOS_IP - 1


def test_alerta_emitida_al_superar_umbral():
    """Al alcanzar MAX_FALLOS_IP, se emite una advertencia al logger."""
    records: list[logging.LogRecord] = []

    class Cap(logging.Handler):
        def emit(self, r):
            records.append(r)

    h = Cap()
    alerta_ip_module._logger.addHandler(h)
    logging.disable(logging.NOTSET)  # Rehabilitar logs (conftest los silencia)
    try:
        for _ in range(MAX_FALLOS_IP):
            registrar_fallo_ip("192.168.1.1")

        alertas = [r for r in records if getattr(r, "tipo_evento", None) == "ALERTA_IP"]
        assert len(alertas) >= 1
        alerta = alertas[0]
        assert alerta.levelno == logging.WARNING
        assert getattr(alerta, "ip") == "192.168.1.1"
    finally:
        alerta_ip_module._logger.removeHandler(h)
        logging.disable(logging.CRITICAL)


def test_alerta_NO_emitida_antes_del_umbral():
    """Antes de alcanzar MAX_FALLOS_IP no se emite alerta."""
    records: list[logging.LogRecord] = []

    class Cap(logging.Handler):
        def emit(self, r):
            records.append(r)

    h = Cap()
    alerta_ip_module._logger.addHandler(h)
    logging.disable(logging.NOTSET)
    try:
        for _ in range(MAX_FALLOS_IP - 1):
            registrar_fallo_ip("172.16.0.1")
        alertas = [r for r in records if getattr(r, "tipo_evento", None) == "ALERTA_IP"]
        assert len(alertas) == 0
    finally:
        alerta_ip_module._logger.removeHandler(h)
        logging.disable(logging.CRITICAL)


def test_ips_distintas_no_interfieren():
    """Dos IPs diferentes llevan contadores independientes."""
    for _ in range(MAX_FALLOS_IP - 1):
        registrar_fallo_ip("10.0.0.1")
        registrar_fallo_ip("10.0.0.2")

    estado_1 = alerta_ip_module._estados.get("10.0.0.1")
    estado_2 = alerta_ip_module._estados.get("10.0.0.2")
    assert estado_1.fallos == MAX_FALLOS_IP - 1
    assert estado_2.fallos == MAX_FALLOS_IP - 1


def test_reset_ip_limpia_solo_esa_ip():
    """reset_ip limpia el estado de una IP sin afectar otras."""
    for _ in range(MAX_FALLOS_IP - 1):
        registrar_fallo_ip("10.0.0.1")
        registrar_fallo_ip("10.0.0.2")

    reset_ip("10.0.0.1")
    assert alerta_ip_module._estados.get("10.0.0.1") is None
    assert alerta_ip_module._estados.get("10.0.0.2") is not None


def test_reset_all_limpia_todo():
    """reset_all vacía todo el estado."""
    for _ in range(2):
        registrar_fallo_ip("10.0.0.1")
        registrar_fallo_ip("10.0.0.2")

    reset_all()
    assert len(alerta_ip_module._estados) == 0


def test_ip_normalizada_strip():
    """IPs con espacios se normalizan correctamente."""
    registrar_fallo_ip("  10.0.0.1  ")
    assert "10.0.0.1" in alerta_ip_module._estados


def test_ventana_expira_y_contador_reinicia(monkeypatch):
    """Cuando la ventana expira, el contador se reinicia en el siguiente fallo."""
    # Registrar algunos fallos
    for _ in range(MAX_FALLOS_IP - 2):
        registrar_fallo_ip("10.0.0.99")

    estado = alerta_ip_module._estados["10.0.0.99"]
    # Simular que el primer fallo fue hace VENTANA_SEGUNDOS + 1
    estado.primer_fallo_en = time.monotonic() - (VENTANA_SEGUNDOS + 1)

    # El siguiente fallo debe reiniciar el contador
    registrar_fallo_ip("10.0.0.99")
    assert alerta_ip_module._estados["10.0.0.99"].fallos == 1
