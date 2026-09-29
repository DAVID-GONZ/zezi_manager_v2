from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config import settings
from src.api.schemas.common import HealthResponse

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", response_model=HealthResponse)
def health():
    from src.infrastructure.db.connection import verify_db_integrity

    ok = verify_db_integrity()
    if not ok:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "version": settings.APP_VERSION},
        )
    return HealthResponse(status="ok", version=settings.APP_VERSION)


# --- Documentación (fuera del versionado) ---

docs_router = APIRouter(prefix="/api")


@docs_router.get("/openapi.json", include_in_schema=False)
def openapi_spec(request: Request):
    return JSONResponse(content=request.app.openapi())


@docs_router.get("/docs", include_in_schema=False)
def swagger_ui(request: Request):
    from fastapi.openapi.docs import get_swagger_ui_html

    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title=f"{settings.APP_NAME} API",
    )


@docs_router.get("/redoc", include_in_schema=False)
def redoc_ui(request: Request):
    from fastapi.openapi.docs import get_redoc_html

    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title=f"{settings.APP_NAME} API",
    )
