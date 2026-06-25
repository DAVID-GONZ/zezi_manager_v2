"""
Tests de los secretos de configuración (seguridad_02 — M1).

Verifican que STORAGE_SECRET es independiente de JWT_SECRET y que el blindaje
de producción bloquea el valor por defecto inseguro de AMBOS secretos.

Se instancia `Settings` directamente con overrides y `_env_file=None` para no
leer el `.env` real del proyecto.
"""
from __future__ import annotations

import pytest

from config import Settings

# Secretos válidos (>=32 chars, no contienen el sentinel inseguro).
_JWT_OK = "x" * 40
_STORAGE_OK = "y" * 40
_JWT_DEFAULT = "cambia-esta-clave-en-produccion-ahora"
_STORAGE_DEFAULT = "cambia-este-storage-secret-en-produccion"


def _settings(**over) -> Settings:
    return Settings(_env_file=None, **over)


class TestStorageSecretIndependiente:
    def test_storage_secret_existe_y_tiene_default_propio(self):
        s = _settings()
        assert isinstance(s.STORAGE_SECRET, str)
        assert s.STORAGE_SECRET  # no vacío

    def test_default_storage_distinto_de_default_jwt(self):
        s = _settings()
        assert s.STORAGE_SECRET != s.JWT_SECRET

    def test_acepta_valores_personalizados_distintos(self):
        s = _settings(
            APP_ENV="development",
            JWT_SECRET=_JWT_OK,
            STORAGE_SECRET=_STORAGE_OK,
        )
        assert s.JWT_SECRET == _JWT_OK
        assert s.STORAGE_SECRET == _STORAGE_OK


class TestBlindajeProduccion:
    def test_produccion_bloquea_storage_default(self):
        with pytest.raises(ValueError, match="STORAGE_SECRET"):
            _settings(
                APP_ENV="production",
                JWT_SECRET=_JWT_OK,            # JWT seguro
                STORAGE_SECRET=_STORAGE_DEFAULT,  # storage inseguro
            )

    def test_produccion_bloquea_jwt_default(self):
        with pytest.raises(ValueError, match="JWT_SECRET"):
            _settings(
                APP_ENV="production",
                JWT_SECRET=_JWT_DEFAULT,        # JWT inseguro
                STORAGE_SECRET=_STORAGE_OK,
            )

    def test_produccion_acepta_ambos_seguros(self):
        s = _settings(
            APP_ENV="production",
            JWT_SECRET=_JWT_OK,
            STORAGE_SECRET=_STORAGE_OK,
        )
        assert s.is_production

    def test_desarrollo_no_bloquea_con_defaults(self):
        # En development, los defaults solo advierten (no lanzan).
        s = _settings(
            APP_ENV="development",
            JWT_SECRET=_JWT_DEFAULT,
            STORAGE_SECRET=_STORAGE_DEFAULT,
        )
        assert s.is_development
