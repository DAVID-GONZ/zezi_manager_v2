# Requisitos: PWA — Service Worker seguro (seguridad_web_15)

> **Nivel:** N3 — Con PWA / WebView2 (Fase 2 del backend_00)
> **Dificultad:** Código-Bajo (configuración del service worker)
> **Depende de:** backend_10_nicegui_native (modo PWA activo)
> **Relacionado con:** S03 (cookies), S08 (CSP)

## Contexto del problema

Un service worker actúa como proxy entre el navegador y la red. Si cachea datos
sensibles (respuestas de API con datos de alumnos, tokens de sesión), esos datos
quedan accesibles offline y potencialmente para otras apps del mismo origen.
También puede ser un vector de ataque si se registra un service worker malicioso
mediante XSS (por eso S08 es prerequisito).

## Requisitos

R1: EL SERVICE WORKER SOLO DEBE cachear assets estáticos: HTML base, CSS, JavaScript
    de la app, imágenes y fuentes. Nunca cachear respuestas de la API, cookies, tokens
    o datos de usuarios.

R2: LA ESTRATEGIA DE CACHÉ PARA RECURSOS ESTÁTICOS DEBE ser "cache first con
    network fallback". La estrategia para cualquier request a `/api/*` DEBE ser
    "network only" (sin cache en absoluto).

R3: EL SERVICE WORKER DEBE tener una versión explícita en su nombre de archivo o
    en una variable interna (`CACHE_VERSION = 'v1.2.0'`). Al actualizar la app,
    el service worker nuevo DEBE eliminar los caches de la versión anterior.

R4: EL SERVICE WORKER DEBE registrarse solo desde el mismo origen que la app
    (no cross-origin). La CSP (S08) DEBE incluir `worker-src 'self'` para
    prevenir el registro de service workers de orígenes externos.

R5: EL ARCHIVO DEL SERVICE WORKER DEBE servirse con `Cache-Control: no-cache`
    para que el navegador siempre verifique si hay una versión nueva en el servidor.

R6: EL SERVICE WORKER NO DEBE interceptar requests de autenticación (login, logout,
    refresh de tokens). Esas peticiones siempre van directo a la red.

R7: DEBE existir un mecanismo para forzar la actualización del service worker en
    los clientes que tienen una versión antigua cacheada (útil para desplegar
    correcciones de seguridad urgentes). El mecanismo mínimo es incrementar
    `CACHE_VERSION` en cada release.

## Criterio de done

- Las respuestas de `/api/*` no aparecen en el cache del service worker
  (verificable con DevTools → Application → Cache Storage).
- Al actualizar la versión del service worker, los caches anteriores son eliminados.
- `Cache-Control: no-cache` está presente en el archivo del service worker.
