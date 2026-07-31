"""Tests unitarios para la política de contraseñas (dominio puro)."""
from __future__ import annotations

import pytest

from src.domain.policies.password_policy import (
    LONGITUD_MAXIMA,
    LONGITUD_MINIMA,
    errores_password,
    requisitos_password,
    validar_password,
)

# Contraseña que cumple TODAS las reglas nuevas.
_VALIDA = "MiClave2026!"


class TestErroresPassword:
    def test_password_valida_no_tiene_errores(self):
        assert errores_password(_VALIDA) == []

    def test_corta_tiene_error_de_longitud(self):
        errores = errores_password("Ab1!")
        assert any(str(LONGITUD_MINIMA) in e for e in errores)

    def test_excede_maximo_tiene_error(self):
        larga = "Aa1!" + "x" * (LONGITUD_MAXIMA + 1)
        errores = errores_password(larga)
        assert any(str(LONGITUD_MAXIMA) in e for e in errores)

    def test_sin_mayuscula_falla(self):
        errores = errores_password("miclave2026!")
        assert any("mayúscula" in e.lower() for e in errores)

    def test_sin_minuscula_falla(self):
        errores = errores_password("MICLAVE2026!")
        assert any("minúscula" in e.lower() for e in errores)

    def test_solo_digitos_falla(self):
        errores = errores_password("1234567890")
        assert errores != []

    def test_solo_letras_falla(self):
        errores = errores_password("Abcdefghij")
        assert errores != []

    def test_sin_digito_falla(self):
        errores = errores_password("MiClave!!xx")
        assert any("número" in e.lower() for e in errores)

    def test_sin_especial_falla(self):
        errores = errores_password("MiClave2026x")
        assert any("especial" in e.lower() for e in errores)

    def test_igual_al_username_falla(self):
        errores = errores_password("MiClave2026!", username="MiClave2026!")
        assert any("usuario" in e.lower() for e in errores)

    def test_distinta_del_username_pasa(self):
        assert errores_password(_VALIDA, username="juan") == []

    def test_sin_username_no_aplica_regla_igualdad(self):
        assert errores_password(_VALIDA) == []

    def test_password_comun_prohibida(self):
        errores = errores_password("Password123!")
        assert any("común" in e.lower() for e in errores)

    def test_password_comun_case_insensitive(self):
        errores = errores_password("password123!")
        assert any("común" in e.lower() for e in errores)


class TestValidarPassword:
    def test_no_lanza_si_valida(self):
        validar_password(_VALIDA)

    def test_lanza_si_corta(self):
        with pytest.raises(ValueError):
            validar_password("Ab1!")

    def test_lanza_si_solo_digitos(self):
        with pytest.raises(ValueError):
            validar_password("1234567890")

    def test_lanza_si_solo_letras(self):
        with pytest.raises(ValueError):
            validar_password("Abcdefghij")

    def test_lanza_si_igual_al_username(self):
        with pytest.raises(ValueError):
            validar_password("MiClave2026!", username="MiClave2026!")

    def test_lanza_si_sin_mayuscula(self):
        with pytest.raises(ValueError):
            validar_password("miclave2026!")

    def test_lanza_si_sin_minuscula(self):
        with pytest.raises(ValueError):
            validar_password("MICLAVE2026!")

    def test_lanza_si_sin_especial(self):
        with pytest.raises(ValueError):
            validar_password("MiClave2026x")

    def test_lanza_si_excede_maximo(self):
        with pytest.raises(ValueError):
            validar_password("Aa1!" + "x" * (LONGITUD_MAXIMA + 1))

    def test_lanza_si_password_comun(self):
        with pytest.raises(ValueError):
            validar_password("Password123!")


class TestRequisitosPassword:
    def test_devuelve_lista_de_strings_no_vacia(self):
        reqs = requisitos_password()
        assert isinstance(reqs, list)
        assert reqs
        assert all(isinstance(r, str) for r in reqs)

    def test_incluye_reglas_clave(self):
        texto = " ".join(requisitos_password()).lower()
        assert str(LONGITUD_MINIMA) in texto
        assert "mayúscula" in texto
        assert "minúscula" in texto
        assert "número" in texto
        assert "especial" in texto
