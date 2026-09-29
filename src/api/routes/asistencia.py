"""
Router de Asistencia — AVEDRA API (backend_12).

Endpoints:
  GET  /asistencia/estados         estados del dia por grupo y fecha
  POST /asistencia/masiva          guardar asistencia en lote
  GET  /asistencia/resumen-grupo   resumen por grupo/periodo/asignacion
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from container import Container
from src.api.schemas.asistencia import (
    GuardarAsistenciaMasivaRequest,
    ResumenAsistenciaResponse,
)
from src.api.schemas.auth import CurrentUserDTO
from src.api.security import get_current_user

router = APIRouter(prefix="/asistencia", tags=["asistencia"])


@router.get("/estados")
def estados_por_grupo_y_fecha(
    grupo_id: int,
    asignacion_id: int,
    fecha: date,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """
    Retorna los estados de asistencia registrados para el grupo en la fecha.
    dict[estudiante_id, {estado, observacion}]
    """
    svc = Container.asistencia_service()
    return svc.estados_por_grupo_y_fecha(grupo_id, asignacion_id, fecha)


@router.post("/masiva")
def guardar_masiva(
    body: GuardarAsistenciaMasivaRequest,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Guarda la asistencia de un grupo en una fecha (en lote)."""
    svc = Container.asistencia_service()
    lista = [item.model_dump() for item in body.lista]
    guardados = svc.guardar_asistencia_masiva(
        grupo_id=body.grupo_id,
        asignacion_id=body.asignacion_id,
        periodo_id=body.periodo_id,
        fecha=body.fecha,
        lista=lista,
        usuario_id=user.usuario_id,
    )
    return {"guardados": guardados}


@router.get("/resumen-grupo", response_model=list[ResumenAsistenciaResponse])
def resumen_grupo(
    grupo_id: int,
    asignacion_id: int,
    periodo_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Retorna el resumen de asistencia de todos los estudiantes del grupo."""
    svc = Container.asistencia_service()
    resumenes = svc.resumen_grupo(grupo_id, asignacion_id, periodo_id)
    return [ResumenAsistenciaResponse.model_validate(r) for r in resumenes]
