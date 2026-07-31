# Requisitos: WebView2 — Origen restringido y APIs nativas (seguridad_web_16)

> **Nivel:** N3 — Con PWA / WebView2 (Fase 2 del backend_00)
> **Dificultad:** Código-Bajo (configuración de pywebview / WebView2)
> **Depende de:** backend_10_nicegui_native (modo nativo activo)
> **Relacionado con:** S17 (actualización segura del .exe)

## Contexto del problema

En modo escritorio con pywebview (WebView2 en Windows), el contenido web corre
en un control de navegador integrado en la app. Si el WebView puede navegar a
URLs externas o si el código Python expone APIs nativas al JavaScript sin restricciones,
un XSS en la app tiene acceso al filesystem o a la red local de la máquina del usuario.
La superficie de ataque es mayor que en un navegador normal.

## Requisitos

R1: EL WEBVIEW DEBE configurarse para cargar únicamente el origen de la app
    (`http://127.0.0.1:<PORT>`). La navegación a cualquier otra URL DEBE ser
    interceptada y bloqueada o redirigida al navegador externo del sistema.

R2: SI PYWEBVIEW EXPONE APIS PYTHON AL JAVASCRIPT (a través de `webview.expose`
    o equivalente), SOLO las funciones estrictamente necesarias DEBEN exponerse.
    Cada función expuesta DEBE tener validación de entrada; ninguna debe ejecutar
    comandos del sistema operativo con input del usuario.

R3: EL WEBVIEW NO DEBE tener habilitada la consola de desarrollador en builds de
    producción (`debug=False` en `ui.run()`). La consola permite ejecutar JavaScript
    arbitrario con acceso a todas las APIs expuestas.

R4: LA APP DE ESCRITORIO NO DEBE almacenar tokens de sesión en el filesystem en
    texto claro. Si NiceGUI persiste datos de sesión en disco (para recordar el
    login entre sesiones), DEBEN estar cifrados usando el keychain del SO o
    `cryptography.fernet` con una clave derivada de credenciales del usuario.

R5: EL WEBVIEW DEBE aplicar la misma CSP que la versión web (S08), ajustada para
    `connect-src` que apunte a `http://127.0.0.1` en lugar del dominio público.

R6: EL PROCESO PYTHON QUE SIRVE LA APP LOCALMENTE DEBE escuchar solo en
    `127.0.0.1`, nunca en `0.0.0.0`. Esto previene que otras apps o dispositivos
    en la red local accedan a la sesión del usuario.

## Criterio de done

- Intentar navegar a `https://google.com` desde dentro del WebView no carga la página
  (se bloquea o se abre en el navegador externo).
- `debug=False` en el build de producción (verificable en el código de `main.py`).
- La consola de desarrollador no es accesible por el usuario final.
