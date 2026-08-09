"""
test_gate_configuracion.py — Tests de la función pura decidir_gate_configuracion.

Cubre la matriz completa: 4 roles × 2 estados × rutas exentas/no-exentas.
Garantiza que la función pura es 100% predecible sin NiceGUI ni BD.
"""
from __future__ import annotations

import pytest

from src.interface.auth.route_guard import (
    GATE_ESPERA,
    GATE_OK,
    GATE_WIZARD,
    decidir_gate_configuracion,
)

# ---------------------------------------------------------------------------
# Casos base: admin nunca es bloqueado
# ---------------------------------------------------------------------------

def test_admin_siempre_ok_config_completa():
    result = decidir_gate_configuracion(
        rol="admin", config_completa=True, ruta="/inicio"
    )
    assert result == GATE_OK


def test_admin_siempre_ok_config_incompleta():
    """Admin no está sometido al gate aunque el tenant no esté configurado."""
    result = decidir_gate_configuracion(
        rol="admin", config_completa=False, ruta="/inicio"
    )
    assert result == GATE_OK


def test_admin_siempre_ok_ruta_sensible():
    """Admin tampoco es bloqueado en rutas de configuración."""
    result = decidir_gate_configuracion(
        rol="admin", config_completa=False, ruta="/admin/configuracion"
    )
    assert result == GATE_OK


# ---------------------------------------------------------------------------
# Tenant configurado: todos los roles pasan
# ---------------------------------------------------------------------------

def test_director_config_completa_ok():
    result = decidir_gate_configuracion(
        rol="director", config_completa=True, ruta="/inicio"
    )
    assert result == GATE_OK


def test_coordinador_config_completa_ok():
    result = decidir_gate_configuracion(
        rol="coordinador", config_completa=True, ruta="/inicio"
    )
    assert result == GATE_OK


def test_profesor_config_completa_ok():
    result = decidir_gate_configuracion(
        rol="profesor", config_completa=True, ruta="/evaluacion/planilla"
    )
    assert result == GATE_OK


# ---------------------------------------------------------------------------
# Tenant SIN configurar: comportamiento por rol
# ---------------------------------------------------------------------------

def test_director_config_incompleta_devuelve_wizard():
    """Director del tenant sin configurar → debe completar el wizard."""
    result = decidir_gate_configuracion(
        rol="director", config_completa=False, ruta="/inicio"
    )
    assert result == GATE_WIZARD


def test_coordinador_config_incompleta_devuelve_espera():
    result = decidir_gate_configuracion(
        rol="coordinador", config_completa=False, ruta="/inicio"
    )
    assert result == GATE_ESPERA


def test_profesor_config_incompleta_devuelve_espera():
    result = decidir_gate_configuracion(
        rol="profesor", config_completa=False, ruta="/asistencia"
    )
    assert result == GATE_ESPERA


def test_rol_desconocido_config_incompleta_devuelve_espera():
    """Un rol inesperado no debe bloquear la ruta con WIZARD (solo director hace eso)."""
    result = decidir_gate_configuracion(
        rol="acudiente", config_completa=False, ruta="/inicio"
    )
    assert result == GATE_ESPERA


# ---------------------------------------------------------------------------
# Rutas exentas: nunca redirigen (evita redirect-loops)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ruta", [
    "/configuracion-inicial",
    "/espera-configuracion",
    "/logout",
    "/cambiar-password",
])
def test_rutas_exentas_no_son_bloqueadas(ruta: str):
    """Las rutas exentas deben devolver GATE_OK aun cuando el tenant no está configurado."""
    result = decidir_gate_configuracion(
        rol="director", config_completa=False, ruta=ruta
    )
    assert result == GATE_OK


@pytest.mark.parametrize("ruta", [
    "/configuracion-inicial",
    "/espera-configuracion",
    "/logout",
    "/cambiar-password",
])
def test_rutas_exentas_ok_para_coordinador_sin_config(ruta: str):
    """Coordinador en ruta exenta → OK aun sin configuración (no hay loop)."""
    result = decidir_gate_configuracion(
        rol="coordinador", config_completa=False, ruta=ruta
    )
    assert result == GATE_OK


# ---------------------------------------------------------------------------
# Rol None (sesión incompleta)
# ---------------------------------------------------------------------------

def test_rol_none_config_incompleta_espera():
    """Sesión sin rol definido → tratado como no-director → ESPERA."""
    result = decidir_gate_configuracion(
        rol=None, config_completa=False, ruta="/inicio"
    )
    assert result == GATE_ESPERA


def test_rol_none_config_completa_ok():
    """Sesión sin rol pero tenant configurado → OK."""
    result = decidir_gate_configuracion(
        rol=None, config_completa=True, ruta="/inicio"
    )
    assert result == GATE_OK
