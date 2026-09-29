"""
Router de Convivencia — AVEDRA API (backend_12).

Endpoints:
  GET  /convivencia/observaciones              listar observaciones de un estudiante
  POST /convivencia/observaciones              registrar observacion
  GET  /convivencia/resumen-grupo              resumen convivencia por grupo/periodo
  GET  /convivencia/notas-grupo               notas de comportamiento del grupo
  GET  /convivencia/vista-360/{estudiante_id} perfil 360 del estudiante
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from container import Container
from src.api.schemas.auth import CurrentUserDTO
from src.api.schemas.convivencia import (
    NotaComportamientoResponse,
    NuevaObservacionRequest,
    ObservacionResponse,
    ResumenConvivenciaResponse,
)
from src.api.security import get_current_user, require_role

router = APIRouter(prefix="/convivencia", tags=["convivencia"])


@router.get("/observaciones", response_model=list[ObservacionResponse])
def listar_observaciones(
    estudiante_id: int,
    periodo_id: int | None = None,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Lista observaciones de un estudiante (opcionalmente filtradas por periodo)."""
    svc = Container.convivencia_service()
    obs = svc.listar_observaciones(
        estudiante_id,
        periodo_id=periodo_id,
        usuario_id=user.usuario_id,
        usuario_rol=user.rol,
    )
    return [ObservacionResponse.model_validate(o) for o in obs]


@router.post("/observaciones", response_model=ObservacionResponse, status_code=201)
def registrar_observacion(
    body: NuevaObservacionRequest,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Registra o actualiza una observacion narrativa."""
    from src.domain.models.convivencia import NuevaObservacionDTO

    svc = Container.convivencia_service()
    dto = NuevaObservacionDTO(
        estudiante_id=body.estudiante_id,
        asignacion_id=body.asignacion_id,
        periodo_id=body.periodo_id,
        texto=body.texto,
        categoria_id=body.categoria_id,
        es_publica=body.es_publica,
    )
    resultado = svc.registrar_observacion(dto, usuario_id=user.usuario_id, usuario_rol=user.rol)
    return ObservacionResponse.model_validate(resultado)


@router.get("/resumen-grupo", response_model=list[ResumenConvivenciaResponse])
def resumen_convivencia_grupo(
    grupo_id: int,
    periodo_id: int,
    user: CurrentUserDTO = Depends(require_role("admin", "director", "coordinador")),  # noqa: B008
):
    """Resumen de convivencia (notas, observaciones, alertas) de todos los estudiantes."""
    svc = Container.convivencia_service()
    resumenes = svc.resumen_convivencia_grupo(grupo_id, periodo_id)
    return [ResumenConvivenciaResponse.model_validate(r) for r in resumenes]


@router.get("/notas-grupo", response_model=list[NotaComportamientoResponse])
def notas_grupo(
    grupo_id: int,
    periodo_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Retorna las notas de comportamiento de todos los estudiantes del grupo."""
    svc = Container.convivencia_service()
    notas = svc.listar_notas_grupo(grupo_id, periodo_id)
    return [NotaComportamientoResponse.model_validate(n) for n in notas]


@router.get("/vista-360/{estudiante_id}")
def vista_360(
    estudiante_id: int,
    periodo_id: int,
    user: CurrentUserDTO = Depends(require_role("admin", "director", "coordinador")),  # noqa: B008
):
    """Perfil 360 de convivencia de un estudiante en un periodo."""
    svc = Container.convivencia_service()
    resultado = svc.vista_360(
        estudiante_id,
        periodo_id,
        usuario_id=user.usuario_id,
        usuario_rol=user.rol,
    )
    return resultado
