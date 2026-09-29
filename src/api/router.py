from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config import settings
from src.api.auth import auth_router
from src.api.routes.asistencia import router as asistencia_router
from src.api.routes.auditoria import router as auditoria_router
from src.api.routes.configuracion import router as configuracion_router
from src.api.routes.contexto import router as contexto_router
from src.api.routes.convivencia import router as convivencia_router
from src.api.routes.estudiantes import router as estudiantes_router
from src.api.routes.evaluacion import router as evaluacion_router
from src.api.routes.informes import router as informes_router
from src.api.routes.usuarios import router as usuarios_router
from src.api.schemas.common import HealthResponse

api_router = APIRouter(prefix="/api/v1")

# --- Autenticacion JWT (backend_11) ---
api_router.include_router(auth_router)

# --- Modulos CRUD (backend_12, OLA 1) ---
api_router.include_router(usuarios_router)
api_router.include_router(estudiantes_router)
api_router.include_router(contexto_router)

# --- Modulos CRUD (backend_12, OLA 2) ---
api_router.include_router(asistencia_router)
api_router.include_router(convivencia_router)
api_router.include_router(evaluacion_router)

# --- Modulos CRUD (backend_12, OLA 3) ---
api_router.include_router(informes_router)
api_router.include_router(configuracion_router)
api_router.include_router(auditoria_router)


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
