"""Tests de src/domain/policies/severidad_evento.py (obs_07, T5).

Verifica la función pura severidad_de() para todos los casos relevantes.
"""
from __future__ import annotations

import pytest

from src.domain.models.auditoria import SeveridadEvento, TipoEventoSesion
from src.domain.policies.severidad_evento import (
    MOTIVO_CROSS_TENANT,
    MOTIVO_ROL,
    MOTIVO_SOLO_LECTURA,
    severidad_de,
)

# ── ACCESO_DENEGADO — variantes por motivo ───────────────────────────────────

@pytest.mark.parametrize(
    "motivo, esperada",
    [
        (MOTIVO_SOLO_LECTURA, SeveridadEvento.ADVERTENCIA),
        (MOTIVO_ROL, SeveridadEvento.ADVERTENCIA),
        (MOTIVO_CROSS_TENANT, SeveridadEvento.CRITICA),
        ("motivo_desconocido", SeveridadEvento.CRITICA),  # falla hacia el lado seguro
        (None, SeveridadEvento.CRITICA),                  # falla hacia el lado seguro
        ("", SeveridadEvento.CRITICA),                    # string vacío → seguro
    ],
)
def test_denegacion_por_motivo(motivo: str | None, esperada: SeveridadEvento) -> None:
    assert severidad_de(TipoEventoSesion.ACCESO_DENEGADO, motivo) is esperada


# ── Otros tipos de evento ────────────────────────────────────────────────────

def test_login_fallido_es_advertencia() -> None:
    assert severidad_de(TipoEventoSesion.LOGIN_FALLIDO) is SeveridadEvento.ADVERTENCIA


def test_login_fallido_ignora_motivo() -> None:
    """El motivo no afecta LOGIN_FALLIDO (es siempre ADVERTENCIA)."""
    assert severidad_de(TipoEventoSesion.LOGIN_FALLIDO, MOTIVO_CROSS_TENANT) is SeveridadEvento.ADVERTENCIA


def test_login_exitoso_es_info() -> None:
    assert severidad_de(TipoEventoSesion.LOGIN_EXITOSO) is SeveridadEvento.INFO


def test_logout_es_info() -> None:
    assert severidad_de(TipoEventoSesion.LOGOUT) is SeveridadEvento.INFO


def test_ver_como_inicio_es_info() -> None:
    assert severidad_de(TipoEventoSesion.VER_COMO_INICIO) is SeveridadEvento.INFO


def test_ver_como_fin_es_info() -> None:
    assert severidad_de(TipoEventoSesion.VER_COMO_FIN) is SeveridadEvento.INFO


def test_crear_usuario_es_info() -> None:
    assert severidad_de(TipoEventoSesion.CREAR_USUARIO) is SeveridadEvento.INFO


def test_editar_usuario_es_info() -> None:
    assert severidad_de(TipoEventoSesion.EDITAR_USUARIO) is SeveridadEvento.INFO
