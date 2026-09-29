"""
Router de Auditoria — AVEDRA API (backend_12).

Solo accesible para admin y director.

Endpoints:
  GET /auditoria/eventos        listar eventos de sesion (login/logout)
  GET /auditoria/cambios        listar cambios del audit log
  GET /auditoria/integridad     verificar integridad de la cadena de hash
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from container import Container
from src.api.deps import PaginationParams, scope_from_user
from src.api.schemas.auditoria import (
    EventoSesionResponse,
    IntegridadResponse,
    RegistroCambioResponse,
)
from src.api.schemas.auth import CurrentUserDTO
from src.api.schemas.common import PaginatedResponse
from src.api.security import require_role

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("/eventos", response_model=PaginatedResponse[EventoSesionResponse])
def listar_eventos(
    usuario_id: int | None = None,
    tipo_evento: str | None = None,
    pagination: PaginationParams = Depends(),  # noqa: B008
    user: CurrentUserDTO = Depends(require_role("admin", "director")),  # noqa: B008
):
    """Lista eventos de sesion (login, logout, fallos) paginados."""
    from src.domain.models.auditoria import FiltroAuditoriaDTO, TipoEventoSesion

    svc = Container.auditoria_service()
    scope = scope_from_user(user)
    tipo_enum = TipoEventoSesion(tipo_evento) if tipo_evento is not None else None
    filtro = FiltroAuditoriaDTO(
        usuario_id=usuario_id,
        tipo_evento=tipo_enum,
        pagina=pagination.page,
        por_pagina=pagination.per_page,
    )
    eventos = svc.listar_eventos_sesion(filtro, scope)
    return PaginatedResponse(
        items=[EventoSesionResponse.model_validate(e) for e in eventos],
        total=len(eventos),
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.get("/cambios", response_model=PaginatedResponse[RegistroCambioResponse])
def listar_cambios(
    usuario_id: int | None = None,
    tabla: str | None = None,
    pagination: PaginationParams = Depends(),  # noqa: B008
    user: CurrentUserDTO = Depends(require_role("admin", "director")),  # noqa: B008
):
    """Lista cambios del audit_log paginados."""
    from src.domain.models.auditoria import FiltroAuditoriaDTO

    svc = Container.auditoria_service()
    scope = scope_from_user(user)
    filtro = FiltroAuditoriaDTO(
        usuario_id=usuario_id,
        tabla=tabla,
        pagina=pagination.page,
        por_pagina=pagination.per_page,
    )
    cambios = svc.listar_cambios(filtro, scope)
    return PaginatedResponse(
        items=[RegistroCambioResponse.model_validate(c) for c in cambios],
        total=len(cambios),
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.get("/integridad", response_model=IntegridadResponse)
def verificar_integridad(
    completa: bool = False,
    user: CurrentUserDTO = Depends(require_role("admin")),  # noqa: B008
):
    """Verifica el encadenamiento por hash de las tablas de auditoria."""
    svc = Container.auditoria_service()
    resultado = svc.verificar_integridad(completa=completa)
    return IntegridadResponse(
        eventos_ok=resultado.get("eventos_ok", True),
        cambios_ok=resultado.get("cambios_ok", True),
        evento_roto_id=resultado.get("evento_roto_id"),
        cambio_roto_id=resultado.get("cambio_roto_id"),
        alcance=resultado.get("alcance", "incremental"),
    )
