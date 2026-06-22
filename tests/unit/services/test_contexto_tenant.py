"""
Tests del mecanismo central de scope por institución (paso_28 — frente C).

Cubre:
  - Primitivas del módulo contexto_tenant (default None, set/get).
  - Restauración del context manager usar_institucion (anidado incluido).
"""
from __future__ import annotations

import pytest

from src.services.contexto_tenant import (
    activar_institucion,
    institucion_actual,
    usar_institucion,
    verificar_pertenencia,
    OperacionFueraDeInstitucionError,
)


@pytest.fixture(autouse=True)
def _reset_scope():
    """Cada test arranca y termina sin scope (None)."""
    activar_institucion(None)
    yield
    activar_institucion(None)


# ── Primitivas del módulo ───────────────────────────────────────────────────

def test_default_es_none():
    assert institucion_actual() is None


def test_activar_y_consultar():
    activar_institucion(7)
    assert institucion_actual() == 7
    activar_institucion(None)
    assert institucion_actual() is None


# ── Context manager ──────────────────────────────────────────────────────────

def test_usar_institucion_setea_y_restaura():
    assert institucion_actual() is None
    with usar_institucion(3):
        assert institucion_actual() == 3
    assert institucion_actual() is None


def test_usar_institucion_restaura_valor_previo():
    activar_institucion(1)
    with usar_institucion(5):
        assert institucion_actual() == 5
    assert institucion_actual() == 1


def test_usar_institucion_anidado():
    with usar_institucion(1):
        assert institucion_actual() == 1
        with usar_institucion(2):
            assert institucion_actual() == 2
        assert institucion_actual() == 1
    assert institucion_actual() is None


def test_usar_institucion_restaura_ante_excepcion():
    activar_institucion(9)
    with pytest.raises(RuntimeError):
        with usar_institucion(4):
            assert institucion_actual() == 4
            raise RuntimeError("boom")
    assert institucion_actual() == 9


# ── Helper de pertenencia (paso_36 — hallazgo E) ────────────────────────────

def test_verificar_pertenencia_scope_none_pasa_siempre():
    # Sin scope (admin / seed): cualquier institucion_id (incluido None) pasa.
    assert institucion_actual() is None
    verificar_pertenencia(1)
    verificar_pertenencia(99)
    verificar_pertenencia(None)


def test_verificar_pertenencia_scope_x_pasa_con_x():
    activar_institucion(5)
    verificar_pertenencia(5)  # no lanza


def test_verificar_pertenencia_scope_x_lanza_con_y():
    activar_institucion(5)
    with pytest.raises(OperacionFueraDeInstitucionError):
        verificar_pertenencia(6)


def test_verificar_pertenencia_scope_x_lanza_con_none():
    # Objeto sin institución asignada bajo un scope concreto → rechazado.
    activar_institucion(5)
    with pytest.raises(OperacionFueraDeInstitucionError):
        verificar_pertenencia(None)


def test_error_es_permission_error():
    assert issubclass(OperacionFueraDeInstitucionError, PermissionError)
