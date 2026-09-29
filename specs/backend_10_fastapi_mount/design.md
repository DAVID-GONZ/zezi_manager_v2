# Diseno: backend_10_fastapi_mount

## Punto de partida medido

| Componente | Estado actual |
|---|---|
| `main.py` | `registrar_rutas_internas(app)` ya recibe el `app` FastAPI |
| `/health` | Existe en `main.py:87`, directo en el app raiz |
| `src/api/` | No existe (se crea como hermano de `src/interface/`) |
| CORS | No configurado |
| OpenAPI docs | NiceGUI las desactiva por defecto |
| `requirements.txt` | No incluye `python-multipart` (necesario para form data) |

## D1 — Estructura de archivos

```
src/api/
  __init__.py
  router.py          # APIRouter raiz con prefijo /api/v1
  deps.py            # get_engine(), get_service() como Depends
  errors.py          # Exception handlers para AvedraError
  schemas/
    __init__.py
    common.py         # HealthResponse, ErrorResponse, PaginatedResponse
```

## D2 — Router raiz

```python
# src/api/router.py
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")

@api_router.get("/health", response_model=HealthResponse)
def health():
    ...
```

El router se registra en `main.py` dentro de `registrar_rutas_internas()`:

```python
from src.api.router import api_router
app.include_router(api_router)
```

## D3 — Dependencias compartidas (deps.py)

```python
from container import Container

def get_engine():
    return Container.engine()

def get_auth_service():
    return Container.auth_service()

# Patron: una funcion por servicio, invocada via Depends.
# No inyectar Container directo para testabilidad.
```

## D4 — Manejo de errores (errors.py)

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from src.domain.exceptions import (
    AvedraError, NoEncontradoError, ReglaDeNegocioError,
    ConflictoError, PermisoDenegadoError,
)

STATUS_MAP = {
    NoEncontradoError: 404,
    ConflictoError: 409,
    ReglaDeNegocioError: 422,
    PermisoDenegadoError: 403,
}

async def avedra_error_handler(request: Request, exc: AvedraError):
    status = STATUS_MAP.get(type(exc), 400)
    return JSONResponse(
        status_code=status,
        content={"detail": str(exc), "code": exc.codigo},
    )
```

Se registra en main.py:
```python
from src.api.errors import avedra_error_handler
app.add_exception_handler(AvedraError, avedra_error_handler)
```

## D5 — CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`config.py` anade:
```python
CORS_ORIGINS: list[str] = Field(
    default=["http://localhost:5173"],
    description="Origenes permitidos para CORS.",
)
```

## D6 — OpenAPI docs

NiceGUI arranca con `docs_url=None` internamente. Se habilitan
configurando las URLs en el router o en el app despues de NiceGUI:

```python
app.docs_url = "/api/docs"
app.redoc_url = "/api/redoc"
app.openapi_url = "/api/openapi.json"
```

Nota: NiceGUI >=2.x expone `app` antes de `ui.run()`. Si hay conflicto,
el endpoint de OpenAPI se sirve manualmente desde el router.

## Alternativa descartada

**App FastAPI separada montada como sub-aplicacion.** Complicaria el
deploy (dos procesos o mount ASGI) sin beneficio: NiceGUI ya ES FastAPI.
