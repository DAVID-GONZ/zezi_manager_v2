# tenant_07_middleware_api_tenant — Middleware FastAPI + request.state.tenant

> **Fase 3 del plan de aislamiento multi-tenant.**
> Prepara el terreno para el frontend Vue aislando la logica HTTP de la de
> WebSockets de NiceGUI. El tenant se valida en el middleware y se propaga
> via `request.state.tenant` (stateless, inmutable por request).
>
> **Alineacion con roadmap:** Extiende `backend_10_fastapi_mount`,
> `backend_11_api_auth` y `backend_12_endpoints_crud`.

## Principio: stateless y sin ContextVars

La API REST NO depende de `app.storage.user` ni de `contextvars.ContextVar`.
El middleware extrae el tenant del JWT en cada request y lo inyecta en
`request.state.tenant`. Los endpoints y la session de SQLAlchemy leen
exclusivamente de este objeto inmutable.

Esto elimina la clase de bugs de propagacion de ContextVar que afecta a NiceGUI.

## Scope

```
src/interface/api/                            (NUEVO — paquete API)
src/interface/api/router.py                   (router principal)
src/interface/api/middleware/                  (NUEVO)
src/interface/api/middleware/tenant.py         (middleware de tenant)
src/interface/api/middleware/auth.py           (middleware de JWT)
src/interface/api/deps.py                     (dependencias FastAPI)
src/interface/api/endpoints/                   (NUEVO)
tests/unit/interface/api/test_middleware.py    (NUEVO)
tests/integration/api/test_tenant_api.py      (NUEVO)
```

## Tareas

### T1 — Definir router FastAPI y montarlo en NiceGUI  [ ]

**Corresponde a roadmap `backend_10_fastapi_mount`.**

```python
# src/interface/api/router.py
from fastapi import FastAPI

api_app = FastAPI(
    title="ZECI Manager API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
```

En `main.py`, montar paralelo a NiceGUI:
```python
from src.interface.api.router import api_app
app.mount("/api", api_app)
```

**Verificacion:** `GET /api/docs` muestra Swagger UI.

### T2 — Modelo TenantContext inmutable  [ ]

```python
# src/interface/api/middleware/tenant.py
from dataclasses import dataclass

@dataclass(frozen=True)
class TenantContext:
    """Contexto de tenant validado, inmutable por request."""
    institucion_id: int
    usuario_id: int
    rol: str

    @property
    def es_admin(self) -> bool:
        return self.rol == "admin"

    @property
    def scope(self) -> int | None:
        """None para admin (cross-tenant), int para tenant scopeado."""
        return None if self.es_admin else self.institucion_id
```

**Verificacion:** Unit test de TenantContext.

### T3 — Middleware de autenticacion JWT  [ ]

**Corresponde a roadmap `backend_11_api_auth`.**

```python
# src/interface/api/middleware/auth.py
from starlette.middleware.base import BaseHTTPMiddleware

class JWTTenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Rutas publicas (login, health) no requieren JWT
        if request.url.path in ("/api/health", "/api/auth/login"):
            return await call_next(request)

        # Extraer y verificar JWT
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Token requerido"})

        token = auth_header.removeprefix("Bearer ")
        try:
            payload = verify_jwt(token)  # reusa AuthService existente
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Token invalido"})

        # Construir TenantContext inmutable
        request.state.tenant = TenantContext(
            institucion_id=payload["institucion_id"],
            usuario_id=payload["sub"],
            rol=payload["rol"],
        )

        return await call_next(request)
```

**Verificacion:** Test con JWT valido → request.state.tenant poblado.
Test con JWT invalido → 401.

### T4 — Dependencia FastAPI para inyectar tenant  [ ]

```python
# src/interface/api/deps.py
from fastapi import Request, Depends

def get_tenant(request: Request) -> TenantContext:
    """Dependencia que extrae el TenantContext del request."""
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(401, "No autenticado")
    return tenant

def get_tenant_scope(tenant: TenantContext = Depends(get_tenant)) -> int | None:
    """Scope para pasar al ORM: None=admin, int=tenant."""
    return tenant.scope
```

Los endpoints lo usan como dependencia:
```python
@router.get("/usuarios")
async def listar_usuarios(tenant: TenantContext = Depends(get_tenant)):
    ...
```

**Verificacion:** Endpoint responde con tenant inyectado.

### T5 — Conectar middleware con session SQLAlchemy  [ ]

El `api_tenant_provider` de tenant_06 lee de `request.state.tenant`:

```python
# Registrar como el provider de la session para requests API
def api_tenant_provider() -> int | None:
    # Leer del contexto de request actual (via contextvars o starlette)
    from starlette.requests import Request
    # ... obtener request actual del scope de la task
    return request.state.tenant.scope
```

**Alternativa (mas limpia):** Usar `contextvars` solo como puente entre el
middleware y el ORM hook, pero seteado por el middleware (no por app.storage):

```python
# En el middleware:
_api_tenant_var: ContextVar[int | None] = ContextVar("api_tenant", default=None)

class JWTTenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ...
        _api_tenant_var.set(tenant_context.scope)
        response = await call_next(request)
        _api_tenant_var.set(None)
        return response
```

**Decision:** Se define durante la implementacion de tenant_06 segun si se usa
Core o Declarative.

**Verificacion:** Query desde un endpoint API → automaticamente filtrada por tenant.

### T6 — Endpoint de health y login  [ ]

```python
@api_app.get("/api/health")
async def health():
    return {"status": "ok"}

@api_app.post("/api/auth/login")
async def login(credentials: LoginDTO):
    # Reusa Container.auth_service().autenticar_usuario()
    # Retorna JWT con institucion_id, rol, usuario_id
    ...
```

**Verificacion:** Login retorna JWT; health responde sin auth.

### T7 — Tests de aislamiento en la API  [ ]

En `tests/integration/api/test_tenant_api.py`:

1. **test_request_sin_jwt_rechazado:** GET /api/usuarios sin header → 401.
2. **test_jwt_institucion_A_solo_ve_A:** Login como director A, listar usuarios
   → solo usuarios de A.
3. **test_jwt_institucion_B_no_ve_A:** Login como director B → 0 usuarios de A.
4. **test_admin_ve_todos:** Login como admin → usuarios de A y B.
5. **test_jwt_expirado_rechazado:** Token con expiracion pasada → 401.
6. **test_tenant_no_puede_crear_en_otro:** Director A intenta crear usuario
   con institucion_id=B → rechazado (403 o validacion).

**Verificacion:** `python -m pytest tests/integration/api/test_tenant_api.py -v`

## Criterio de done
- [ ] Router FastAPI montado y `/api/docs` accesible
- [ ] Middleware JWT extrae y valida tenant en cada request
- [ ] `request.state.tenant` es TenantContext inmutable
- [ ] Dependencia FastAPI inyecta tenant en endpoints
- [ ] Session SQLAlchemy lee tenant del middleware (no de ContextVar global)
- [ ] Endpoint de health y login funcionando
- [ ] 6 tests de aislamiento en API verdes
- [ ] OpenAPI spec exportable (contrato para Vue)
- [ ] NiceGUI sigue funcionando en paralelo sin cambios
- [ ] `python init.py` verde
