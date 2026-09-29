"""
Router de Evaluacion — AVEDRA API (backend_12).

Endpoints:
  GET  /evaluacion/planilla        planilla de notas del grupo
  POST /evaluacion/notas-masivas   registrar notas en lote
  GET  /evaluacion/siee            configuracion SIEE del anio
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from container import Container
from src.api.schemas.auth import CurrentUserDTO
from src.api.schemas.evaluacion import (
    ConfiguracionSIEEResponse,
    PlanillaEstudianteResponse,
    RegistrarNotasMasivasRequest,
)
from src.api.security import get_current_user

router = APIRouter(prefix="/evaluacion", tags=["evaluacion"])


@router.get("/planilla", response_model=list[PlanillaEstudianteResponse])
def obtener_planilla(
    grupo_id: int,
    asignacion_id: int,
    periodo_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Retorna la planilla de notas del grupo con definitivas calculadas."""
    svc = Container.evaluacion_service()
    resultados = svc.obtener_planilla(grupo_id, asignacion_id, periodo_id)
    return [PlanillaEstudianteResponse.model_validate(r) for r in resultados]


@router.post("/notas-masivas")
def registrar_notas_masivas(
    body: RegistrarNotasMasivasRequest,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Registra notas para multiples estudiantes en una actividad."""
    from decimal import Decimal

    from src.domain.models.dtos import ContextoAcademicoDTO
    from src.domain.models.evaluacion import RegistrarNotaDTO, RegistrarNotasMasivasDTO

    svc = Container.evaluacion_service()
    notas_dto = [
        RegistrarNotaDTO(
            estudiante_id=n.estudiante_id,
            actividad_id=n.actividad_id,
            valor=Decimal(str(n.valor)),
            usuario_registro_id=user.usuario_id,
        )
        for n in body.notas
    ]
    dto = RegistrarNotasMasivasDTO(
        actividad_id=body.actividad_id,
        notas=notas_dto,
        usuario_registro_id=user.usuario_id,
    )
    ctx = ContextoAcademicoDTO(
        usuario_id=user.usuario_id,
        anio_id=body.anio_id,
        periodo_id=body.periodo_id,
        grupo_id=body.grupo_id,
        asignacion_id=body.asignacion_id,
    )
    guardadas = svc.registrar_notas_masivas(dto, ctx, usuario_id=user.usuario_id)
    return {"guardadas": guardadas}


@router.get("/siee", response_model=ConfiguracionSIEEResponse)
def get_configuracion_siee(
    anio_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Retorna la configuracion SIEE del anio lectivo."""
    svc = Container.evaluacion_service()
    cfg = svc.get_configuracion_siee(anio_id)
    return ConfiguracionSIEEResponse.model_validate(cfg)
