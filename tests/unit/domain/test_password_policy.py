"""Tests unitarios para la política de contraseñas (dominio puro)."""
from __future__ import annotations

import pytest

from src.domain.policies.password_policy import (
    LONGITUD_MINIMA,
    errores_password,
    requisitos_password,
    validar_password,
)


class TestErroresPassword:
    def test_password_valida_no_tiene_errores(self):
        assert errores_password("Clave2026") == []

    def test_corta_tiene_error_de_longitud(self):
        errores = errores_password("Ab1")
        assert any(str(LONGITUD_MINIMA) in e for e in errores)

    def test_solo_digitos_falla_composicion(self):
        # 8 dígitos: longitud OK, pero sin letra → falla composición.
        errores = errores_password("12345678")
        assert errores != []
        assert any("letra" in e.lower() for e in errores)

    def test_solo_letras_falla_composicion(self):
        errores = errores_password("abcdefgh")
        assert errores != []
        assert any("número" in e.lower() or "numero" in e.lower() for e in errores)

    def test_igual_al_username_falla(self):
        # cumple longitud + composición, pero es igual (case-insensitive) al user.
        errores = errores_password("Juan2026", username="juan2026")
        assert any("usuario" in e.lower() for e in errores)

    def test_distinta_del_username_pasa(self):
        assert errores_password("Clave2026", username="juan") == []

    def test_sin_username_no_aplica_regla_igualdad(self):
        assert errores_password("Clave2026") == []


class TestValidarPassword:
    def test_no_lanza_si_valida(self):
        validar_password("Clave2026")  # no lanza

    def test_lanza_si_corta(self):
        with pytest.raises(ValueError):
            validar_password("Ab1")

    def test_lanza_si_solo_digitos(self):
        with pytest.raises(ValueError):
            validar_password("12345678")

    def test_lanza_si_solo_letras(self):
        with pytest.raises(ValueError):
            validar_password("abcdefgh")

    def test_lanza_si_igual_al_username(self):
        with pytest.raises(ValueError):
            validar_password("Juan2026", username="JUAN2026")


class TestRequisitosPassword:
    def test_devuelve_lista_de_strings_no_vacia(self):
        reqs = requisitos_password()
        assert isinstance(reqs, list)
        assert reqs
        assert all(isinstance(r, str) for r in reqs)
