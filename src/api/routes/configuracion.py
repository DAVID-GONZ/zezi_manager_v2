"""
Router de Configuracion — AVEDRA API (backend_12).

Endpoints:
  GET  /configuracion/anio-activo              configuracion del anio activo
  GET  /configuracion/info-institucional/{id}  info institucional del anio
  PUT  /configuracion/info-institucional/{id}  actualizar info institucional
  GET  /configuracion/niveles/{anio_id}        niveles de desempeno del anio
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from container import Container
from src.api.schemas.auth import CurrentUserDTO
from src.api.schemas.configuracion import (
    ActualizarInfoInstitucionalRequest,
    ConfiguracionAnioResponse,
)
from src.api.security import get_current_user, require_role

router = APIRouter(prefix="/configuracion", tags=["configuracion"])


@router.get("/anio-activo", response_model=ConfiguracionAnioResponse)
def get_anio_activo(
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Retorna la configuracion del anio lectivo activo de la institucion."""
    svc = Container.configuracion_service()
    config = svc.get_activa()
    return ConfiguracionAnioResponse.model_validate(config)


@router.get("/info-institucional/{anio_id}")
def get_info_institucional(
    anio_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Retorna la informacion institucional del anio lectivo."""
    svc = Container.configuracion_service()
    info = svc.get_info_institucional(anio_id)
    return info.model_dump() if hasattr(info, "model_dump") else dict(info)


@router.put("/info-institucional/{anio_id}", response_model=ConfiguracionAnioResponse)
def actualizar_info_institucional(
    anio_id: int,
    body: ActualizarInfoInstitucionalRequest,
    user: CurrentUserDTO = Depends(require_role("admin", "director")),  # noqa: B008
):
    """Actualiza la informacion institucional del anio lectivo."""
    from src.domain.models.configuracion import ActualizarInfoInstitucionalDTO

    svc = Container.configuracion_service()
    dto = ActualizarInfoInstitucionalDTO(
        nombre_institucion=body.nombre_institucion,
        dane_code=body.dane_code,
        rector=body.rector,
        municipio=body.municipio,
        direccion=body.direccion,
    )
    config_actualizada = svc.actualizar_info_institucional(anio_id, dto)
    return ConfiguracionAnioResponse.model_validate(config_actualizada)


@router.get("/niveles/{anio_id}")
def listar_niveles(
    anio_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Lista los niveles de desempeno configurados para el anio."""
    svc = Container.configuracion_service()
    niveles = svc.listar_niveles(anio_id)
    return [
        {"id": n.id, "nombre": n.nombre, "rango_min": n.rango_min, "rango_max": n.rango_max}
        for n in niveles
    ]
