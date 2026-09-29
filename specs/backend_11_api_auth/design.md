# Diseno: backend_11_api_auth

## Punto de partida medido

| Componente | Estado actual |
|---|---|
| `JWTHandler` | Completo en `src/infrastructure/auth/jwt_handler.py`, stdlib pura, HS256 |
| `BcryptAuthService` | Completo: `autenticar_usuario()` verifica credenciales + estado |
| ContextVars | `contexto_tenant`, `contexto_actor`, `solo_lectura` — 3 ContextVars activas |
| Rate limiting | No existe en la app |
| `config.py` | `JWT_SECRET`, `JWT_EXPIRE_MINUTES` ya definidos |
| Auditoria | `LOGIN` y `ACCESO_DENEGADO` ya emitidos desde NiceGUI (obs_06) |

## D1 — Archivos nuevos

```
src/api/
  auth.py             # Router de autenticacion (/auth/login)
  security.py         # get_current_user, require_role, rate_limiter
  schemas/
    auth.py           # LoginRequest, TokenResponse, CurrentUserDTO
```

## D2 — Endpoint de login (auth.py)

```python
auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request):
    rate_limiter.check(request.client.host)
    try:
        user = Container.auth_service().autenticar_usuario(
            body.username, body.password,
        )
    except ValueError as e:
        if str(e) == "cuenta_inactiva":
            raise HTTPException(403, "cuenta_inactiva")
        raise HTTPException(401, "credenciales_invalidas")

    token = JWTHandler(
        secret=settings.JWT_SECRET,
        expiracion_horas=settings.JWT_EXPIRE_MINUTES / 60,
    ).crear_token({
        "usuario_id": user.id,
        "username": user.username,
        "rol": user.rol.value,
        "institucion_id": user.institucion_id,
    })

    # Auditar
    construir_y_registrar_evento(LOGIN_API, user, request)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )
```

## D3 — Dependencia get_current_user (security.py)

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUserDTO:
    payload = JWTHandler(secret=settings.JWT_SECRET).verificar_token(
        credentials.credentials,
    )
    if payload is None:
        raise HTTPException(401, "Token invalido o expirado")
    user = CurrentUserDTO(**payload)
    # Setear ContextVars para que los servicios funcionen
    _set_context_vars(user)
    return user

def _set_context_vars(user: CurrentUserDTO):
    from src.infrastructure.context.contexto_tenant import _avedra_tenant_var
    from src.infrastructure.context.contexto_actor import _avedra_actor_var
    from src.domain.models.auditoria import ActorContexto

    _avedra_tenant_var.set(user.institucion_id)
    _avedra_actor_var.set(ActorContexto(
        usuario_id=user.usuario_id,
        username=user.username,
        ip=None,  # se llena en el middleware
    ))
```

## D4 — Autorizacion por rol

```python
def require_role(*roles: str):
    async def _check(user: CurrentUserDTO = Depends(get_current_user)):
        if user.rol not in roles:
            raise HTTPException(403, "Rol insuficiente")
        return user
    return _check
```

Uso en endpoint:
```python
@router.get("/usuarios", dependencies=[Depends(require_role("admin"))])
```

## D5 — Rate limiter en memoria

```python
import time
from collections import defaultdict

class InMemoryRateLimiter:
    def __init__(self, max_intentos: int = 5, ventana_seg: int = 300):
        self._intentos: dict[str, list[float]] = defaultdict(list)
        self._max = max_intentos
        self._ventana = ventana_seg

    def check(self, ip: str) -> None:
        ahora = time.monotonic()
        intentos = self._intentos[ip]
        # Purgar viejos
        self._intentos[ip] = [t for t in intentos if ahora - t < self._ventana]
        if len(self._intentos[ip]) >= self._max:
            raise HTTPException(429, "Demasiados intentos. Espere 5 minutos.")
        self._intentos[ip].append(ahora)

    def registrar_fallo(self, ip: str) -> None:
        self._intentos[ip].append(time.monotonic())

rate_limiter = InMemoryRateLimiter()
```

Solo se registra el intento en caso de fallo. El check se invoca antes
de verificar credenciales.

## D6 — ContextVars y middleware

El middleware de IP para la API reutiliza la misma logica de
`request_ip.py` (obs_06). Se aplica como dependencia del router,
no como middleware global (para no afectar NiceGUI):

```python
@api_router.middleware("http")
async def set_request_ip(request: Request, call_next):
    ip = request.client.host if request.client else None
    # Disponible para get_current_user via request.state
    request.state.client_ip = ip
    response = await call_next(request)
    return response
```

## Alternativa descartada

**python-jose o PyJWT como dependencia.** `JWTHandler` ya existe, usa
stdlib pura, esta testeado y no introduce dependencias. No hay razon
para reemplazarlo.
