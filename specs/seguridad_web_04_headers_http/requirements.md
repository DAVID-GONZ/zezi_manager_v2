# Requisitos: Headers HTTP de seguridad (seguridad_web_04)

> **Nivel:** N0 — Bloqueante de deploy
> **Dificultad:** Infra (configuración de proxy; ajuste fino de CSP es S08)
> **Depende de:** S01 (HSTS requiere HTTPS activo)
> **Relacionado con:** S08 (CSP ajustada a NiceGUI — ese spec hace el trabajo fino)

## Contexto del problema

Los headers HTTP de seguridad son la primera línea de defensa del navegador. La mayoría
se configuran en el reverse proxy y no requieren ningún cambio en el código Python.
La excepción es la Content Security Policy (CSP), que necesita ajuste fino con NiceGUI
y Quasar — eso lo cubre S08 por separado.

Este spec establece los headers que DEBEN estar presentes en el primer deploy, usando
valores conservadores que no rompan la app.

## Requisitos

R1: EL REVERSE PROXY DEBE enviar `Strict-Transport-Security: max-age=31536000;
    includeSubDomains` en todas las respuestas HTTPS. Esto instruye al navegador a
    rechazar conexiones HTTP durante un año. Solo activar cuando el dominio tiene TLS
    estable (no revertible fácilmente una vez que los clientes lo cachean).

R2: EL REVERSE PROXY DEBE enviar `X-Content-Type-Options: nosniff` en todas las
    respuestas. Impide que el navegador interprete un archivo con un MIME type
    diferente al declarado (previene ataques MIME sniffing).

R3: EL REVERSE PROXY DEBE enviar `X-Frame-Options: DENY` (o `SAMEORIGIN` si hay
    iframes legítimos de la misma app). Impide que la app sea embebida en iframes
    de otros sitios (previene clickjacking).

R4: EL REVERSE PROXY DEBE enviar `Referrer-Policy: strict-origin-when-cross-origin`.
    Limita la información enviada en la cabecera `Referer` a requests cross-origin,
    previniendo filtrado de URLs internas.

R5: EL REVERSE PROXY DEBE enviar `Permissions-Policy: camera=(), microphone=(),
    geolocation=()`. Deshabilita explícitamente APIs del navegador que la app no usa.

R6: EL REVERSE PROXY NO DEBE enviar la cabecera `Server` con el nombre y versión
    del software (nginx, etc.). Esta información ayuda a los atacantes a identificar
    versiones vulnerables.

R7: EL REVERSE PROXY NO DEBE enviar `X-Powered-By` ni cabeceras similares que
    revelen el stack tecnológico.

R8: UNA HERRAMIENTA AUTOMATIZADA (securityheaders.com en staging, o equivalente
    local como `curl` + script) DEBE verificar la presencia de estos headers antes
    de cada deploy a producción. El check DEBE integrarse con S11 (CI/CD seguro).

R9: LA CONTENT SECURITY POLICY inicial DEBE ser permisiva pero registrar violaciones
    (usar `Content-Security-Policy-Report-Only` con un `report-uri`) hasta que S08
    establezca la política definitiva. Esto evita romper la app mientras se afina la CSP.

## Criterio de done

- `curl -I https://<dominio>` muestra todos los headers listados (R1–R7).
- `securityheaders.com` (o equivalente en staging) reporta grado A o superior,
  salvo por CSP (que estará en Report-Only hasta que S08 esté completo).
- Los headers `Server` y `X-Powered-By` están ausentes de las respuestas.
