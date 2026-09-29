# Requisitos: backend_11_api_auth

> Ambito: autenticacion JWT para la API REST, independiente de la sesion
> NiceGUI. Reusa `JWTHandler` (`src/infrastructure/auth/jwt_handler.py`)
> y `BcryptAuthService` existentes. No modifica la autenticacion de NiceGUI.
>
> DEPENDE de backend_10: el router `/api/v1` debe estar montado.

---

## Endpoint de login

R1: EL SISTEMA DEBE exponer `POST /api/v1/auth/login` que recibe
    `{"username": "...", "password": "..."}` y retorna:
    - 200 `{"access_token": "<jwt>", "token_type": "bearer", "expires_in": <seg>}`
    - 401 `{"detail": "credenciales_invalidas"}` si falla.
    - 403 `{"detail": "cuenta_inactiva"}` si la cuenta esta desactivada.

R2: EL token JWT DEBE contener: `usuario_id`, `username`, `rol`,
    `institucion_id`, `iat`, `exp`. No incluir datos sensibles
    (password_hash, email, nombre completo).

R3: EL login DEBE auditar el evento LOGIN_API via AuditoriaService,
    con IP y username, usando los mismos mecanismos de obs_06.

---

## Dependencia de autenticacion

R4: EL SISTEMA DEBE proveer una dependencia FastAPI `get_current_user`
    que:
    - Extrae el token del header `Authorization: Bearer <token>`.
    - Verifica firma y expiracion via `JWTHandler.verificar_token()`.
    - Retorna un DTO con `usuario_id`, `username`, `rol`, `institucion_id`.
    - Lanza `HTTPException(401)` si el token es invalido o ausente.

R5: LA dependencia DEBE setear las ContextVars de tenant, actor y
    solo_lectura antes de que el endpoint ejecute, para que los
    servicios funcionen identico que bajo NiceGUI.

---

## Autorizacion por rol

R6: EL SISTEMA DEBE proveer una dependencia `require_role(*roles)`
    parametrizable que verifique que el rol del usuario esta en la
    lista permitida. Lanza 403 si no.

R7: LA matriz de roles por endpoint API DEBE replicar la de las rutas
    NiceGUI (`main.py` lineas 125-130). Un endpoint de admin no es
    accesible para un profesor.

---

## Seguridad

R8: EL endpoint de login DEBE aplicar rate limiting basico: maximo
    5 intentos fallidos por IP en 5 minutos. Retorna 429 al exceder.
    Implementacion en memoria (dict con TTL), sin Redis.

R9: EL token NO DEBE incluir informacion PII mas alla del username.
    Ni email, ni nombre completo, ni datos del estudiante.

R10: LA expiracion del token DEBE respetar `JWT_EXPIRE_MINUTES` de
     `config.py` (default 480 = 8 horas, jornada escolar).

---

## Fuera de alcance

- Refresh tokens (se anade cuando haya frontend Vue que lo consuma).
- OAuth2 / SSO (posterior).
- Modificar la autenticacion de NiceGUI (cookie/storage).
