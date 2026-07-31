# Requisitos: Cookies de sesión seguras (seguridad_web_03)

> **Nivel:** N0 — Bloqueante de deploy
> **Dificultad:** Código-Bajo (configuración del arranque de NiceGUI)
> **Depende de:** S01 (HTTPS debe estar activo para que el flag `Secure` tenga efecto)
> **Bloquea a:** nada directamente, pero es la base de toda la autenticación web

## Contexto del problema

NiceGUI mantiene la sesión mediante una cookie firmada con `STORAGE_SECRET`. Esta cookie
es el único mecanismo de autenticación de la app (los JWT son para la futura API REST).
Si la cookie viaja sin los flags de seguridad correctos, puede ser robada por XSS
(`HttpOnly` lo previene) o enviada sobre HTTP (`Secure` lo previene) o enviada a otros
sitios en requests cross-site (`SameSite` lo previene).

Hoy no hay evidencia de que `ui.run()` configure estos flags explícitamente.

## Requisitos

R1: LA COOKIE DE SESIÓN DE NICEGUI DEBE tener el flag `HttpOnly` activo. Este flag
    impide que JavaScript del navegador lea el valor de la cookie, previniendo el robo
    de sesión mediante XSS.

R2: LA COOKIE DE SESIÓN DEBE tener el flag `Secure` activo en `APP_ENV=production`.
    Esto garantiza que el navegador solo envíe la cookie sobre conexiones HTTPS.
    En desarrollo local (HTTP) este flag puede estar desactivado.

R3: LA COOKIE DE SESIÓN DEBE tener `SameSite=Lax` como mínimo. `SameSite=Strict` es
    preferible si no hay flujos legítimos de navegación cross-site a la app. `None`
    está prohibido sin una justificación documentada.

R4: LA DURACIÓN DE LA SESIÓN DEBE tener un timeout de inactividad (máximo 60 minutos
    sin actividad) y un timeout absoluto (máximo 8 horas desde el login, sin importar
    la actividad). Al expirar, la sesión debe invalidarse server-side, no solo borrar
    la cookie en el cliente.

R5: EL NOMBRE DE LA COOKIE NO DEBE revelar el framework o tecnología usada
    (evitar nombres como `nicegui_session` o similares en producción).

R6: LA IMPLEMENTACIÓN DEBE estar centralizada en el arranque de `main.py` o en la
    configuración de `ui.run()`, no distribuida en páginas individuales.

R7: DEBE existir un test de integración que verifique que una respuesta HTTP de la app
    incluye los flags `HttpOnly`, `Secure` (en modo producción) y `SameSite` en la
    cabecera `Set-Cookie`.

## Criterio de done

- `curl -I https://<dominio>` y la cabecera `Set-Cookie` muestra `HttpOnly; Secure; SameSite=Lax`.
- Test automatizado verifica los flags de la cookie en modo producción.
- Sesión expirada por inactividad redirige al login (no muestra la última página).
