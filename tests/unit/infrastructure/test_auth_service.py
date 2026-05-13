"""Tests de BcryptAuthService — operaciones de criptografía pura (sin repo)."""
from __future__ import annotations

import hashlib

from src.infrastructure.auth import BcryptAuthService


def test_hashear_y_verificar():
    svc = BcryptAuthService()
    hash_ = svc.hashear_password("mi_clave_123")
    assert svc.verificar_password("mi_clave_123", hash_) is True
    assert svc.verificar_password("clave_incorrecta", hash_) is False


def test_verificar_hash_sha256_legacy():
    # Compatibilidad con hashes del seed.py de desarrollo
    digest = hashlib.sha256("Admin2025*".encode()).hexdigest()
    hash_legacy = f"sha256:{digest}"
    svc = BcryptAuthService()
    assert svc.verificar_password("Admin2025*", hash_legacy) is True


def test_hashes_distintos_mismo_password():
    # bcrypt genera salt distinto cada vez — dos hashes del mismo
    # password no deben ser iguales (propiedad de seguridad)
    svc = BcryptAuthService()
    h1 = svc.hashear_password("misma_clave")
    h2 = svc.hashear_password("misma_clave")
    assert h1 != h2
    assert svc.verificar_password("misma_clave", h1) is True
    assert svc.verificar_password("misma_clave", h2) is True
