# Requisitos: Autenticación de API con JWT (seguridad_web_13)

> **Nivel:** N2 — Con la API REST (Fase 3 del backend_00)
> **Dificultad:** Código-Alto (arquitectura de tokens, revocación, rotación)
> **Depende de:** backend_13_api_auth (el spec de backend ya define el endpoint de login)
> **Relacionado con:** S12 (CORS), S14 (rate limiting de API)

## Contexto del problema

`src/infrastructure/auth/jwt_handler.py` ya existe pero no se usa en producción
(diferido en B4 del épico `seguridad_01..04`). La app web usa cookies de sesión de
NiceGUI; la API REST para Android necesitará JWT. Este spec activa y endurece el
sistema de JWT cuando la API REST exista.

El riesgo principal de JWT mal implementado: tokens que no se pueden revocar (si un
token es robado, el atacante tiene acceso hasta que expire), o tokens con vida larga
(24h+) que amplían la ventana de compromiso.

## Requisitos

### Emisión de tokens

R1: EL ENDPOINT DE LOGIN DE LA API DEBE emitir dos tokens distintos:
    - **Access token**: vida corta (15–30 minutos), usado en cada request a la API.
    - **Refresh token**: vida larga (7–30 días), usado solo para obtener un nuevo
      access token. Nunca enviar el refresh token a endpoints de la API de negocio.

R2: LOS ACCESS TOKENS DEBEN firmarse con HS256 y `JWT_SECRET` (ya existente en
    `config.py`). Si en el futuro hay múltiples servicios que validan tokens,
    migrar a RS256 con clave privada/pública. Documentar la decisión.

R3: EL PAYLOAD DEL TOKEN DEBE incluir como mínimo: `sub` (username o user_id),
    `rol`, `institucion_id`, `exp` (expiración), `iat` (emisión), `jti` (ID único
    del token). El `jti` es necesario para la revocación.

R4: LOS TOKENS NO DEBEN incluir datos sensibles en el payload (passwords, hashes,
    información personal de alumnos). El payload es base64, no cifrado; cualquier
    persona con el token puede decodificarlo.

### Validación

R5: CADA REQUEST A UN ENDPOINT PROTEGIDO DEBE validar: firma del token, expiración
    (`exp`), que el `jti` no esté en la lista de revocación, y que el rol del token
    tenga permiso para el endpoint solicitado.

R6: LA VALIDACIÓN DEBE ocurrir en un middleware centralizado, no en cada endpoint.
    Los endpoints reciben el contexto de usuario ya validado (similar al `route_guard`
    de NiceGUI).

### Revocación

R7: EL SISTEMA DEBE implementar una lista de revocación de tokens (blocklist)
    persistida en Postgres. Cuando un usuario hace logout o cambia su contraseña,
    todos sus tokens activos DEBEN invalidarse inmediatamente.

R8: LA LISTA DE REVOCACIÓN DEBE purgarse automáticamente de entradas con `exp`
    pasada para evitar crecimiento indefinido de la tabla.

R9: EL REFRESH TOKEN DEBE ser de un solo uso: al usarlo para obtener un nuevo
    access token, el refresh token original se invalida y se emite uno nuevo
    (rotación de refresh tokens). Esto permite detectar robo de refresh tokens.

### Almacenamiento en el cliente

R10: LA DOCUMENTACIÓN DE LA API (OpenAPI) DEBE recomendar a los clientes móviles
     almacenar los tokens en almacenamiento seguro del sistema operativo
     (Keychain en iOS, EncryptedSharedPreferences en Android), no en texto claro.

R11: EL SERVIDOR NUNCA DEBE enviar refresh tokens en el cuerpo de una respuesta
     JSON si el cliente es un navegador. Para clientes web, usar cookies
     `HttpOnly; Secure; SameSite=Strict` para el refresh token.

## Criterio de done

- Login en `/api/auth/login` retorna access token (exp 15–30 min) y refresh token.
- Un access token expirado retorna `401 Unauthorized` en cualquier endpoint protegido.
- Logout invalida el token (el mismo token retorna `401` tras el logout).
- Cambio de contraseña invalida todos los tokens activos del usuario.
- Test de rotación de refresh tokens: usar el mismo refresh token dos veces retorna `401`.
