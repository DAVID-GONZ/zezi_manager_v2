# Requisitos: Rate limiting de API REST (seguridad_web_14)

> **Nivel:** N2 — Con la API REST (Fase 3 del backend_00)
> **Dificultad:** Código-Bajo (middleware de FastAPI; librería existente)
> **Depende de:** backend_12_fastapi_mount, S12 (CORS), S13 (JWT)
> **Relacionado con:** S05 (throttle de login — diferente objetivo)

## Contexto del problema

El throttle de login (S05) protege el endpoint de autenticación. Este spec protege
el resto de la API REST: un cliente (legítimo o malicioso) que hace 10.000 requests
por minuto puede tumbar el servidor o agotar la conexión a BD, afectando a todos
los usuarios. El rate limiting es la defensa contra abuso de la API, scraping
masivo y ataques de amplificación.

## Requisitos

R1: LA API DEBE aplicar rate limiting por IP y por `jti` de token (usuario autenticado).
    El límite por IP protege endpoints públicos (login, health); el límite por token
    protege endpoints autenticados contra abuso con un token válido.

R2: LOS LÍMITES DEBEN ser configurables vía `config.py` sin modificar código:
    - Endpoints públicos (login): máximo 20 requests/minuto por IP.
    - Endpoints autenticados: máximo 200 requests/minuto por token.
    Valores iniciales; ajustar según el uso real del cliente Android.

R3: UNA PETICIÓN QUE SUPERE EL LÍMITE DEBE recibir `429 Too Many Requests` con
    la cabecera `Retry-After: <segundos>`. La app cliente DEBE implementar backoff
    exponencial basado en esta cabecera.

R4: EL ESTADO DEL RATE LIMITING DEBE persistirse en Postgres o Redis, no en
    memoria del proceso. Mismo argumento que S05: múltiples workers comparten el límite.

R5: EL RATE LIMITING DEBE aplicarse en un middleware de FastAPI, no en cada endpoint.
    Los endpoints no deben conocer la existencia del rate limiting.

R6: LOS ENDPOINTS DE HEALTH CHECK (`/api/health`) DEBEN estar excluidos del rate
    limiting para no bloquear los checks del proveedor cloud.

R7: EL RATE LIMITING DEBE loguear los eventos de throttling con: IP, endpoint,
    token (sin valor completo, solo primeros 8 chars), y timestamp. Esto alimenta
    el sistema de alertas de S09.

## Criterio de done

- 21 requests consecutivos al endpoint de login desde la misma IP retorna `429` en el 21°.
- La cabecera `Retry-After` está presente en las respuestas `429`.
- 201 requests autenticados desde el mismo token retorna `429` en el 201°.
- Reiniciar la app no resetea los contadores (persistencia en BD).
