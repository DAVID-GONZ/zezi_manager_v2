# Seguridad — despliegue y decisiones

> Registro de decisiones de seguridad del épico `seguridad_01..04` y guía de
> despliegue de ZECI Manager v2.0. Complementa `docs/decisions.md`.

## Despliegue con TLS (M2)

NiceGUI (`ui.run`) **no** termina TLS por sí mismo: no expone `ssl_certfile` /
`ssl_keyfile` en el patrón de despliegue de esta app. El patrón correcto es
servir la aplicación **detrás de un reverse proxy** (nginx, Caddy, Traefik) que
termine HTTPS y reenvíe el tráfico ya descifrado a la app local.

Reglas de despliegue en producción:

- **`HOST=127.0.0.1`** — la app escucha solo en loopback, de modo que únicamente
  el reverse proxy de la misma máquina pueda alcanzarla. **Nunca** exponer
  `HOST=0.0.0.0` sin HTTPS por delante: la cookie de sesión de NiceGUI viaja en
  claro y sería interceptable.
- El **reverse proxy** (nginx/Caddy) escucha en `443`, termina TLS con un
  certificado válido (p. ej. Let's Encrypt) y hace `proxy_pass` hacia
  `http://127.0.0.1:8080` (el `PORT` de la app).
- En el arranque, `main()` emite un `logging.warning` cuando `APP_ENV=production`
  recordando este requisito (ver `main.py`).
- Genera cada secreto (`JWT_SECRET`, `STORAGE_SECRET`) con valores aleatorios y
  **distintos** entre sí:

  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

  En producción el arranque se **bloquea** si conservan su valor por defecto
  (ver `config.py`). Detalles en `.env.example`.

Ejemplo mínimo de bloque nginx:

```nginx
server {
    listen 443 ssl;
    server_name zeci.example.org;

    ssl_certificate     /etc/letsencrypt/live/zeci.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/zeci.example.org/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade    $http_upgrade;   # WebSocket de NiceGUI
        proxy_set_header Connection "upgrade";
        proxy_set_header Host       $host;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Decisiones aceptadas / diferidas

### B3 — `check_same_thread=False` (aceptado)

`src/infrastructure/db/connection.py` abre las conexiones SQLite con
`check_same_thread=False`. Es un **requisito de NiceGUI**: el servidor accede a
la conexión desde el pool de hilos de la capa async, por lo que SQLite debe
permitir uso multihilo. **No es una vulnerabilidad**: el acceso sigue
serializado por la lógica de la app y por SQLite. Se acepta como decisión de
arquitectura; sin cambio de código.

### B4 — Revocación de JWT (diferido a la API v3)

`src/.../jwt_handler.py` está preparado para una futura **API REST (v3)** que aún
no existe. La app de escritorio actual **no consume JWT** para autorizar
peticiones (la sesión vive en la cookie firmada de NiceGUI), de modo que hoy no
hay superficie de ataque por tokens no revocables. La lista de revocación /
rotación de JWT se **difiere a v3**, cuando la API exponga endpoints
autenticados por token. Sin cambio de código en v2.

## Estado del épico de seguridad

| ID | Hallazgo | Severidad | Tratamiento | Estado |
|----|----------|-----------|-------------|--------|
| A1 | Hash de contraseñas / política de credenciales | Alto | Código (seguridad_01) | Cerrado |
| A2 | Cambio forzado de contraseña (deny-by-default) | Alto | Código (seguridad_01) | Cerrado |
| M1 | Secretos JWT y de sesión independientes | Medio | Código (seguridad_02) | Cerrado |
| M3 | Configuración / carga de secretos endurecida | Medio | Código (seguridad_02) | Cerrado |
| M4 | Integridad de auditoría (cadena hash) | Medio | Código (seguridad_03) | Cerrado |
| B2 | Hallazgo bajo cerrado en código | Bajo | Código (seguridad_01–03) | Cerrado |
| B1 | Fragilidad del ContextVar (sync de contexto) | Bajo | Código (seguridad_04) — sync central en el guard | Cerrado |
| M2 | Sin TLS a nivel de app | Medio | Despliegue — reverse proxy + doc + warning de arranque | Documentado |
| B3 | `check_same_thread=False` | Bajo | Aceptado — requisito de NiceGUI | Documentado |
| B4 | Revocación de JWT | Bajo | Diferido a la API v3 | Documentado |

### B1 — Sync central del contexto (cerrado en seguridad_04)

El modo solo-lectura ("Ver como") y el scope multi-tenant dependen de que el
contexto de sesión sincronice sus `ContextVar` de servicios
(`solo_lectura` + `institucion`) en cada render. Antes, ese sync dependía de que
**cada página** llamara `SessionContext.desde_storage()`. Ahora el guard central
(`src/interface/auth/route_guard.py`, `_pagina_protegida`) invoca
`SessionContext.desde_storage()` **antes** de renderizar cualquier página
protegida, de modo que toda petición sincroniza el contexto independientemente de
lo que recuerde la página (defensa en profundidad). Un test guardarraíl
(`tests/unit/interface/auth/test_route_guard.py::test_guard_sincroniza_contexto_central`)
verifica vía AST que el guard mantiene esta llamada e impide la regresión.
