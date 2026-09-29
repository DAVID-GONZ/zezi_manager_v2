from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from src.domain.exceptions import (
    AvedraError,
    ConflictoError,
    NoEncontradoError,
    PermisoDenegadoError,
    ReglaDeNegocioError,
)

_STATUS_MAP: dict[type[AvedraError], int] = {
    NoEncontradoError: 404,
    ConflictoError: 409,
    ReglaDeNegocioError: 422,
    PermisoDenegadoError: 403,
}


async def avedra_error_handler(request: Request, exc: AvedraError) -> JSONResponse:
    status = 400
    for cls, code in _STATUS_MAP.items():
        if isinstance(exc, cls):
            status = code
            break
    return JSONResponse(
        status_code=status,
        content={"detail": str(exc), "code": str(exc.codigo)},
    )
