"""
auth.py -- Endpoint de autenticacion JWT para la API REST (backend_11).

POST /auth/login: autentica usuario y retorna token JWT.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from config import settings
from container import Container
from src.api.schemas.auth import LoginRequest, TokenResponse
from src.api.security import rate_limiter
from src.infrastructure.auth.jwt_handler import JWTHandler

_log = logging.getLogger("API_AUTH")

auth_router = APIRouter(prefix="/auth", tags=["auth"])


# =========================================================================
# Helpers de auditoria
# =========================================================================


def _auditar_login_exitoso(user, ip: str | None) -> None:
    """Registra un evento de login exitoso via API REST."""
    try:
        from src.domain.models.auditoria import EventoSesion, TipoEventoSesion
        from src.domain.policies.severidad_evento import severidad_de

        Container.auditoria_service().registrar_evento(
            EventoSesion(
                usuario=user.usuario,
                usuario_id=user.id,
                tipo_evento=TipoEventoSesion.LOGIN_EXITOSO,
                ip_address=ip,
                detalles="API REST",
                severidad=severidad_de(TipoEventoSesion.LOGIN_EXITOSO, None),
                institucion_id=user.institucion_id,
            )
        )
    except Exception:
        _log.warning("No se pudo auditar login exitoso")


def _auditar_login_fallido(username: str, ip: str | None) -> None:
    """Registra un evento de login fallido via API REST."""
    try:
        from src.domain.models.auditoria import EventoSesion, TipoEventoSesion
        from src.domain.policies.severidad_evento import severidad_de

        Container.auditoria_service().registrar_evento(
            EventoSesion(
                usuario=username,
                usuario_id=None,
                tipo_evento=TipoEventoSesion.LOGIN_FALLIDO,
                ip_address=ip,
                detalles="API REST",
                severidad=severidad_de(TipoEventoSesion.LOGIN_FALLIDO, None),
            )
        )
    except Exception:
        _log.warning("No se pudo auditar login fallido")


# =========================================================================
# Endpoint
# =========================================================================


@auth_router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request):
    """
    Autentica un usuario y retorna un token JWT.

    Flujo:
      1. Rate-limit por IP.
      2. Autenticar via BcryptAuthService (Container).
      3. Generar token JWT con claims del usuario.
      4. Auditar el resultado (exitoso o fallido).
    """
    ip = request.client.host if request.client else None
    rate_limiter.check(ip or "unknown")

    try:
        user = Container.auth_service().autenticar_usuario(
            body.username, body.password
        )
    except ValueError as e:
        msg = str(e)
        if msg == "cuenta_inactiva":
            raise HTTPException(status_code=403, detail="cuenta_inactiva") from None
        # Credenciales invalidas
        rate_limiter.registrar_fallo(ip or "unknown")
        _auditar_login_fallido(body.username, ip)
        raise HTTPException(status_code=401, detail="credenciales_invalidas") from None

    token = JWTHandler(
        secret=settings.JWT_SECRET,
        expiracion_horas=int(settings.JWT_EXPIRE_MINUTES / 60),
    ).crear_token(
        {
            "usuario_id": user.id,
            "username": user.usuario,
            "rol": user.rol.value,
            "institucion_id": user.institucion_id,
        }
    )

    _auditar_login_exitoso(user, ip)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


__all__ = ["auth_router"]
