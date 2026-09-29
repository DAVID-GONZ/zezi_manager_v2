"""
Router de Estudiantes — AVEDRA API (backend_12).

Endpoints:
  GET    /estudiantes          listar estudiantes (filtros: grupo_id, estado)
  POST   /estudiantes          matricular estudiante
  GET    /estudiantes/{id}     obtener por id
  PUT    /estudiantes/{id}     actualizar estudiante
  POST   /estudiantes/{id}/retirar     retirar estudiante
  POST   /estudiantes/carga-masiva     carga CSV multipart
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, UploadFile

from container import Container
from src.api.deps import PaginationParams
from src.api.schemas.auth import CurrentUserDTO
from src.api.schemas.common import PaginatedResponse
from src.api.schemas.estudiantes import (
    ActualizarEstudianteRequest,
    CargaMasivaResponse,
    EstudianteResponse,
    NuevoEstudianteRequest,
    RetirarEstudianteRequest,
)
from src.api.security import get_current_user, require_role

router = APIRouter(prefix="/estudiantes", tags=["estudiantes"])


@router.get("", response_model=PaginatedResponse[EstudianteResponse])
def listar_estudiantes(
    grupo_id: int | None = None,
    estado: str | None = None,
    pagination: PaginationParams = Depends(),  # noqa: B008
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Lista estudiantes con filtros opcionales."""
    from src.domain.models.estudiante import EstadoMatricula, FiltroEstudiantesDTO

    svc = Container.estudiante_service()
    estado_enum = EstadoMatricula(estado) if estado is not None else None
    filtro = FiltroEstudiantesDTO(grupo_id=grupo_id, estado_matricula=estado_enum)
    todos = svc.listar_filtrado(filtro)
    page_items = todos[pagination.offset : pagination.offset + pagination.per_page]
    return PaginatedResponse(
        items=[EstudianteResponse.model_validate(e) for e in page_items],
        total=len(todos),
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.post("", response_model=EstudianteResponse, status_code=201)
def matricular_estudiante(
    body: NuevoEstudianteRequest,
    user: CurrentUserDTO = Depends(require_role("admin", "director", "coordinador")),  # noqa: B008
):
    """Matricula un estudiante nuevo."""
    from src.domain.models.estudiante import NuevoEstudianteDTO, TipoDocumento

    svc = Container.estudiante_service()
    dto = NuevoEstudianteDTO(
        tipo_documento=TipoDocumento(body.tipo_documento),
        numero_documento=body.numero_documento,
        nombre=body.nombre,
        apellido=body.apellido,
        genero=body.genero,
        fecha_nacimiento=body.fecha_nacimiento,
        direccion=body.direccion,
        grupo_id=body.grupo_id,
    )
    nuevo = svc.matricular(dto, usuario_id=user.usuario_id, actor_rol=user.rol)
    return EstudianteResponse.model_validate(nuevo)


@router.get("/{estudiante_id}", response_model=EstudianteResponse)
def obtener_estudiante(
    estudiante_id: int,
    user: CurrentUserDTO = Depends(get_current_user),  # noqa: B008
):
    """Obtiene un estudiante por id."""
    svc = Container.estudiante_service()
    obj = svc.get_by_id(estudiante_id)
    return EstudianteResponse.model_validate(obj)


@router.put("/{estudiante_id}", response_model=EstudianteResponse)
def actualizar_estudiante(
    estudiante_id: int,
    body: ActualizarEstudianteRequest,
    user: CurrentUserDTO = Depends(require_role("admin", "director", "coordinador")),  # noqa: B008
):
    """Actualiza datos de un estudiante."""
    from src.domain.models.estudiante import ActualizarEstudianteDTO

    svc = Container.estudiante_service()
    dto = ActualizarEstudianteDTO(
        nombre=body.nombre,
        apellido=body.apellido,
        genero=body.genero,
        fecha_nacimiento=body.fecha_nacimiento,
        direccion=body.direccion,
        grupo_id=body.grupo_id,
        posee_piar=body.posee_piar,
    )
    actualizado = svc.actualizar(
        estudiante_id, dto, usuario_id=user.usuario_id, actor_rol=user.rol
    )
    return EstudianteResponse.model_validate(actualizado)


@router.post("/{estudiante_id}/retirar", response_model=EstudianteResponse)
def retirar_estudiante(
    estudiante_id: int,
    body: RetirarEstudianteRequest,
    user: CurrentUserDTO = Depends(require_role("admin", "director", "coordinador")),  # noqa: B008
):
    """Retira un estudiante del establecimiento."""
    svc = Container.estudiante_service()
    resultado = svc.retirar(estudiante_id, motivo=body.motivo, usuario_id=user.usuario_id)
    return EstudianteResponse.model_validate(resultado)


@router.post("/carga-masiva", response_model=CargaMasivaResponse, status_code=201)
async def carga_masiva(
    file: UploadFile = File(...),  # noqa: B008
    user: CurrentUserDTO = Depends(require_role("admin", "director", "coordinador")),  # noqa: B008
):
    """Carga masiva de estudiantes desde CSV."""
    contenido = await file.read()
    reader = csv.DictReader(io.StringIO(contenido.decode("utf-8-sig")))
    filas = list(reader)
    grupos = Container.catalogo_academico_service().listar_grupos()
    mapa = {g.nombre: g.id for g in grupos}
    resultado = Container.estudiante_service().matricular_masivo_csv(
        filas, mapa, usuario_id=user.usuario_id, actor_rol=user.rol
    )
    return CargaMasivaResponse(insertados=resultado.exitosas, errores=resultado.errores)
