# mi_cuenta_password — Requisitos

## Problema

El sistema tiene dos flujos de contraseña:
1. **Cambio forzado** (`/cambiar-password`) — standalone, solo cuando `debe_cambiar_password=True`.
2. **Reset de admin** (dialog en `usuarios.py`) — solo el admin puede resetear contraseñas ajenas.

Ningún usuario puede cambiar voluntariamente su propia contraseña desde dentro del app. Eso obliga a que cualquier cambio pase por el admin, lo que es un problema de autonomía y de seguridad (el admin vería la contraseña temporal).

## Solución

Módulo de cambio voluntario de contraseña accesible desde el topbar, disponible para cualquier usuario autenticado, independientemente de su rol.

## Reglas funcionales

### RF-1 — Acceso
- Ruta: `/mi-cuenta/cambiar-password`
- Roles permitidos: `AUTENTICADO` (todos los roles sin excepción)
- Punto de entrada: botón `btn_icon("key")` en `_user_block_topbar()`, antes del logout
- La ruta es accesible en cualquier momento (no interfiere con el flujo forzado `/cambiar-password`)

### RF-2 — Formulario
El formulario tiene exactamente tres campos, en este orden:
1. **Contraseña actual** — requerido, password con toggle de visibilidad
2. **Nueva contraseña** — requerido, password con toggle de visibilidad
3. **Confirmar nueva contraseña** — requerido, password con toggle de visibilidad

### RF-3 — Requisitos dinámicos
- Los requisitos de la nueva contraseña se obtienen en cada render desde `Container.usuario_service().requisitos_password()`
- No se hardcodean en la UI; si la política cambia en `password_policy.py`, la UI lo refleja sin modificar código de interfaz
- Se muestran como un checklist visual (orientativo) que se actualiza en tiempo real al escribir

### RF-4 — Medidor de fortaleza
- Se actualiza en tiempo real al escribir en "Nueva contraseña"
- Tres niveles: débil / aceptable / fuerte
- Es orientativo; no bloquea el submit

### RF-5 — Validaciones de UI (complementarias, no sustitutas)
La UI valida solo para UX inmediato; **el backend SIEMPRE valida**:
- Campos vacíos → banner error, no llama al servicio
- Nueva contraseña ≠ confirmación → banner error, no llama al servicio
- Nueva contraseña = actual → banner error, no llama al servicio
- El botón "Cambiar contraseña" está siempre habilitado si los campos no están vacíos (no bloquear por fortaleza)

### RF-6 — Conexión con la capa de servicio
La única llamada al backend es:
```python
Container.usuario_service().cambiar_password(usuario_id, actual, nueva)
```
- `usuario_id` viene de `app.storage.user.get("usuario_id")` (la sesión actual)
- Cualquier `ValueError` devuelto por el servicio se muestra directamente en el banner de error, sin traducir ni filtrar
- El servicio delega en `BcryptAuthService.cambiar_password()` (verifica actual) y `password_policy.validar_password()` (valida nueva)

### RF-7 — Flujo de éxito
1. Servicio ejecuta sin excepción
2. Banner éxito visible con mensaje "Contraseña actualizada correctamente"
3. `toast_success("Contraseña actualizada correctamente")`
4. Navegación a `/inicio` tras 1.5 segundos

### RF-8 — Estados de UI
| Estado | Comportamiento |
|---|---|
| Default | Campos vacíos, medidor oculto, requisitos en disabled |
| Escribiendo | Medidor y checklist se actualizan con `on_value_change` (throttle 0.3s) |
| Loading | Botón con `.props("loading")` y `.disable()`, campos deshabilitados |
| Error UI | Banner `.andes-alert-error`, campo(s) en estado error, foco al primero inválido |
| Error backend | Banner `.andes-alert-error` con mensaje exacto del `ValueError` |
| Éxito | Banner `.andes-alert-success`, toast, navegación automática |

## Reglas de capa

- Esta página **no importa** `src.domain.models.*` — pasa primitivos al servicio
- `usuario_id` se obtiene de `app.storage.user`, no del `SessionContext` (consistente con `cambiar_password.py`)
- Sigue el patrón de `cambiar_password.py` para la estructura del formulario
- El CSS nuevo no duplica reglas existentes en `cards.css`, `badges.css`, `forms.css` ni `buttons.css` — solo agrega lo genuinamente nuevo

## Coherencia visual

La card reutiliza exactamente las clases del login (`cambiar_password.py`):
- `.andes-login-card` para la tarjeta
- `.andes-login-logo`, `.andes-login-icon-wrap`, `.andes-login-logo-title`, `.andes-login-logo-subtitle` para el header
- `.andes-input.outlined` para los campos
- `.andes-alert.andes-alert-error` / `.andes-alert-success` para los banners
- `btn_primary`, `btn_secondary` para las acciones
- Icono: `"key"` (40px, `var(--color-primary)`)

## No está en scope

- Cambio de email, teléfono u otros datos de perfil — eso es un módulo distinto
- El admin reseteando contraseñas ajenas — ya existe en `usuarios.py`
- Recordatorio por email — no existe sistema de email en esta versión
