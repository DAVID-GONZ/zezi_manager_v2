# Requisitos: Content Security Policy ajustada a NiceGUI/Quasar (seguridad_web_08)

> **Nivel:** N1 — Primer mes en producción
> **Dificultad:** Código-Alto (requiere iteración; NiceGUI/Quasar tienen scripts inline)
> **Depende de:** S04 (ya debe haber un CSP Report-Only activo)
> **Relacionado con:** S04 (que establece la política en Report-Only)

## Contexto del problema

NiceGUI se construye sobre Quasar (Vue 3) y genera scripts inline para el bootstrapping
de la UI. Una CSP estricta (`script-src 'self'`) rompe la app porque bloquea esos
scripts inline. La estrategia es:

1. Correr en modo `Report-Only` durante staging (ya establecido en S04).
2. Analizar los reportes de violación para identificar exactamente qué permite NiceGUI.
3. Activar la CSP en modo `enforce` con los permisos mínimos necesarios.

Este es el spec más difícil de N1 porque depende del comportamiento interno de NiceGUI,
que puede cambiar con actualizaciones del framework.

## Requisitos

R1: LA CSP DEFINITIVA DEBE estar en modo `enforce` (no `Report-Only`) antes del
    final del primer mes en producción. Mientras esté en Report-Only no protege.

R2: LA CSP DEBE permitir `connect-src wss://<dominio>` para los WebSockets de NiceGUI.
    Sin esto, la UI pierde la conexión en tiempo real.

R3: LA CSP DEBE usar `nonce` o `hash` para los scripts inline de NiceGUI en lugar de
    `'unsafe-inline'`. Si el framework no soporta nonce, usar hash SHA-256 de los
    scripts fijos. `'unsafe-inline'` en `script-src` anula la protección XSS de la CSP.

R4: SI `'unsafe-inline'` en `script-src` es inevitable por limitaciones de NiceGUI,
    DEBE documentarse en `docs/seguridad.md` como decisión aceptada con: versión de
    NiceGUI que lo requiere, tracking issue del framework, y compensación activa
    (validación de salida, sin `ui.html()` con datos del usuario).

R5: LA CSP DEBE incluir `default-src 'self'` como base y sobrescribir solo las
    directivas que necesiten más permisos. Cada directiva permisiva DEBE estar
    justificada en comentario junto a la configuración del proxy.

R6: `style-src` PUEDE incluir `'unsafe-inline'` si Quasar lo requiere para estilos
    dinámicos. Esto es menos crítico que `script-src` porque CSS no ejecuta código.

R7: `frame-ancestors 'none'` DEBE estar presente (refuerza X-Frame-Options).

R8: `form-action 'self'` DEBE estar presente si la app usa formularios HTML nativos.

R9: EL SISTEMA DEBE tener un endpoint de report (`/csp-report`) o usar un servicio
    externo para recibir las violaciones de CSP incluso en modo enforce. Esto permite
    detectar ataques reales o misconfiguraciones post-deploy.

R10: LOS CAMBIOS DE VERSIÓN DE NICEGUI DEBEN disparar una revisión de la CSP. El
     changelog de NiceGUI DEBE revisarse antes de actualizar la dependencia.

## Criterio de done

- `Content-Security-Policy` está en modo `enforce` (no `Report-Only`) en producción.
- La app funciona completamente sin errores de CSP en la consola del navegador.
- `'unsafe-inline'` en `script-src`, si está presente, está documentado en `docs/seguridad.md`.
- El endpoint de report está activo y recibiendo (0 violaciones en uso normal).
