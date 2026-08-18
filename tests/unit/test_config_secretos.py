"""
Tests de gestión de secretos en Settings (seguridad_web_02 — R4, R8).

- Bloqueo de arranque en producción con secretos por defecto (R8).
- repr() enmascara JWT_SECRET y STORAGE_SECRET (R4).
- JWT_SECRET != STORAGE_SECRET cuando ambos están configurados.
"""
from __future__ import annotations

import pytest

from config import Settings

_JWT_OK = "x" * 48
_STORAGE_OK = "y" * 48
_JWT_DEFAULT = "cambia-esta-clave-en-produccion-ahora"
_STORAGE_DEFAULT = "cambia-este-storage-secret-en-produccion"


def _settings(**over) -> Settings:
    return Settings(_env_file=None, **over)


def _settings_prod(**over) -> Settings:
    return _settings(
        APP_ENV="production",
        JWT_SECRET=_JWT_OK,
        STORAGE_SECRET=_STORAGE_OK,
        **over,
    )


class TestBloqueoProduccion:
    """R8 — arranque en production con secretos por defecto debe abortar."""

    def test_jwt_default_bloquea(self):
        with pytest.raises(ValueError, match="JWT_SECRET"):
            _settings(APP_ENV="production", JWT_SECRET=_JWT_DEFAULT, STORAGE_SECRET=_STORAGE_OK)

    def test_storage_default_bloquea(self):
        with pytest.raises(ValueError, match="STORAGE_SECRET"):
            _settings(APP_ENV="production", JWT_SECRET=_JWT_OK, STORAGE_SECRET=_STORAGE_DEFAULT)

    def test_ambos_seguros_arranca(self):
        s = _settings_prod()
        assert s.is_production


class TestEnmascaradoRepr:
    """R4 — repr() no debe exponer valores de secretos en claro."""

    def test_repr_enmascara_jwt_secret(self):
        s = _settings_prod()
        assert _JWT_OK not in repr(s)
        assert "***" in repr(s)

    def test_repr_enmascara_storage_secret(self):
        s = _settings_prod()
        assert _STORAGE_OK not in repr(s)

    def test_repr_enmascara_ambos(self):
        s = _settings(JWT_SECRET=_JWT_OK, STORAGE_SECRET=_STORAGE_OK)
        r = repr(s)
        assert _JWT_OK not in r
        assert _STORAGE_OK not in r
        assert r.count("***") >= 2

    def test_acceso_directo_no_enmascarado(self):
        """El atributo real sigue accesible; solo repr() enmascara."""
        s = _settings_prod()
        assert s.JWT_SECRET == _JWT_OK
        assert s.STORAGE_SECRET == _STORAGE_OK


class TestSecretosIndependientes:
    """R1 — JWT_SECRET != STORAGE_SECRET."""

    def test_valores_distintos(self):
        s = _settings(JWT_SECRET=_JWT_OK, STORAGE_SECRET=_STORAGE_OK)
        assert s.JWT_SECRET != s.STORAGE_SECRET

    def test_defaults_distintos(self):
        s = _settings()
        assert s.JWT_SECRET != s.STORAGE_SECRET
