# Requisitos: CORS para API REST (seguridad_web_12)

> **Nivel:** N2 — Con la API REST (Fase 3 del backend_00)
> **Dificultad:** Config (configuración de FastAPI/Starlette; mínimo código)
> **Depende de:** backend_12_fastapi_mount (endpoint `/api/` existente)
> **Bloquea a:** S13, S14 (la API necesita CORS antes de exponerse)

## Contexto del problema

Cuando FastAPI se monta en el proceso NiceGUI (`backend_12`), queda expuesto bajo
el mismo dominio pero en rutas `/api/*`. Los clientes de la API (app Android, futura
web React) hacen peticiones cross-origin. Sin CORS configurado, el navegador bloquea
las respuestas. Con CORS mal configurado (`Allow-Origin: *` + credenciales), cualquier
sitio web puede hacer peticiones autenticadas a la API en nombre del usuario.

## Requisitos

R1: LA CONFIGURACIÓN CORS DEBE listar explícitamente los orígenes permitidos
    (`allow_origins`). Está prohibido usar `["*"]` junto con `allow_credentials=True`.
    Esa combinación es ignorada por los navegadores modernos y en algunos contextos
    expone la API completa.

R2: LOS ORÍGENES PERMITIDOS DEBEN configurarse vía variable de entorno (p. ej.
    `CORS_ORIGINS=https://app.zeci.edu,https://staging.zeci.edu`), no hardcodeados.
    Esto permite añadir orígenes en staging sin tocar el código.

R3: SI LA API USA JWT BEARER TOKENS (sin cookies), `allow_credentials` PUEDE ser
    `False`. Si la API usa cookies de sesión, `allow_credentials=True` es necesario
    pero los orígenes deben ser explícitos (R1).

R4: `allow_methods` DEBE listar solo los métodos HTTP que la API realmente usa.
    No incluir métodos como `PATCH` o `DELETE` si la API no los implementa.

R5: `allow_headers` DEBE listar solo los headers que el cliente necesita enviar
    (`Authorization`, `Content-Type`, `X-Request-ID`). No usar `["*"]`.

R6: LA RUTA `/api/` DEBE tener su propia política CORS, separada de la de NiceGUI.
    NiceGUI no necesita CORS (sirve al navegador directamente, no cross-origin).

R7: LAS RUTAS INTERNAS DE NICEGUI (WebSocket, assets) NO DEBEN tener CORS
    habilitado. El middleware CORS DEBE aplicarse solo a `/api/*`.

R8: DEBE existir un test de integración que verifique que una petición OPTIONS
    desde un origen no permitido recibe `403` o no incluye `Access-Control-Allow-Origin`.

## Criterio de done

- `curl -H "Origin: https://malicioso.com" -I https://<dominio>/api/health`
  no retorna `Access-Control-Allow-Origin`.
- `curl -H "Origin: https://app.zeci.edu" -I https://<dominio>/api/health`
  retorna `Access-Control-Allow-Origin: https://app.zeci.edu`.
- Test de integración de CORS verde.
