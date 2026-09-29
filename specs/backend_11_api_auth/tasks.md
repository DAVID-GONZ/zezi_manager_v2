# Tareas: backend_11_api_auth

> SCOPE — archivos que pueden editarse:
> `src/api/auth.py` (crear), `src/api/security.py` (crear),
> `src/api/schemas/auth.py` (crear), `src/api/router.py`,
> `main.py`, `config.py`.
>
> Fuera de scope: `BcryptAuthService`, `JWTHandler`, paginas NiceGUI,
> servicios de dominio. Si una tarea exige tocar algo de ahi -> PARAR.
>
> DEPENDE de backend_10.

---

## T1 — Schemas de autenticacion

Crear `src/api/schemas/auth.py`:
- `LoginRequest(username: str, password: str)`
- `TokenResponse(access_token: str, token_type: str, expires_in: int)`
- `CurrentUserDTO(usuario_id: int, username: str, rol: str, institucion_id: int | None)`

**Verificacion:** importar y construir cada schema sin errores.

---

## T2 — Rate limiter en memoria

Crear `InMemoryRateLimiter` en `src/api/security.py` segun D5.
Instanciar como singleton del modulo.

**Verificacion:** test unitario: 5 fallos -> 6to lanza 429.

---

## T3 — Dependencia get_current_user

Implementar `get_current_user` en `security.py` segun D3.
Incluir `_set_context_vars` que sincroniza las 3 ContextVars.

**Verificacion:** test con token valido retorna CurrentUserDTO.
Test con token invalido lanza 401.

---

## T4 — Dependencia require_role

Implementar `require_role(*roles)` en `security.py` segun D4.

**Verificacion:** test con rol correcto pasa, rol incorrecto lanza 403.

---

## T5 — Endpoint POST /auth/login

Crear `src/api/auth.py` con `auth_router` segun D2.
Incluir:
- Verificacion de rate limiter.
- Llamada a `autenticar_usuario()`.
- Generacion de token con `JWTHandler`.
- Emision de evento LOGIN_API en auditoria.

Registrar `auth_router` en el `api_router` de `router.py`.

**Verificacion:** `curl -X POST http://localhost:8080/api/v1/auth/login
-H "Content-Type: application/json"
-d '{"username":"admin","password":"admin123"}'`
retorna `{"access_token": "...", ...}`.

---

## T6 — Middleware de IP para API

Anadir middleware al api_router que capture `request.client.host`
y lo haga disponible via `request.state.client_ip` segun D6.
`get_current_user` lo lee y lo pasa al ActorContexto.

**Verificacion:** el evento LOGIN_API registra la IP del cliente.

---

## T7 — CORS_ORIGINS en config.py

Anadir `CORS_ORIGINS: list[str]` a `config.py` con default
`["http://localhost:5173"]`. Documentar en `.env.example`.

Si backend_10 ya lo hizo, verificar que existe y no duplicar.

---

## T8 — Tests de integracion de auth

Crear `tests/unit/interface/api/test_api_auth.py`:
- Test login exitoso retorna 200 + token valido.
- Test login fallido retorna 401.
- Test cuenta inactiva retorna 403.
- Test rate limiting: 6 fallos rapidos retorna 429.
- Test endpoint protegido sin token retorna 401.
- Test endpoint protegido con rol incorrecto retorna 403.

Usar `fastapi.testclient.TestClient` contra el app.

---

## T9 — Verificacion de no regresion y cierre

```
.venv/Scripts/python.exe scripts/init.py
```
TODO VERDE. Login NiceGUI no se ve afectado. Login API funciona.

**Artefacto:** `progress/impl_backend_11.md`.
