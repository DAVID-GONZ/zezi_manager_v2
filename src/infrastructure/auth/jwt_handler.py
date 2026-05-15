"""
jwt_handler.py — Generación y verificación de tokens JWT.

Implementación con stdlib pura (hmac + hashlib + base64 + json).
No requiere dependencias externas adicionales.

Preparado para la capa API REST (v3.0). No se usa en la versión
de escritorio con NiceGUI (v2.x), donde la sesión se gestiona
via app.storage.user.

Estructura del token: header.payload.signature (RFC 7519)
  - Algoritmo: HS256 (HMAC-SHA256)
  - Expiración: configurable, default 8 horas
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


class JWTHandler:
    """
    Manejador de tokens JWT con firma HMAC-SHA256 (HS256).

    Args:
        secret:           Clave secreta para firmar tokens. Usar mínimo 32 bytes
                          de entropía en producción.
        expiracion_horas: Tiempo de vida del token en horas (default: 8).

    Ejemplo:
        handler = JWTHandler(secret=settings.JWT_SECRET)
        token   = handler.crear_token({"usuario_id": 1, "rol": "profesor"})
        payload = handler.verificar_token(token)
        if payload:
            usuario_id = payload["usuario_id"]
    """

    algorithm = "HS256"

    def __init__(self, secret: str, expiracion_horas: int = 8) -> None:
        if not secret:
            raise ValueError("JWT secret no puede estar vacío.")
        self._secret  = secret.encode("utf-8")
        self._exp_seg = expiracion_horas * 3600

    # ── Creación ──────────────────────────────────────────────────────────────

    def crear_token(self, payload: dict[str, Any]) -> str:
        """
        Genera un token JWT firmado con los datos del payload.

        Incluye automáticamente iat (emitido) y exp (expiración).

        Args:
            payload: Datos a incluir (ej: {"usuario_id": 1, "rol": "profesor"}).

        Returns:
            Token JWT como string (header.payload.signature).
        """
        ahora  = int(time.time())
        claims = {
            **payload,
            "iat": ahora,
            "exp": ahora + self._exp_seg,
        }

        header = _b64url_encode(json.dumps({"alg": self.algorithm, "typ": "JWT"}).encode())
        body   = _b64url_encode(json.dumps(claims, ensure_ascii=False).encode())
        firma  = self._firmar(f"{header}.{body}")

        return f"{header}.{body}.{firma}"

    # ── Verificación ──────────────────────────────────────────────────────────

    def verificar_token(self, token: str) -> dict[str, Any] | None:
        """
        Verifica firma e integridad; retorna el payload si es válido.

        Retorna None (no lanza) si el token es inválido, mal formado o expirado.

        Args:
            token: Token JWT generado por `crear_token()`.

        Returns:
            Dict con el payload decodificado, o None si es inválido/expirado.
        """
        try:
            partes = token.split(".")
            if len(partes) != 3:
                return None

            header_b64, body_b64, firma_recibida = partes

            if not hmac.compare_digest(self._firmar(f"{header_b64}.{body_b64}"), firma_recibida):
                return None

            payload = json.loads(_b64url_decode(body_b64))

            if "exp" in payload and payload["exp"] < int(time.time()):
                return None

            return payload

        except Exception:
            return None

    # ── Utilidades ────────────────────────────────────────────────────────────

    def token_expirado(self, token: str) -> bool:
        """True si el token tiene firma válida pero ya expiró."""
        try:
            partes = token.split(".")
            if len(partes) != 3:
                return False
            header_b64, body_b64, firma = partes
            if not hmac.compare_digest(self._firmar(f"{header_b64}.{body_b64}"), firma):
                return False
            payload = json.loads(_b64url_decode(body_b64))
            return payload.get("exp", 0) < int(time.time())
        except Exception:
            return False

    def _firmar(self, mensaje: str) -> str:
        return _b64url_encode(
            hmac.new(self._secret, mensaje.encode("ascii"), hashlib.sha256).digest()
        )


# ── Funciones de conveniencia (API funcional alternativa) ─────────────────────

def crear_token(payload: dict[str, Any], secret: str, expiracion_horas: int = 8) -> str:
    """Atajo funcional para crear un token sin instanciar JWTHandler."""
    return JWTHandler(secret=secret, expiracion_horas=expiracion_horas).crear_token(payload)


def verificar_token(token: str, secret: str) -> dict[str, Any] | None:
    """Atajo funcional para verificar un token sin instanciar JWTHandler."""
    return JWTHandler(secret=secret).verificar_token(token)


__all__ = ["JWTHandler", "crear_token", "verificar_token"]
