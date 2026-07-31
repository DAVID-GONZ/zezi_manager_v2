# mi_cuenta_password — Tareas de implementación

> Implementa el módulo de cambio voluntario de contraseña dentro del app layout.
> El backend ya existe: `Container.usuario_service().cambiar_password()` y
> `requisitos_password()`. Solo hay que construir la UI y conectarla.
>
> Baseline antes de empezar: `python init.py` verde.

Scope:
```
CREAR:
  src/interface/pages/mi_cuenta_password.py
  src/interface/design/styles/components/password_change.css

MODIFICAR:
  src/interface/design/theme.py
  src/interface/design/layout.py
  main.py
```

---

## T1 — CSS: `password_change.css`

Crear `src/interface/design/styles/components/password_change.css` con las clases
nuevas definidas en `design.md`:
- `.pwd-page-center` — wrapper de centrado dentro del content area
- `.pwd-separator` — divisor 1px divider entre campo actual y nuevo
- `.pwd-strength`, `.pwd-strength-track`, `.pwd-strength-seg` + variantes `.s-weak/.s-fair/.s-strong`
- `.pwd-strength-label` + variantes `.l-weak/.l-fair/.l-strong`
- `.pwd-reqs`, `.pwd-reqs-title`, `.pwd-req-item`, `.pwd-req-item.met`
- `.pwd-actions` — flex row, justify-end, con border-top divider
- Dark mode overrides con los valores exactos de `tokens.css`:
  `#F07070` (error dark), `#F0A850` (warning dark), `#5EC48A` (success dark)
- Duplicar overrides bajo `@media (prefers-color-scheme: dark)` con
  `:root:not([data-theme="light"])` (mismo patrón que `badges.css`)
- Media query `≤640px`: `.pwd-actions` column, botones `width: 100%`
- `@media (prefers-reduced-motion: reduce)`: eliminar transitions de segmentos,
  label y req-items

**Regla:** no duplicar ninguna regla ya presente en `cards.css`, `badges.css`,
`forms.css` ni `buttons.css`. Solo lo genuinamente nuevo.

**Verif:** archivo existe y no vacío; ninguna regla repite selectores de otros archivos.

---

## T2 — theme.py: registrar el CSS

En `ThemeManager.CSS_LOAD_ORDER`, agregar `"components/password_change.css"`
después de `"components/forms.css"` y antes de `"components/date_input.css"`.

**Verif:** `python -c "from src.interface.design.theme import ThemeManager; print('OK')"` sin error.

---

## T3 — layout.py: botón de acceso en el topbar

En `_user_block_topbar()`, agregar `btn_icon("key", on_click=..., tooltip="Cambiar contraseña")`
**antes** del `btn_icon(Icons.LOGOUT, ...)` existente.

El `on_click` debe hacer `lambda: ui.navigate.to("/mi-cuenta/cambiar-password")`.

**Verif:** smoke visual — el icono de llave aparece en el topbar entre el bloque de
usuario y el botón de logout.

---

## T4 — `mi_cuenta_password.py`: estructura y checklist de requisitos

Crear `src/interface/pages/mi_cuenta_password.py` con la función
`mi_cuenta_password_page()` (page-delegate, sin `@ui.page`):

1. Obtener contexto: `SessionContext.desde_storage()` y `app.storage.user.get("usuario_id")`
2. Llamar `app_layout(ctx, contenido_fn, page_titulo=..., page_subtitulo=..., page_icono="lock")`
3. En `contenido_fn()`:
   - `div.pwd-page-center` → `div.andes-login-card`
   - Header con `.andes-login-logo`, `.andes-login-icon-wrap` (icono "key" 40px),
     `.andes-login-logo-title`, `.andes-login-logo-subtitle`
   - Los tres campos `ui.input` con `.classes("w-full andes-input").props("outlined")`
     y `password=True, password_toggle_button=True`
   - `div.pwd-separator` entre campo actual y campo nueva
   - `div.pwd-strength` (3 segmentos + label)
   - `div.pwd-reqs` con checklist dinámico de `Container.usuario_service().requisitos_password()`
   - Banners `error_container` / `success_container` con clases `andes-alert andes-alert-error/success hidden`
   - `div.pwd-actions` con `btn_secondary("Cancelar")` y `btn_primary("Cambiar contraseña")`

El checklist: iterar `requisitos`, crear un `ui.row().classes("pwd-req-item")` por
cada regla con `ThemeManager.icono("check_circle", size=16)` + `ui.label(req)`.
Guardar referencias en un dict `{idx: row}` para actualizarlos en T5.

**Verif:** página carga en `/mi-cuenta/cambiar-password` sin errores; card visible
con los tres campos y el checklist; `python scripts/check_design.py --file src/interface/pages/mi_cuenta_password.py` sin violaciones.

---

## T5 — `mi_cuenta_password.py`: medidor de fortaleza + actualizaciones en tiempo real

En `mi_cuenta_password.py`, implementar `_on_nueva_change(e)` para `on("input", ..., throttle=0.3)`:

**Checklist (heurística visual, complementaria al backend):**
- `len(val) >= 8` → req de longitud marcado como `met`
- `any(c.isalpha() for c in val)` → req de letra marcado como `met`
- `any(c.isdigit() for c in val)` → req de dígito marcado como `met`
- Requisito de "diferente al usuario" → siempre visible, nunca se valida en UI
  (se marca como `met` si las anteriores pasan; el backend lo verifica realmente)

Marcar `met`: `req_row.classes(add="met")` o `req_row.classes(remove="met")`.

**Medidor:**
- Calcular score (suma de condiciones: len≥4, len≥8, letra+dígito, especial, len≥12)
- Score ≤2 → `s-weak` / `l-weak` / "Débil"
- Score ≤3 → `s-fair` / `l-fair` / "Aceptable"
- Score ≥4 → `s-strong` / `l-strong` / "Fuerte"
- Aplicar con `.classes(add=..., remove=...)` a cada segmento y al label

Cuando `val` está vacío: limpiar todas las clases de segmentos y label, `set_text("")`.

**Verif:** escribir en el campo "Nueva contraseña" actualiza visualmente el medidor
y el checklist sin latencia perceptible (throttle 0.3s).

---

## T6 — `mi_cuenta_password.py`: handler `intentar_cambio()` y conexión con servicio

Implementar `intentar_cambio()` según el flujo de `design.md`:

**Validaciones UI (complementarias):**
1. Campos vacíos → banner error "Completa todos los campos", `.props("error")` en vacíos
2. `nueva != confirmar` → banner error "La nueva contraseña y su confirmación no coinciden"
3. `nueva == actual` → banner error "La nueva contraseña debe ser distinta de la actual"

**Llamada al servicio (RF-6):**
```python
Container.usuario_service().cambiar_password(usuario_id, actual, nueva)
```

**Éxito (RF-7):**
- Banner success con "Contraseña actualizada correctamente"
- `toast_success("Contraseña actualizada correctamente")`
- `ui.timer(1.5, lambda: ui.navigate.to("/inicio"), once=True)`

**`ValueError` del backend:** mostrar `str(exc).strip()` directamente en el banner
error, sin traducir ni filtrar.

**`Exception` general:** log + "Error del sistema. Intenta de nuevo."

**Keyboard:**
```python
confirmar_input.on("keydown.enter", lambda _: intentar_cambio())
actual_input.on("keydown",    lambda _: actual_input.props(remove="error"))
nueva_input.on("keydown",     lambda _: nueva_input.props(remove="error"))
confirmar_input.on("keydown", lambda _: confirmar_input.props(remove="error"))
```

**Verif:**
- Campos vacíos → banner error sin llamar al servicio
- Contraseñas no coinciden → banner error sin llamar al servicio
- Contraseña actual incorrecta → banner con el mensaje exacto del `ValueError`
- Contraseña válida → éxito, toast, redirección a `/inicio`

---

## T7 — `main.py`: registrar la ruta

```python
from src.interface.pages.mi_cuenta_password import mi_cuenta_password_page
...
registrar_pagina("/mi-cuenta/cambiar-password", mi_cuenta_password_page, roles=AUTENTICADO)
```

Ubicar junto a la ruta `/cambiar-password` existente en la sección de rutas autenticadas.

**Verif:** `python -c "import main"` sin error; ruta aparece al inspeccionar routes de NiceGUI.

---

## T8 — Verificación integral

- `python init.py` → verde sin regresiones
- `python scripts/check_design.py --file src/interface/pages/mi_cuenta_password.py` → sin violaciones
- Smoke manual:
  1. Login → botón de llave visible en topbar
  2. Click → carga `/mi-cuenta/cambiar-password` con card idéntica al login
  3. Escribir en nueva contraseña → medidor y checklist se actualizan
  4. Submit con actual incorrecta → banner con mensaje del backend
  5. Submit con política violada (ej: sin dígito) → banner con mensaje del backend
  6. Submit correcto → toast + redirección a `/inicio`
  7. Toggle dark mode → colores correctos (card, inputs, banners, medidor)
- `step_list.json` → agregar entry `"mi_cuenta_password"` con `"status": "spec_ready"`

## criterio_done

`/mi-cuenta/cambiar-password` accesible desde el topbar (icono "key") para cualquier
usuario autenticado; card visualmente idéntica al login (mismas clases CSS); checklist
de requisitos generado dinámicamente desde `requisitos_password()` (si la política
cambia, la UI lo refleja sin tocar código de interfaz); medidor de fortaleza orientativo;
`intentar_cambio()` hace validaciones UI ligeras y delega al backend sin filtrar mensajes
de error; `python init.py` verde sin regresiones.
