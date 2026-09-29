"""
Router de Informes — AVEDRA API (backend_12).

Endpoints:
  GET /informes/boletin-periodo/{estudiante_id}  boletin PDF por periodo
  GET /informes/boletin-anual/{estudiante_id}    boletin PDF anual
  GET /informes/notas                            informe de notas (Excel/PDF)
  GET /informes/asistencia                       informe de asistencia (Excel/PDF)
"""

from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from container import Container
from src.api.schemas.auth import CurrentUserDTO
from src.api.security import get_current_user

router = APIRouter(prefix="/informes", tags=["informes"])


@router.get("/boletin-periodo/{estudiante_id}")
def boletin_periodo(
    estudiante_id: int,
    grupo_id: int,
    periodo_id: int,
    formato: str = "pdf",
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Genera el boletin de un estudiante para un periodo (PDF o Excel)."""
    bytes_doc = Container.informe_service().generar_boletin_periodo(
        estudiante_id, grupo_id, periodo_id, formato=formato
    )
    media_type = "application/pdf" if formato == "pdf" else (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    ext = "pdf" if formato == "pdf" else "xlsx"
    return StreamingResponse(
        io.BytesIO(bytes_doc),
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=boletin_{estudiante_id}_p{periodo_id}.{ext}"
            )
        },
    )


@router.get("/boletin-anual/{estudiante_id}")
def boletin_anual(
    estudiante_id: int,
    grupo_id: int,
    anio_id: int,
    formato: str = "pdf",
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Genera el boletin anual de un estudiante (PDF o Excel)."""
    bytes_doc = Container.informe_service().generar_boletin_anual(
        estudiante_id, grupo_id, anio_id, formato=formato
    )
    media_type = "application/pdf" if formato == "pdf" else (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    ext = "pdf" if formato == "pdf" else "xlsx"
    return StreamingResponse(
        io.BytesIO(bytes_doc),
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=boletin_anual_{estudiante_id}_{anio_id}.{ext}"
            )
        },
    )


@router.get("/notas")
def informe_notas(
    grupo_id: int,
    asignacion_id: int,
    periodo_id: int,
    fecha_desde: date,
    fecha_hasta: date,
    formato: str = "excel",
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Genera el informe de notas del grupo (Excel o PDF)."""
    from src.domain.models.dtos import FormatoInforme, InformeNotasDTO

    dto = InformeNotasDTO(
        grupo_id=grupo_id,
        asignacion_id=asignacion_id,
        periodo_id=periodo_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        formato=FormatoInforme(formato),
    )
    bytes_doc = Container.informe_service().generar_notas(dto)
    media_type = "application/pdf" if formato == "pdf" else (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    ext = "pdf" if formato == "pdf" else "xlsx"
    return StreamingResponse(
        io.BytesIO(bytes_doc),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=notas_p{periodo_id}.{ext}"},
    )


@router.get("/asistencia")
def informe_asistencia(
    grupo_id: int,
    asignacion_id: int,
    periodo_id: int,
    fecha_desde: date,
    fecha_hasta: date,
    formato: str = "excel",
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Genera el informe de asistencia del grupo (Excel o PDF)."""
    from src.domain.models.dtos import FormatoInforme, InformeAsistenciaDTO

    dto = InformeAsistenciaDTO(
        grupo_id=grupo_id,
        asignacion_id=asignacion_id,
        periodo_id=periodo_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        formato=FormatoInforme(formato),
    )
    bytes_doc = Container.informe_service().generar_asistencia(dto)
    media_type = "application/pdf" if formato == "pdf" else (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    ext = "pdf" if formato == "pdf" else "xlsx"
    return StreamingResponse(
        io.BytesIO(bytes_doc),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=asistencia_p{periodo_id}.{ext}"},
    )
