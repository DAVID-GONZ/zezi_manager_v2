"""
bcrypt_auth.py — Utilidades bcrypt puras.

Funciones de bajo nivel para hashear y verificar contraseñas con bcrypt.
Sin dependencias de dominio, servicios ni base de datos.
Usadas internamente por BcryptAuthService.
"""
from __future__ import annotations

import bcrypt

ROUNDS = 12


def hashear(password: str) -> str:
    """
    Genera un hash bcrypt con salt aleatorio.

    Cada llamada produce un hash distinto (salt embebido).
    El resultado comienza con '$2b$' (formato bcrypt estándar).

    Args:
        password: Contraseña en texto plano.

    Returns:
        Hash bcrypt como string UTF-8.
    """
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=ROUNDS),
    ).decode("utf-8")


def verificar(password: str, password_hash: str) -> bool:
    """
    Verifica un password contra su hash bcrypt.

    Retorna False (no lanza) si el hash tiene formato inválido.

    Args:
        password:      Contraseña en texto plano.
        password_hash: Hash bcrypt generado por `hashear()`.

    Returns:
        True si el password coincide, False en cualquier otro caso.
    """
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except Exception:
        return False


__all__ = ["hashear", "verificar", "ROUNDS"]
