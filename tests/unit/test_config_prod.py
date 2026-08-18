"""
Tests de la aserción de binding en producción (seguridad_web_01 — R2).

Verifican que Settings rechaza HOST != loopback cuando APP_ENV=production,
y que en desarrollo no bloquea aunque HOST sea 0.0.0.0.
"""
from __future__ import annotations

import pytest

from config import Settings

_JWT_OK = "x" * 40
_STORAGE_OK = "y" * 40


def _settings(**over) -> Settings:
    return Settings(_env_file=None, **over)


def _settings_prod(**over) -> Settings:
    return _settings(
        APP_ENV="production",
        JWT_SECRET=_JWT_OK,
        STORAGE_SECRET=_STORAGE_OK,
        **over,
    )


class TestBindingProduccion:
    def test_produccion_loopback_ipv4_ok(self):
        s = _settings_prod(HOST="127.0.0.1")
        assert s.is_production

    def test_produccion_localhost_ok(self):
        s = _settings_prod(HOST="localhost")
        assert s.is_production

    def test_produccion_all_interfaces_bloquea(self):
        with pytest.raises(ValueError, match="HOST debe ser loopback"):
            _settings_prod(HOST="0.0.0.0")

    def test_produccion_ip_publica_bloquea(self):
        with pytest.raises(ValueError, match="HOST debe ser loopback"):
            _settings_prod(HOST="203.0.113.1")

    def test_desarrollo_no_bloquea_con_host_externo(self):
        s = _settings(APP_ENV="development", HOST="0.0.0.0")
        assert s.is_development

    def test_desarrollo_default_host_es_loopback(self):
        s = _settings(APP_ENV="development")
        assert s.HOST == "127.0.0.1"
