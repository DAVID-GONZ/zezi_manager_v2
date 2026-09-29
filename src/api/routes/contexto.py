"""
Router de Contexto Academico — AVEDRA API (backend_12).

Expone el catalogo de grupos, asignaturas y periodos para que
los clientes conozcan el contexto academico de la institucion.

Endpoints:
  GET /contexto/grupos          listar grupos (filtro: grado)
  GET /contexto/asignaturas     listar asignaturas (filtro: area_id)
  GET /contexto/periodos        listar periodos por anio
  GET /contexto/periodos/activo periodo activo del anio
  GET /contexto/anio-activo     configuracion del anio activo
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from container import Container
from src.api.schemas.auth import CurrentUserDTO
from src.api.schemas.contexto import AsignaturaResponse, GrupoResponse, PeriodoResponse
from src.api.security import get_current_user

router = APIRouter(prefix="/contexto", tags=["contexto"])


@router.get("/grupos", response_model=list[GrupoResponse])
def listar_grupos(
    grado: int | None = None,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Lista todos los grupos del catalogo (opcionalmente filtrados por grado)."""
    svc = Container.catalogo_academico_service()
    grupos = svc.listar_grupos(grado=grado)
    return [GrupoResponse.model_validate(g) for g in grupos]


@router.get("/asignaturas", response_model=list[AsignaturaResponse])
def listar_asignaturas(
    area_id: int | None = None,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Lista todas las asignaturas del catalogo (opcionalmente por area)."""
    svc = Container.catalogo_academico_service()
    asignaturas = svc.listar_asignaturas(area_id=area_id)
    return [AsignaturaResponse.model_validate(a) for a in asignaturas]


@router.get("/periodos", response_model=list[PeriodoResponse])
def listar_periodos(
    anio_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Lista los periodos de un anio lectivo."""
    svc = Container.periodo_service()
    periodos = svc.listar_por_anio(anio_id)
    return [PeriodoResponse.model_validate(p) for p in periodos]


@router.get("/periodos/activo", response_model=PeriodoResponse)
def periodo_activo(
    anio_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Retorna el periodo activo del anio lectivo."""
    svc = Container.periodo_service()
    periodo = svc.get_activo(anio_id)
    return PeriodoResponse.model_validate(periodo)


@router.get("/anio-activo")
def anio_activo(
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Retorna la configuracion del anio lectivo activo."""
    svc = Container.configuracion_service()
    config = svc.get_activa()
    return {
        "id": config.id,
        "anio": config.anio,
        "activo": config.activo,
        "institucion_id": config.institucion_id,
        "nota_minima_aprobacion": config.nota_minima_aprobacion,
    }
