"""
Router de Usuarios — AVEDRA API (backend_12).

Endpoints:
  GET    /usuarios          listar usuarios (con filtros)
  POST   /usuarios          crear usuario
  GET    /usuarios/{id}     obtener usuario por id
  PUT    /usuarios/{id}     actualizar usuario
  POST   /usuarios/{id}/desactivar   desactivar usuario
  POST   /usuarios/{id}/reactivar    reactivar usuario
  POST   /usuarios/{id}/cambiar-rol  cambiar rol
  POST   /usuarios/{id}/resetear-password  resetear password
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from container import Container
from src.api.deps import PaginationParams
from src.api.schemas.auth import CurrentUserDTO
from src.api.schemas.common import PaginatedResponse
from src.api.schemas.usuarios import (
    ActualizarUsuarioRequest,
    CambiarRolRequest,
    NuevoUsuarioRequest,
    ResetearPasswordRequest,
    UsuarioResponse,
)
from src.api.security import get_current_user, require_role

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=PaginatedResponse[UsuarioResponse])
def listar_usuarios(
    rol: str | None = None,
    activo: bool | None = None,
    pagination: PaginationParams = Depends(),  # noqa: B008
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Lista usuarios con filtros opcionales (rol, activo)."""
    from src.domain.models.usuario import FiltroUsuariosDTO, Rol

    svc = Container.usuario_service()
    rol_enum = Rol(rol) if rol is not None else None
    solo_activos = activo if activo is not None else False
    filtro = FiltroUsuariosDTO(rol=rol_enum, solo_activos=solo_activos, por_pagina=pagination.per_page)
    todos = svc.listar_filtrado(filtro)
    page_items = todos[pagination.offset : pagination.offset + pagination.per_page]
    return PaginatedResponse(
        items=[UsuarioResponse.model_validate(u) for u in page_items],
        total=len(todos),
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.post("", response_model=UsuarioResponse, status_code=201)
def crear_usuario(
    body: NuevoUsuarioRequest,
    user: CurrentUserDTO = Depends(require_role("admin", "director")),  # noqa: B008
):
    """Crea un usuario nuevo."""
    from src.domain.models.usuario import NuevoUsuarioDTO, Rol

    svc = Container.usuario_service()
    dto = NuevoUsuarioDTO(
        usuario=body.usuario,
        nombre_completo=body.nombre_completo,
        rol=Rol(body.rol),
        email=body.email,
        institucion_id=body.institucion_id,
        password=body.password,
    )
    nuevo = svc.crear_usuario(dto, creado_por_id=user.usuario_id, actor_rol=user.rol)
    return UsuarioResponse.model_validate(nuevo)


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def obtener_usuario(
    usuario_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Obtiene un usuario por id."""
    svc = Container.usuario_service()
    obj = svc.get_by_id(usuario_id)
    return UsuarioResponse.model_validate(obj)


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(
    usuario_id: int,
    body: ActualizarUsuarioRequest,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Actualiza nombre, email o telefono de un usuario."""
    from src.domain.models.usuario import ActualizarUsuarioDTO

    svc = Container.usuario_service()
    dto = ActualizarUsuarioDTO(
        nombre_completo=body.nombre_completo,
        email=body.email,
        telefono=body.telefono,
    )
    actualizado = svc.actualizar(usuario_id, dto, actualizado_por_id=user.usuario_id)
    return UsuarioResponse.model_validate(actualizado)


@router.post("/{usuario_id}/desactivar", response_model=UsuarioResponse)
def desactivar_usuario(
    usuario_id: int,
    user: CurrentUserDTO = Depends(require_role("admin", "director")),  # noqa: B008
):
    """Desactiva un usuario (soft delete)."""
    svc = Container.usuario_service()
    resultado = svc.desactivar(usuario_id, desactivado_por_id=user.usuario_id, actor_rol=user.rol)
    return UsuarioResponse.model_validate(resultado)


@router.post("/{usuario_id}/reactivar", response_model=UsuarioResponse)
def reactivar_usuario(
    usuario_id: int,
    user: CurrentUserDTO = Depends(require_role("admin", "director")),  # noqa: B008
):
    """Reactiva un usuario desactivado."""
    svc = Container.usuario_service()
    resultado = svc.reactivar(usuario_id, reactivado_por_id=user.usuario_id, actor_rol=user.rol)
    return UsuarioResponse.model_validate(resultado)


@router.post("/{usuario_id}/cambiar-rol", response_model=UsuarioResponse)
def cambiar_rol(
    usuario_id: int,
    body: CambiarRolRequest,
    user: CurrentUserDTO = Depends(require_role("admin", "director")),  # noqa: B008
):
    """Cambia el rol de un usuario."""
    from src.domain.models.usuario import Rol

    svc = Container.usuario_service()
    resultado = svc.cambiar_rol(
        usuario_id,
        Rol(body.nuevo_rol),
        cambiado_por_id=user.usuario_id,
        actor_rol=user.rol,
    )
    return UsuarioResponse.model_validate(resultado)


@router.post("/{usuario_id}/resetear-password")
def resetear_password(
    usuario_id: int,
    body: ResetearPasswordRequest,
    user: CurrentUserDTO = Depends(require_role("admin", "director")),  # noqa: B008
):
    """Resetea la contrasena de un usuario. Retorna la temporal si no se dio una explicita."""
    svc = Container.usuario_service()
    temporal = svc.resetear_password(
        usuario_id,
        body.nueva_password,
        actor_rol=user.rol,
        reset_por_id=user.usuario_id,
    )
    return {"password_temporal": temporal}
