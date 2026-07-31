# Requisitos: TLS + Reverse Proxy (seguridad_web_01)

> **Nivel:** N0 — Bloqueante de deploy
> **Dificultad:** Infra (cero código Python)
> **Depende de:** ningún otro spec
> **Bloquea a:** S03 (cookies Secure requieren HTTPS activo)

## Contexto del problema

NiceGUI no termina TLS por sí mismo. Sin HTTPS la cookie de sesión viaja en claro
y puede ser interceptada por cualquiera en la red. Adicionalmente, los WebSockets de
NiceGUI y el futuro canal de tiempo real requieren `wss://`, que solo existe sobre TLS.
La app debe escuchar únicamente en loopback; el proxy es el único punto de entrada público.

Este control ya está documentado en `docs/seguridad.md` §"Despliegue con TLS (M2)".
Este spec lo formaliza como requisito verificable para el deploy en Postgres/cloud.

## Requisitos

R1: EL SISTEMA DEBE terminar TLS en un reverse proxy (nginx, Caddy o Traefik) con
    un certificado válido (Let's Encrypt u equivalente), escuchando en el puerto 443.
    La app Python NUNCA expone TLS directamente.

R2: LA CONFIGURACIÓN DEBE hacer que la app escuche exclusivamente en `HOST=127.0.0.1`
    en producción, de modo que sea inaccesible desde la red sin pasar por el proxy.

R3: EL REVERSE PROXY DEBE redirigir todo el tráfico HTTP (puerto 80) a HTTPS (443)
    con código 301. Ninguna página debe servirse en claro.

R4: EL PROXY DEBE pasar las cabeceras `Upgrade: websocket` y `Connection: upgrade`
    hacia la app para que los WebSockets de NiceGUI funcionen sobre TLS.

R5: EL PROXY DEBE pasar `X-Forwarded-For` y `X-Forwarded-Proto` para que la app
    pueda reconstruir la IP real del cliente (necesario para S09 — logging) y detectar
    si la petición llegó por HTTPS.

R6: EL CERTIFICADO DEBE renovarse automáticamente antes de su expiración. La caída
    del certificado debe provocar una alerta, no un deploy manual de emergencia.

R7: LA CONFIGURACIÓN DEBE deshabilitar protocolos TLS obsoletos (TLS 1.0, TLS 1.1)
    y suites de cifrado débiles. Solo TLS 1.2 y TLS 1.3 son aceptables.

R8: EL ENTORNO de staging DEBE tener TLS activo antes de que lo tenga producción,
    de modo que el comportamiento de cookies y WebSockets pueda verificarse con HTTPS
    real antes del primer deploy a prod.

## Criterio de done

- `curl -I http://<dominio>` devuelve `301 Moved Permanently` hacia `https://`.
- `curl -I https://<dominio>` devuelve `200 OK` y la cookie de sesión lleva `Secure`.
- `ssllabs.com/ssltest` o `testssl.sh` reporta grado A o superior.
- La conexión WebSocket funciona sobre `wss://`.
- La renovación automática del certificado está probada (dry-run de certbot o equivalente).