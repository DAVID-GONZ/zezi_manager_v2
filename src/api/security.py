"""
security.py -- Seguridad de la API REST (backend_11).

Contiene:
  - InMemoryRateLimiter: proteccion contra fuerza bruta en login.
  - get_current_user: dependencia FastAPI que valida el JWT y fija ContextVars.
  - require_role: factory de dependencias que exige rol(es) especifico(s).
"""

from __future__ import annotations

import time

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings
from src.api.schemas.auth import CurrentUserDTO
from src.infrastructure.context.contexto_actor import activar_actor
from src.infrastructure.context.contexto_tenant import activar_institucion
from src.infrastructure.context.solo_lectura import activar_solo_lectura

# =========================================================================
# Rate limiter en memoria
# =========================================================================


class InMemoryRateLimiter:
    """
    Limitador de intentos por IP en memoria.

    Parametros por defecto: maximo 5 intentos fallidos por IP en una ventana
    de 300 segundos (5 minutos). Al exceder el limite, ``check()`` lanza
    HTTPException 429.

    Limitaciones conocidas:
      - No persiste entre reinicios del proceso.
      - No escala a multiples workers/procesos (usar Redis en produccion).
    """

    def __init__(self, max_intentos: int = 5, ventana_seg: int = 300) -> None:
        self._max_intentos = max_intentos
        self._ventana_seg = ventana_seg
        self._intentos: dict[str, list[float]] = {}

    def _purgar(self, ip: str) -> None:
        """Elimina timestamps mas antiguos que la ventana para la IP dada."""
        corte = time.monotonic() - self._ventana_seg
        if ip in self._intentos:
            self._intentos[ip] = [t for t in self._intentos[ip] if t > corte]
            if not self._intentos[ip]:
                del self._intentos[ip]

    def check(self, ip: str) -> None:
        """Lanza HTTPException 429 si la IP excedio el limite de intentos."""
        self._purgar(ip)
        if ip in self._intentos and len(self._intentos[ip]) >= self._max_intentos:
            raise HTTPException(
                status_code=429,
                detail="Demasiados intentos. Intente de nuevo mas tarde.",
            )

    def registrar_fallo(self, ip: str) -> None:
        """Registra un intento fallido para la IP dada."""
        self._intentos.setdefault(ip, []).append(time.monotonic())


# Singleton del modulo
rate_limiter = InMemoryRateLimiter()


# =========================================================================
# Esquema de autenticacion Bearer
# =========================================================================

bearer_scheme = HTTPBearer()


# =========================================================================
# Dependencia: get_current_user
# =========================================================================


def _set_context_vars(user: CurrentUserDTO, request: Request) -> None:
    """Fija las ContextVars de la sesion a partir del usuario autenticado."""
    ip = request.client.host if request.client else None
    activar_institucion(user.institucion_id)
    activar_actor(user.usuario_id, user.username, ip)
    activar_solo_lectura(False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),  # noqa: B008
) -> CurrentUserDTO:
    """
    Dependencia FastAPI que valida el token JWT Bearer y retorna el usuario.

    Fija las ContextVars (tenant, actor, solo_lectura) para que los servicios
    downstream operen con el contexto correcto.
    """
    from src.infrastructure.auth.jwt_handler import JWTHandler

    payload = JWTHandler(secret=settings.JWT_SECRET).verificar_token(
        credentials.credentials,
    )
    if payload is None:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")

    user = CurrentUserDTO(
        usuario_id=payload["usuario_id"],
        username=payload["username"],
        rol=payload["rol"],
        institucion_id=payload.get("institucion_id"),
    )
    _set_context_vars(user, request)
    return user


# =========================================================================
# Dependencia: require_role
# =========================================================================


def require_role(*roles: str):
    """
    Factory de dependencias que exige que el usuario tenga uno de los roles dados.

    Uso::

        @router.get("/admin-only")
        def admin_view(user = Depends(require_role("admin"))):
            ...
    """

    async def _check(
        user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
    ) -> CurrentUserDTO:
        if user.rol not in roles:
            raise HTTPException(status_code=403, detail="Rol insuficiente")
        return user

    return _check


__all__ = [
    "InMemoryRateLimiter",
    "bearer_scheme",
    "get_current_user",
    "rate_limiter",
    "require_role",
]
