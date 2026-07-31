# mi_cuenta_password — Diseño

## Estructura de archivos

```
CREAR:
  src/interface/pages/mi_cuenta_password.py
  src/interface/design/styles/components/password_change.css

MODIFICAR:
  src/interface/design/theme.py       (agregar password_change.css a CSS_LOAD_ORDER)
  src/interface/design/layout.py      (_user_block_topbar: botón key antes del logout)
  main.py                             (registrar ruta /mi-cuenta/cambiar-password)
```

---

## `mi_cuenta_password.py`

### Patrón general
Sigue el patrón de `cambiar_password.py`: page-delegate registrado en `main.py`
vía `registrar_pagina`. Pero a diferencia del flujo forzado (standalone), esta
página usa `app_layout()` con rail + topbar completo.

```
mi_cuenta_password_page()
  └── app_layout(ctx, contenido_fn,
        page_titulo="Cambiar contraseña",
        page_subtitulo="Actualiza tu contraseña de acceso",
        page_icono="lock")

  contenido_fn():
    div.pwd-page-center
      div.andes-login-card
        div.andes-login-logo
          div.andes-login-icon-wrap → ThemeManager.icono("key", size=40, color="var(--color-primary)")
          ui.label("Cambiar contraseña").classes("andes-login-logo-title")
          ui.label("Elige una nueva contraseña segura...").classes("andes-login-logo-subtitle")

        ui.column().classes("w-full gap-4")
          [actual_input]    ui.input(label="Contraseña actual", password=True, toggle=True)
                            .classes("w-full andes-input").props("outlined")
          div.pwd-separator
          [nueva_input]     ui.input(label="Nueva contraseña", password=True, toggle=True)
                            .classes("w-full andes-input").props("outlined")
          div.pwd-strength  → 3 .pwd-strength-seg + .pwd-strength-label
          div.pwd-reqs      → .pwd-reqs-title + items desde requisitos_password()
          [confirmar_input] ui.input(label="Confirmar nueva contraseña", password=True, toggle=True)
                            .classes("w-full andes-input").props("outlined")

        [error_container]  ui.row().classes("andes-alert andes-alert-error hidden ...")
        [success_container] ui.row().classes("andes-alert andes-alert-success hidden ...")

        div.pwd-actions
          btn_secondary("Cancelar", on_click → navigate.to("/inicio"))
          btn_primary("Cambiar contraseña", on_click=intentar_cambio)
```

### Obtención de contexto
```python
ctx = SessionContext.desde_storage()
usuario_id = app.storage.user.get("usuario_id")
```
No se pasa `ctx` a la función — se obtiene dentro de `contenido_fn` para garantizar que siempre es fresco.

### Requisitos dinámicos (RF-3)
```python
requisitos = Container.usuario_service().requisitos_password()
# Render del checklist:
with ui.element("div").classes("pwd-reqs"):
    ui.label("Requisitos").classes("pwd-reqs-title")
    req_items = {}
    for req in requisitos:
        with ui.row().classes("pwd-req-item") as row:
            ThemeManager.icono("check_circle", size=16)
            ui.label(req)
        req_items[req] = row
```

### Medidor de fortaleza (RF-4)
Segmentos construidos con `ui.element("div")`:
```python
with ui.element("div").classes("pwd-strength"):
    with ui.element("div").classes("pwd-strength-track"):
        seg1 = ui.element("div").classes("pwd-strength-seg")
        seg2 = ui.element("div").classes("pwd-strength-seg")
        seg3 = ui.element("div").classes("pwd-strength-seg")
    strength_label = ui.label("").classes("pwd-strength-label")
```

Handler con throttle:
```python
def _on_nueva_change(e) -> None:
    val = e.value or ""
    # Actualizar checklist
    has_len    = len(val) >= 8
    has_letter = any(c.isalpha() for c in val)
    has_digit  = any(c.isdigit() for c in val)
    # ... actualizar clases de req_items según reglas

    # Actualizar medidor
    score = sum([len(val) >= 4, has_len, has_letter and has_digit,
                 any(not c.isalnum() for c in val), len(val) >= 12])
    if score <= 2:
        nivel, label = "weak", "Débil"
    elif score <= 3:
        nivel, label = "fair", "Aceptable"
    else:
        nivel, label = "strong", "Fuerte"
    # ... actualizar clases de segmentos y label

nueva_input.on("input", _on_nueva_change, throttle=0.3)
```

**Nota:** El checklist actualiza clases CSS `met` / sin `met` usando `.classes(add=..., remove=...)`.
Los `req_items` se construyen iterando `requisitos` en orden. La comparación de regla usa
heurística local *solo para visual*; la validación real la hace el backend.

### Handler `intentar_cambio()` (RF-5 y RF-6)
```python
def intentar_cambio() -> None:
    # Limpiar estado
    error_container.classes(add="hidden", remove="andes-login-alert-in")
    success_container.classes(add="hidden")
    actual_input.props(remove="error")
    nueva_input.props(remove="error")
    confirmar_input.props(remove="error")

    cambiar_btn.disable()
    cambiar_btn.props("loading")
    [inputs].disable()

    def on_finish():
        cambiar_btn.enable()
        cambiar_btn.props(remove="loading")
        [inputs].enable()

    actual    = actual_input.value or ""
    nueva     = nueva_input.value or ""
    confirmar = confirmar_input.value or ""

    # --- Validaciones UI (complementarias) ---
    if not actual or not nueva or not confirmar:
        error_label.set_text("Completa todos los campos.")
        error_container.classes(remove="hidden", add="andes-login-alert-in")
        if not actual: actual_input.props("error")
        if not nueva:  nueva_input.props("error")
        if not confirmar: confirmar_input.props("error")
        on_finish(); return

    if nueva != confirmar:
        error_label.set_text("La nueva contraseña y su confirmación no coinciden.")
        error_container.classes(remove="hidden", add="andes-login-alert-in")
        nueva_input.props("error")
        confirmar_input.props("error")
        on_finish(); return

    if nueva == actual:
        error_label.set_text("La nueva contraseña debe ser distinta de la actual.")
        error_container.classes(remove="hidden", add="andes-login-alert-in")
        nueva_input.props("error")
        on_finish(); return

    usuario_id = app.storage.user.get("usuario_id")
    if not usuario_id:
        ui.navigate.to("/login"); return

    # --- Llamada al servicio (RF-6) ---
    try:
        Container.usuario_service().cambiar_password(usuario_id, actual, nueva)
        # Éxito (RF-7)
        success_label.set_text("Contraseña actualizada correctamente.")
        success_container.classes(remove="hidden", add="andes-login-alert-in")
        from src.interface.design.components.toast import toast_success
        toast_success("Contraseña actualizada correctamente")
        ui.timer(1.5, lambda: ui.navigate.to("/inicio"), once=True)

    except ValueError as exc:
        # Mensaje del backend tal cual — sin traducir
        error_label.set_text(str(exc).strip() or "No se pudo cambiar la contraseña.")
        error_container.classes(remove="hidden", add="andes-login-alert-in")
        on_finish()

    except Exception:
        logger.exception("Error inesperado al cambiar contraseña")
        error_label.set_text("Error del sistema. Intenta de nuevo.")
        error_container.classes(remove="hidden", add="andes-login-alert-in")
        on_finish()
```

### Keyboard shortcuts
```python
confirmar_input.on("keydown.enter", lambda _: intentar_cambio())
actual_input.on("keydown", lambda _: actual_input.props(remove="error"))
nueva_input.on("keydown", lambda _: nueva_input.props(remove="error"))
confirmar_input.on("keydown", lambda _: confirmar_input.props(remove="error"))
```

---

## `password_change.css`

Solo define lo que NO existe en los archivos CSS actuales.
Reutiliza directamente `.andes-login-card`, `.andes-login-icon-wrap`, `.andes-alert-*`, etc.

```css
/* ── Centrado de la card dentro del content area ─────────── */
.pwd-page-center {
  display: flex;
  justify-content: center;
  width: 100%;
  padding: var(--space-md) 0;
}

/* ── Separador visual entre contraseña actual y nueva ────── */
.pwd-separator {
  height: 1px;
  background: var(--color-divider);
  margin: var(--space-xs) 0;
}

/* ── Medidor de fortaleza ────────────────────────────────── */
.pwd-strength {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-top: calc(-1 * var(--space-xs));
}
.pwd-strength-track {
  flex: 1;
  height: 3px;
  display: flex;
  gap: 3px;
}
.pwd-strength-seg {
  flex: 1;
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--color-divider);
  transition: background 0.25s var(--transition-base);
}
.pwd-strength-seg.s-weak   { background: var(--color-error); }
.pwd-strength-seg.s-fair   { background: var(--color-warning); }
.pwd-strength-seg.s-strong { background: var(--color-success); }

.pwd-strength-label {
  font-size: var(--font-size-label);
  font-weight: 500;
  min-width: 56px;
  text-align: right;
  color: var(--color-text-disabled);
  transition: color 0.25s var(--transition-base);
}
.pwd-strength-label.l-weak   { color: var(--color-error); }
.pwd-strength-label.l-fair   { color: var(--color-warning); }
.pwd-strength-label.l-strong { color: var(--color-success); }

/* ── Checklist de requisitos ─────────────────────────────── */
.pwd-reqs {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: var(--space-md);
  background: var(--color-surface-alt);
  border: 1px solid var(--color-divider);
  border-radius: var(--radius-md);
}
.pwd-reqs-title {
  font-size: var(--font-size-label);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-text-secondary);
  margin-bottom: 2px;
}
.pwd-req-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--font-size-small);
  color: var(--color-text-disabled);
  transition: color 0.2s ease;
}
.pwd-req-item.met { color: var(--color-success); }

/* ── Footer de acciones ──────────────────────────────────── */
.pwd-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  padding-top: 20px;
  border-top: 1px solid var(--color-divider);
  margin-top: var(--space-xs);
}

/* ── Dark mode overrides ─────────────────────────────────── */
:root[data-theme="dark"] .pwd-strength-seg.s-weak   { background: #F07070; }
:root[data-theme="dark"] .pwd-strength-seg.s-fair   { background: #F0A850; }
:root[data-theme="dark"] .pwd-strength-seg.s-strong { background: #5EC48A; }
:root[data-theme="dark"] .pwd-strength-label.l-weak   { color: #F07070; }
:root[data-theme="dark"] .pwd-strength-label.l-fair   { color: #F0A850; }
:root[data-theme="dark"] .pwd-strength-label.l-strong { color: #5EC48A; }
:root[data-theme="dark"] .pwd-req-item.met            { color: #5EC48A; }
:root[data-theme="dark"] .pwd-reqs {
  background: var(--color-surface);
  border-color: var(--color-border);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .pwd-strength-seg.s-weak   { background: #F07070; }
  :root:not([data-theme="light"]) .pwd-strength-seg.s-fair   { background: #F0A850; }
  :root:not([data-theme="light"]) .pwd-strength-seg.s-strong { background: #5EC48A; }
  :root:not([data-theme="light"]) .pwd-strength-label.l-weak   { color: #F07070; }
  :root:not([data-theme="light"]) .pwd-strength-label.l-fair   { color: #F0A850; }
  :root:not([data-theme="light"]) .pwd-strength-label.l-strong { color: #5EC48A; }
  :root:not([data-theme="light"]) .pwd-req-item.met            { color: #5EC48A; }
  :root:not([data-theme="light"]) .pwd-reqs {
    background: var(--color-surface);
    border-color: var(--color-border);
  }
}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 640px) {
  .pwd-actions { flex-direction: column; }
  .pwd-actions .btn { width: 100%; }
}

/* ── Reduced motion ──────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .pwd-strength-seg,
  .pwd-strength-label,
  .pwd-req-item { transition: none; }
}
```

---

## `theme.py` — modificación

Agregar `"components/password_change.css"` en `CSS_LOAD_ORDER`, después de
`"components/forms.css"` y antes de `"components/date_input.css"`:

```python
CSS_LOAD_ORDER = [
    ...
    "components/forms.css",
    "components/password_change.css",   # ← NUEVO
    "components/date_input.css",
    ...
]
```

---

## `layout.py` — modificación

En `_user_block_topbar()`, agregar `btn_icon` con icono `"key"` antes del logout:

```python
def _user_block_topbar(ctx: SessionContext | None) -> None:
    if not ctx:
        return
    with ui.row().classes("topbar-user-block items-center gap-2"):
        ThemeManager.icono(Icons.PROFILE, size=20)
        with ui.column().classes("gap-0 topbar-user-info"):
            ui.label(ctx.usuario_nombre or "Usuario").classes("topbar-user-name")
            ui.label(ctx.usuario_rol or "").classes("topbar-user-role")
        # ← NUEVO: acceso a cambio voluntario de contraseña
        btn_icon(
            "key",
            on_click=lambda: ui.navigate.to("/mi-cuenta/cambiar-password"),
            tooltip="Cambiar contraseña",
        )
        btn_icon(
            Icons.LOGOUT,
            on_click=lambda: ui.navigate.to("/logout"),
            tooltip="Cerrar sesión",
        ).classes("topbar-logout-btn")
```

---

## `main.py` — modificación

```python
from src.interface.pages.mi_cuenta_password import mi_cuenta_password_page

# En la sección de registro de rutas, junto a /cambiar-password:
registrar_pagina("/mi-cuenta/cambiar-password", mi_cuenta_password_page, roles=AUTENTICADO)
```

---

## Conexión completa con la capa de servicio

```
UI (mi_cuenta_password.py)
  └── app.storage.user["usuario_id"]       ← sesión activa
  └── Container.usuario_service()
        └── .requisitos_password()         ← render inicial del checklist
        └── .cambiar_password(id, actual, nueva)
              ├── password_policy.validar_password(nueva, username)
              │     └── ValueError si: <8 chars / sin letra / sin dígito / == username
              └── auth_service.cambiar_password(id, actual, nueva)
                    ├── repo.get_password_hash(id)
                    ├── BcryptAuthService.verificar_password(actual, hash)
                    │     └── ValueError("credenciales_invalidas") si no coincide
                    └── repo.actualizar_password_hash(id, nuevo_hash)
                          + repo.marcar_debe_cambiar_password(id, False)
```

Todo `ValueError` propagado sube hasta el `except ValueError` del handler de UI,
que lo muestra directamente en el banner de error sin intermediarios.

---

## Mockup interactivo de referencia

https://claude.ai/code/artifact/deaf9571-80e6-4c81-9bb9-56820b6aa959

Los estados interactivos (Vacío / Escribiendo / Error / Éxito) y el toggle de
tema (☀️/🌙) demuestran el comportamiento esperado.
